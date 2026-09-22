#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analyze-firewall-snapshot.py"
SPEC = importlib.util.spec_from_file_location("fw_semantics", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

FILTER = (ROOT / "tests/fixtures/firewall/post-hook-filter.save").read_text()
NAT = (ROOT / "tests/fixtures/firewall/post-hook-nat.save").read_text()
ROUTES = (ROOT / "tests/fixtures/firewall/routes.txt").read_text()


class FirewallSemanticsTests(unittest.TestCase):
    def errors(self, filter_text=FILTER, nat_text=NAT, routes=ROUTES,
               ip_forward="1\n", ts_if="tailscale0", wan_if="ppp0"):
        return MODULE.check(filter_text, nat_text, routes, ip_forward, ts_if, wan_if)

    def assert_bad(self, expected, **kwargs):
        joined = "\n".join(self.errors(**kwargs))
        self.assertIn(expected, joined)

    def test_valid_fixture(self):
        self.assertEqual(self.errors(), [])

    def test_earlier_accept_is_detected(self):
        text = FILTER.replace(
            "-A INPUT -i tailscale0 -j EDGE_TS_INPUT",
            "-A INPUT -j ACCEPT\n-A INPUT -i tailscale0 -j EDGE_TS_INPUT",
            1,
        )
        self.assert_bad("managed jump is not first", filter_text=text)

    def test_earlier_drop_is_detected(self):
        text = FILTER.replace(
            "-A FORWARD -i tailscale0 -j EDGE_TS_FORWARD",
            "-A FORWARD -j DROP\n-A FORWARD -i tailscale0 -j EDGE_TS_FORWARD",
            1,
        )
        self.assert_bad("managed jump is not first", filter_text=text)

    def test_missing_and_duplicate_jump_are_detected(self):
        missing = FILTER.replace("-A INPUT -i tailscale0 -j EDGE_TS_INPUT\n", "")
        self.assert_bad("found 0", filter_text=missing)
        duplicate = FILTER.replace(
            "-A INPUT -i tailscale0 -j EDGE_TS_INPUT",
            "-A INPUT -i tailscale0 -j EDGE_TS_INPUT\n-A INPUT -i tailscale0 -j EDGE_TS_INPUT",
            1,
        )
        self.assert_bad("found 2", filter_text=duplicate)

    def test_terminal_drop_and_conntrack_are_required(self):
        no_drop = FILTER.replace("-A EDGE_TS_FORWARD -j DROP\n", "")
        self.assert_bad("missing terminal DROP", filter_text=no_drop)
        no_return = FILTER.replace(
            "-A EDGE_TS_FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT\n", ""
        )
        self.assert_bad("missing conntrack", filter_text=no_return)

    def test_nat_and_wan_interface_are_semantic(self):
        no_nat = NAT.replace(
            "-A POSTROUTING -o ppp0 ! -s 198.51.100.25/32 -j MASQUERADE\n", ""
        )
        self.assert_bad("no observed MASQUERADE", nat_text=no_nat)
        self.assert_bad("missing exit rule", wan_if="vlan35")

    def test_sysctl_route_interface_and_stale_chain(self):
        self.assert_bad("ip_forward", ip_forward="0\n")
        self.assert_bad("default route", routes="default via 198.51.100.1 dev vlan35\n")
        stale = FILTER.replace(
            ":EDGE_TS_FORWARD - [0:0]",
            ":EDGE_TS_FORWARD - [0:0]\n:EDGE_TS_OLD - [0:0]",
        )
        self.assert_bad("stale/unexpected", filter_text=stale)

    def test_tailscale_interface_rename_is_not_silently_accepted(self):
        self.assert_bad("managed jump", ts_if="tailscale1")


if __name__ == "__main__":
    unittest.main()
