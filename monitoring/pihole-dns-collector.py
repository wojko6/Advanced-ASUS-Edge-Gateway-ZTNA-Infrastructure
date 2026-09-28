#!/usr/bin/env python3
"""Read Pi-hole v6 query history through the authenticated local API.

The collector is intentionally Fedora-side. It expects the Pi-hole API to be
available through a loopback SSH tunnel and writes private NDJSON events plus a
local SQLite checkpoint. No Pi-hole database is opened or modified.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REQUIRED_QUERY_KEYS = {
    "id", "time", "type", "status", "dnssec", "domain", "upstream",
    "reply", "client", "list_id", "ede", "cname",
}
REQUIRED_TOP_LEVEL = {
    "queries", "cursor", "recordsTotal", "recordsFiltered",
    "earliest_timestamp", "earliest_timestamp_disk",
}


class CollectorError(RuntimeError):
    pass


def env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise CollectorError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise CollectorError(f"{name} must be between {minimum} and {maximum}")
    return value


def xdg_state_home() -> Path:
    raw = os.environ.get("XDG_STATE_HOME")
    return Path(raw).expanduser() if raw else Path.home() / ".local" / "state"


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)


def check_secret_file(path: Path) -> str:
    try:
        st = path.stat()
    except FileNotFoundError as exc:
        raise CollectorError(f"application password file does not exist: {path}") from exc

    if st.st_uid != os.getuid():
        raise CollectorError("application password file must be owned by the collector user")
    if stat.S_IMODE(st.st_mode) & 0o077:
        raise CollectorError("application password file must not be group/world accessible")

    secret = path.read_text(encoding="utf-8").strip()
    if not secret:
        raise CollectorError("application password file is empty")
    return secret


def validate_api_url(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise CollectorError("PIHOLE_API_URL must be an http(s) URL")
    if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "::1", "localhost"}:
        raise CollectorError(
            "refusing to send the application password over cleartext non-loopback HTTP"
        )
    return base_url.rstrip("/")


def validate_query(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise CollectorError("Pi-hole query row is not an object")
    missing = REQUIRED_QUERY_KEYS - row.keys()
    if missing:
        raise CollectorError("Pi-hole query schema mismatch: missing " + ",".join(sorted(missing)))
    if not isinstance(row["id"], int):
        raise CollectorError("Pi-hole query schema mismatch: id is not an integer")
    if not isinstance(row["time"], (int, float)):
        raise CollectorError("Pi-hole query schema mismatch: time is not numeric")
    for nested, keys in (
        ("client", {"ip", "name"}),
        ("reply", {"type", "time"}),
        ("ede", {"code", "text"}),
    ):
        obj = row[nested]
        if not isinstance(obj, dict) or not keys.issubset(obj):
            raise CollectorError(f"Pi-hole query schema mismatch: malformed {nested}")
    return row


def normalize_query(row: dict[str, Any]) -> dict[str, Any]:
    validate_query(row)
    return {
        "source": "pihole",
        "dataset": "dns-activity",
        "id": row["id"],
        "time": row["time"],
        "type": row["type"],
        "status": row["status"],
        "dnssec": row["dnssec"],
        "domain": row["domain"],
        "upstream": row["upstream"],
        "reply_type": row["reply"]["type"],
        "reply_time_ms": row["reply"]["time"],
        "client_ip": row["client"]["ip"],
        "client_name": row["client"]["name"],
        "list_id": row["list_id"],
        "ede_code": row["ede"]["code"],
        "ede_text": row["ede"]["text"],
        "cname": row["cname"],
    }


class PiHoleAPI:
    def __init__(self, base_url: str, password: str, timeout: int):
        self.base_url = validate_api_url(base_url)
        self.password = password
        self.timeout = timeout
        self.sid: str | None = None

    def _request(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
        authenticated: bool = True,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if authenticated:
            if not self.sid:
                raise CollectorError("Pi-hole API request attempted without a session")
            headers["X-FTL-SID"] = self.sid

        req = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise CollectorError(f"Pi-hole API returned HTTP {exc.code} for {path}") from exc
        except OSError as exc:
            raise CollectorError(f"Pi-hole API connection failed for {path}: {exc}") from exc

        if not raw:
            return {}
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CollectorError(f"Pi-hole API returned invalid JSON for {path}") from exc
        if not isinstance(obj, dict):
            raise CollectorError(f"Pi-hole API returned a non-object for {path}")
        return obj

    def login(self) -> None:
        data = self._request(
            "/api/auth",
            method="POST",
            payload={"password": self.password},
            authenticated=False,
        )
        session = data.get("session")
        if not isinstance(session, dict) or session.get("valid") is not True:
            raise CollectorError("Pi-hole application-password authentication failed")
        sid = session.get("sid")
        if not isinstance(sid, str) or not sid:
            raise CollectorError("Pi-hole authentication succeeded without a usable SID")
        self.sid = sid

    def logout(self) -> None:
        if not self.sid:
            return
        req = urllib.request.Request(
            self.base_url + "/api/auth",
            headers={"X-FTL-SID": self.sid},
            method="DELETE",
        )
        try:
            urllib.request.urlopen(req, timeout=self.timeout).read()
        except Exception:
            pass
        finally:
            self.sid = None

    def queries(
        self,
        *,
        disk: bool,
        length: int,
        cursor: int | None = None,
        start: int = 0,
    ) -> dict[str, Any]:
        params: dict[str, str | int] = {"length": length}
        if disk:
            params["disk"] = "true"
        if cursor is not None:
            params["cursor"] = cursor
            params["start"] = start
        path = "/api/queries?" + urllib.parse.urlencode(params)
        data = self._request(path)

        missing = REQUIRED_TOP_LEVEL - data.keys()
        if missing:
            raise CollectorError(
                "Pi-hole response schema mismatch: missing " + ",".join(sorted(missing))
            )
        if not isinstance(data.get("queries"), list):
            raise CollectorError("Pi-hole response schema mismatch: queries is not an array")
        return data


def open_state_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS pending (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)"
    )
    conn.commit()
    os.chmod(path, 0o600)
    return conn


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
    return None if row is None else str(row[0])


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO metadata(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def clear_meta(conn: sqlite3.Connection, keys: list[str]) -> None:
    conn.executemany("DELETE FROM metadata WHERE key = ?", [(key,) for key in keys])


PREPARED_KEYS = [
    "prepared_start", "prepared_len", "prepared_sha256", "prepared_max_id",
]


def file_segment_sha256(path: Path, start: int, length: int) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        fh.seek(start)
        remaining = length
        while remaining:
            chunk = fh.read(min(1024 * 1024, remaining))
            if not chunk:
                raise CollectorError("output file ended inside a prepared batch")
            digest.update(chunk)
            remaining -= len(chunk)
    return digest.hexdigest()


def append_prepared(
    conn: sqlite3.Connection,
    output_path: Path,
    prepared_path: Path,
) -> int:
    start_raw = get_meta(conn, "prepared_start")
    length_raw = get_meta(conn, "prepared_len")
    digest = get_meta(conn, "prepared_sha256")
    max_id_raw = get_meta(conn, "prepared_max_id")
    if None in {start_raw, length_raw, digest, max_id_raw}:
        raise CollectorError("prepared-batch journal is incomplete")

    start = int(start_raw)
    length = int(length_raw)
    max_id = int(max_id_raw)

    if not prepared_path.exists():
        raise CollectorError("prepared-batch file is missing")
    if prepared_path.stat().st_size != length:
        raise CollectorError("prepared-batch file length mismatch")
    if file_segment_sha256(prepared_path, 0, length) != digest:
        raise CollectorError("prepared-batch file digest mismatch")

    current = output_path.stat().st_size if output_path.exists() else 0
    expected = start + length

    if current == expected:
        if file_segment_sha256(output_path, start, length) != digest:
            raise CollectorError("existing output batch digest mismatch")
    elif current == start:
        # Normal first append or a clean append after the previous batch.
        # The output file may not exist yet when both values are zero.
        pass
    elif start < current < expected:
        with output_path.open("r+b") as fh:
            fh.truncate(start)
            fh.flush()
            os.fsync(fh.fileno())
        current = start
    else:
        raise CollectorError(
            "output file size changed outside the collector; refusing unsafe recovery"
        )

    if current == start:
        fd = os.open(output_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.chmod(output_path, 0o600)
            with os.fdopen(os.dup(fd), "ab") as out, prepared_path.open("rb") as src:
                shutil.copyfileobj(src, out)
                out.flush()
                os.fsync(out.fileno())
        finally:
            os.close(fd)

    set_meta(conn, "last_id", str(max_id))
    clear_meta(conn, PREPARED_KEYS)
    conn.execute("DELETE FROM pending")
    conn.commit()
    prepared_path.unlink(missing_ok=True)
    return max_id


def recover_prepared(
    conn: sqlite3.Connection,
    output_path: Path,
    prepared_path: Path,
) -> int | None:
    if get_meta(conn, "prepared_start") is None:
        return None
    return append_prepared(conn, output_path, prepared_path)


def collect_source(
    api: PiHoleAPI,
    conn: sqlite3.Connection,
    *,
    last_id: int,
    disk: bool,
    page_size: int,
    max_pages: int,
) -> tuple[int | None, int]:
    initial = api.queries(disk=disk, length=1)
    initial_rows = initial["queries"]
    if not initial_rows:
        return None, 0

    head_row = validate_query(initial_rows[0])
    head_id = head_row["id"]
    if head_id <= last_id:
        return head_id, 0

    start = 0
    pages = 0
    reached_checkpoint = False

    while True:
        pages += 1
        if pages > max_pages:
            raise CollectorError(
                f"bounded extraction exceeded PIHOLE_MAX_PAGES for {'disk' if disk else 'memory'}"
            )

        data = api.queries(
            disk=disk,
            length=page_size,
            cursor=head_id,
            start=start,
        )
        rows = data["queries"]
        if not rows:
            break

        for raw in rows:
            row = validate_query(raw)
            row_id = row["id"]
            if row_id <= last_id:
                reached_checkpoint = True
                continue
            payload = json.dumps(
                normalize_query(row),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            conn.execute(
                "INSERT INTO pending(id,payload) VALUES(?,?) "
                "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                (row_id, payload),
            )

        conn.commit()

        if reached_checkpoint or len(rows) < page_size:
            break
        start += len(rows)

    pending = conn.execute("SELECT COUNT(*) FROM pending").fetchone()[0]
    return head_id, int(pending)


def prepare_batch(
    conn: sqlite3.Connection,
    output_path: Path,
    prepared_path: Path,
) -> int | None:
    row = conn.execute("SELECT MAX(id), COUNT(*) FROM pending").fetchone()
    max_id, count = row if row else (None, 0)
    if not count:
        return None

    digest = hashlib.sha256()
    total = 0
    tmp = prepared_path.with_suffix(".tmp")
    with tmp.open("wb") as fh:
        os.chmod(tmp, 0o600)
        for (payload,) in conn.execute("SELECT payload FROM pending ORDER BY id ASC"):
            line = str(payload).encode("utf-8") + b"\n"
            fh.write(line)
            digest.update(line)
            total += len(line)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, prepared_path)

    start = output_path.stat().st_size if output_path.exists() else 0
    set_meta(conn, "prepared_start", str(start))
    set_meta(conn, "prepared_len", str(total))
    set_meta(conn, "prepared_sha256", digest.hexdigest())
    set_meta(conn, "prepared_max_id", str(int(max_id)))
    conn.commit()
    return int(max_id)


def run() -> int:
    base_url = validate_api_url(os.environ.get("PIHOLE_API_URL", "http://127.0.0.1:18080"))
    timeout = env_int("PIHOLE_HTTP_TIMEOUT", 15, 1, 120)
    page_size = env_int("PIHOLE_PAGE_SIZE", 500, 1, 2000)
    max_pages = env_int("PIHOLE_MAX_PAGES", 1000, 1, 10000)

    state_dir = Path(
        os.environ.get(
            "PIHOLE_STATE_DIR",
            str(xdg_state_home() / "pihole-dns-collector"),
        )
    ).expanduser()
    ensure_private_dir(state_dir)

    output_path = Path(
        os.environ.get("PIHOLE_OUTPUT_FILE", str(state_dir / "queries.ndjson"))
    ).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    state_db_path = Path(
        os.environ.get("PIHOLE_STATE_DB", str(state_dir / "state.sqlite3"))
    ).expanduser()
    password_path = Path(
        os.environ.get(
            "PIHOLE_APP_PASSWORD_FILE",
            str(Path.home() / ".config" / "pihole-dns-collector" / "app-password"),
        )
    ).expanduser()
    prepared_path = state_dir / "prepared.ndjson"

    password = check_secret_file(password_path)
    conn = open_state_db(state_db_path)

    recovered = recover_prepared(conn, output_path, prepared_path)
    if recovered is not None:
        print(f"recovered prepared batch; checkpoint={recovered}")
    elif prepared_path.exists():
        prepared_path.unlink()

    conn.execute("DELETE FROM pending")
    conn.commit()

    last_id = int(get_meta(conn, "last_id") or "0")
    api = PiHoleAPI(base_url, password, timeout)
    started = time.monotonic()

    try:
        api.login()

        disk_head, _ = collect_source(
            api,
            conn,
            last_id=last_id,
            disk=True,
            page_size=page_size,
            max_pages=max_pages,
        )
        disk_pending = conn.execute("SELECT COUNT(*) FROM pending").fetchone()[0]
        mem_head, _ = collect_source(
            api,
            conn,
            last_id=last_id,
            disk=False,
            page_size=page_size,
            max_pages=max_pages,
        )
        union_pending = conn.execute("SELECT COUNT(*) FROM pending").fetchone()[0]

        max_id = prepare_batch(conn, output_path, prepared_path)
        if max_id is not None:
            max_id = append_prepared(conn, output_path, prepared_path)

        elapsed = time.monotonic() - started
        print(
            "collector_ok "
            f"last_id={max_id if max_id is not None else last_id} "
            f"disk_head={disk_head} mem_head={mem_head} "
            f"disk_pending={disk_pending} union_pending={union_pending} "
            f"elapsed_s={elapsed:.3f}"
        )
        return 0
    finally:
        api.logout()
        conn.close()


def main() -> int:
    try:
        return run()
    except CollectorError as exc:
        print(f"collector_error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"collector_error: unexpected {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
