#!/usr/bin/env python3
"""B3B2D: synthetic-only HTTP integration proof for peer-aware B2 cancellation.

This class is not imported into B3B2B, has NO server-start CLI, no listener
and no read on import. Tests mount it ONLY on an ephemeral loopback server
and substitute synthetic child argv before any accepted HTTP GET.
"""
from __future__ import annotations

import json

import v06_b3b_mock_http as b3b1
import v06_b3b2_source_supervisor as b3b2a
import v06_b3b2b_manual_http as b3b2b
import v06_b3b2c_disconnect_lab as b3b2c
import v06_b3b2d_cancel_guard as cancel


class CancelProofHandler(b3b2b.HistoryHandler):
    server_version = "HCC-B3B2D-synthetic-only"

    def do_GET(self):
        try:
            window = b3b1.validate_request(
                self.path, self.headers, self.server.server_address[1])
        except ValueError:
            self._empty(403)
            return
        if not self.server.history_lock.acquire(blocking=False):
            self._empty(503)
            return

        try:
            if b3b2c.disconnected(self.connection):
                self.close_connection = True
                return
            # A B2 worker only starts following a valid, explicit local GET.
            # Automated tests replace the fixed B2 argv with a synthetic
            # subprocess; real-source use is NOT accepted at this stage.
            try:
                result = cancel.read_b2_with_peer(window, self.connection)
                doc = b3b2b.sanitize_result(result, window)
                payload = json.dumps(doc, separators=(",", ":"),
                                     sort_keys=True, ensure_ascii=True,
                                     allow_nan=False).encode("ascii")
                if len(payload) > b3b2b.MAX_RESPONSE_BYTES:
                    raise ValueError("source response too large")
            except Exception:
                payload = json.dumps(b3b2a.unknown(), separators=(",", ":"),
                                     sort_keys=True).encode("ascii")

            # Client may have disconnected during reading or validation:
            # do not start a response on a dead socket.
            if b3b2c.disconnected(self.connection):
                self.close_connection = True
                return
            try:
                self.connection.settimeout(b3b2b.MAX_WRITE_OPERATION_SECONDS)
                self._headers(200, "application/json; charset=utf-8", len(payload))
                self.wfile.write(payload)
            except OSError:
                # Never send a second header or retry a cancelled read.
                self.close_connection = True
        finally:
            self.server.history_lock.release()


# This module has deliberately NO CLI, no HTTP listener and no route wiring
# to the B3B2B manual server. Separate review required before integration.
