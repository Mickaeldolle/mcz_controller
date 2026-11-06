from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import pair_once


class FakeBridge:
    profiles = {"on": "C8CC0245B87789"}

    def __init__(self, result="sent"):
        self.result = result
        self.calls = []
        self.closed = False

    def start(self):
        pass

    def close(self):
        self.closed = True

    def status(self):
        return {"connected": True, "busy": False, "tx_count": 0}

    def command(self, action, request_id):
        self.calls.append((action, request_id))
        return {"result": self.result}


class PairingTests(unittest.TestCase):
    def test_profiles_have_valid_crc_and_real_provenance(self):
        p = pair_once.pairing_profiles(pair_once.ROOT / "config/manual_capture_profiles.json")
        self.assertEqual(p["on"], "C8CC0245B87789")

    def test_cancel_never_sends(self):
        b = FakeBridge()
        with patch.object(pair_once, "wait_status", return_value=b.status()):
            self.assertEqual(pair_once.run_trial(b, lambda _: None, lambda _: "ANNULER"), 0)
        self.assertFalse(b.calls)
        self.assertTrue(b.closed)

    def test_offline_never_sends(self):
        b = FakeBridge()
        with patch.object(pair_once, "wait_status", return_value=None):
            self.assertEqual(pair_once.run_trial(b, lambda _: None, lambda _: self.fail("No prompt offline")), 2)
        self.assertFalse(b.calls)
        self.assertTrue(b.closed)

    def test_exactly_one_command_and_rx_confirmation(self):
        b = FakeBridge()
        with patch.object(pair_once, "wait_status", side_effect=[b.status(), {"connected": True, "tx_count": 1}]):
            self.assertEqual(pair_once.run_trial(b, lambda _: None, lambda _: "ENVOYER"), 0)
        self.assertEqual(len(b.calls), 1)
        self.assertEqual(b.calls[0][0], "on")
        self.assertRegex(b.calls[0][1], r"^[0-9a-f]{32}$")
        self.assertTrue(b.closed)

    def test_uncertain_never_retries(self):
        b = FakeBridge("uncertain")
        with patch.object(pair_once, "wait_status", side_effect=[b.status(), None]):
            self.assertEqual(pair_once.run_trial(b, lambda _: None, lambda _: "ENVOYER"), 1)
        self.assertEqual(len(b.calls), 1)
        self.assertTrue(b.closed)

    def test_disconnect_while_operator_prepares_never_sends(self):
        b = FakeBridge()
        ready = b.status()
        b.status = lambda: {"connected": False, "busy": False, "tx_count": 0}
        with patch.object(pair_once, "wait_status", return_value=ready):
            self.assertEqual(pair_once.run_trial(b, lambda _: None, lambda _: "ENVOYER"), 2)
        self.assertFalse(b.calls)
        self.assertTrue(b.closed)


if __name__ == "__main__":
    unittest.main()
