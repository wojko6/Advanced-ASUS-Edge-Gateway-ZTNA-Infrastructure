import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "monitoring" / "pihole-dns-collector.py"
spec = importlib.util.spec_from_file_location("collector", SCRIPT)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


def row(i, domain=None):
    return {
        "id": i,
        "time": float(i),
        "type": "A",
        "status": "FORWARDED",
        "dnssec": "INSECURE",
        "domain": domain or f"d{i}.example",
        "upstream": "127.0.0.1#53535",
        "reply": {"type": "IP", "time": 1.25},
        "client": {"ip": "192.0.2.10", "name": "test-client"},
        "list_id": None,
        "ede": {"code": 0, "text": None},
        "cname": None,
    }


def response(rows, cursor=999):
    return {
        "queries": rows,
        "cursor": cursor,
        "recordsTotal": len(rows),
        "recordsFiltered": len(rows),
        "earliest_timestamp": 1,
        "earliest_timestamp_disk": 1.0,
    }


class FakeAPI:
    def __init__(self, disk_rows, mem_rows):
        self.disk_rows = disk_rows
        self.mem_rows = mem_rows
        self.calls = []

    def queries(self, *, disk, length, cursor=None, start=0):
        rows = self.disk_rows if disk else self.mem_rows
        self.calls.append((disk, length, cursor, start))
        if cursor is None:
            synthetic_global_cursor = rows[0]["id"] + 20 if rows else 0
            return response(rows[:length], cursor=synthetic_global_cursor)
        frozen = [item for item in rows if item["id"] <= cursor]
        return response(frozen[start:start + length], cursor=cursor)


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = collector.open_state_db(self.root / "state.sqlite3")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_disk_uses_first_returned_id_as_frozen_cursor(self):
        api = FakeAPI([row(10), row(9), row(8)], [])
        head, _ = collector.collect_source(
            api, self.db, last_id=7, disk=True, page_size=2, max_pages=10
        )
        self.assertEqual(head, 10)
        frozen_calls = [call for call in api.calls if call[2] is not None]
        self.assertTrue(frozen_calls)
        self.assertTrue(all(call[2] == 10 for call in frozen_calls))
        ids = [item[0] for item in self.db.execute("SELECT id FROM pending ORDER BY id")]
        self.assertEqual(ids, [8, 9, 10])

    def test_disk_and_memory_union_deduplicates_by_id(self):
        api = FakeAPI(
            [row(10, "disk10"), row(9), row(8)],
            [row(12), row(11), row(10, "mem10"), row(9), row(8)],
        )
        collector.collect_source(
            api, self.db, last_id=7, disk=True, page_size=2, max_pages=10
        )
        collector.collect_source(
            api, self.db, last_id=7, disk=False, page_size=2, max_pages=10
        )
        ids = [item[0] for item in self.db.execute("SELECT id FROM pending ORDER BY id")]
        self.assertEqual(ids, [8, 9, 10, 11, 12])
        payload = json.loads(
            self.db.execute("SELECT payload FROM pending WHERE id=10").fetchone()[0]
        )
        self.assertEqual(payload["domain"], "mem10")

    def test_prepared_batch_recovery_does_not_duplicate_complete_append(self):
        for i in (1, 2):
            payload = json.dumps(
                collector.normalize_query(row(i)),
                separators=(",", ":"),
                sort_keys=True,
            )
            self.db.execute("INSERT INTO pending(id,payload) VALUES(?,?)", (i, payload))
        self.db.commit()

        output = self.root / "queries.ndjson"
        prepared = self.root / "prepared.ndjson"
        max_id = collector.prepare_batch(self.db, output, prepared)
        self.assertEqual(max_id, 2)

        # Simulate a crash after the append reached the output but before the
        # checkpoint transaction finalized.
        output.write_bytes(prepared.read_bytes())
        os.chmod(output, 0o600)

        recovered = collector.recover_prepared(self.db, output, prepared)
        self.assertEqual(recovered, 2)
        self.assertEqual(int(collector.get_meta(self.db, "last_id")), 2)
        self.assertEqual(output.read_text().count("\n"), 2)
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM pending").fetchone()[0], 0
        )

    def test_cleartext_non_loopback_is_refused(self):
        with self.assertRaises(collector.CollectorError):
            collector.validate_api_url("http://192.0.2.5:8080")
        self.assertEqual(
            collector.validate_api_url("http://127.0.0.1:18080"),
            "http://127.0.0.1:18080",
        )


if __name__ == "__main__":
    unittest.main()
