import sys
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from monitor_serial import Lines, Monitor
import monitor_serial


class MonitorTests(unittest.TestCase):
    def test_fragmented_crlf_and_oversized_line_recovery(self):
        lines = Lines()
        self.assertEqual(list(lines.feed(b"Raw: C8 CC")), [])
        self.assertEqual(list(lines.feed(b" 02 8F B8 8E 16\r\nnext\n")),
                         ["Raw: C8 CC 02 8F B8 8E 16", "next"])
        self.assertEqual(list(lines.feed(b"x" * 2049)), [])
        self.assertEqual(list(lines.feed(b"discard\nrecovered\n")), ["recovered"])

    def test_five_repetitions_remain_visible_with_individual_timing(self):
        output = []
        monitor = Monitor(output.append)
        for n in range(5):
            monitor.receive("Raw: C8 CC 02 8F B8 8E 16", 10 + n * .0825)
        self.assertEqual(monitor.count, 5)
        self.assertEqual(len(output), 5)
        self.assertIn("premiere", output[0])
        self.assertIn("RX #0005", output[-1])
        self.assertIn("Allumer enregistre", output[-1])
        self.assertRegex(output[-1], r"\+8[23] ms")

    def test_bad_crc_and_malformed_frames_are_not_counted(self):
        output = []
        monitor = Monitor(output.append)
        for frame in ("Raw: XX", "Raw: C8 CC 02 8F B8 8E 17"):
            monitor.receive(frame, 1)
        self.assertEqual(monitor.count, 0)
        self.assertEqual(len(output), 2)
        monitor.receive("Raw: C8 CC 02 8B 38 D3 5A", 2)
        self.assertIn("autre trame", output[-1])

    def test_status_changes_and_invalid_usb_json(self):
        output = []
        monitor = Monitor(output.append)
        for payload in ("[]", "null", "42", "{"):
            monitor.receive("APP " + payload, 1)
        status = 'APP {"type":"status","ready":true,"frequency":434500000,"tx_count":0}'
        monitor.receive(status, 2)
        monitor.receive(status, 4)
        self.assertEqual(monitor.status_seen, 4)
        self.assertEqual(len(output), 1)
        self.assertIn("RX PRET", output[0])

    def test_session_only_queries_status_and_releases_port(self):
        clock = [0.0]
        writes = []
        closed = []

        class Port:
            in_waiting = 0

            def __enter__(self):
                return self

            def __exit__(self, *args):
                closed.append(True)

            def read(self, count):
                clock[0] += .1
                return b""

            def write(self, data):
                writes.append(data)

        with tempfile.TemporaryDirectory() as folder:
            with patch.object(monitor_serial, "ROOT", Path(folder)), \
                 patch("sys.argv", ["monitor_serial.py", "--port", "FAKE", "--seconds", "5"]), \
                 patch.object(monitor_serial.time, "perf_counter", side_effect=lambda: clock[0]), \
                 patch.object(monitor_serial.time, "monotonic", side_effect=AssertionError("Use the precise clock")), \
                 patch.object(monitor_serial.serial, "Serial", return_value=Port()), \
                 patch("builtins.print"):
                monitor_serial.main()
            logs = list((Path(folder) / "captures").glob("*_live.log"))
            self.assertEqual(len(logs), 1)
            self.assertIn("Port USB libere", logs[0].read_text(encoding="utf-8"))
        self.assertEqual(writes, [b"js", b"j"])
        self.assertEqual(closed, [True])


if __name__ == "__main__":
    unittest.main()
