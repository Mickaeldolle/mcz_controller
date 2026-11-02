"""Run with MCZ_DECODER pointing to the compiled offline decoder executable."""
import binascii
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ToolTests(unittest.TestCase):
    def test_compare(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/compare_frames.py"),
             "A1 B2 C3 CD A0 36 C9", "A1 B2 C3 CD A8 B7 C1"],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(result.stdout.count("CRC=OK"), 2)
        self.assertIn("Octet 4: A0 -> A8", result.stdout)

    def test_bad_hex(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/compare_frames.py"), "XX", "00"],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 2)

    @unittest.skipUnless(os.getenv("MCZ_DECODER"), "Set MCZ_DECODER to offline binary")
    def test_capture_reader(self):
        # Independent synthetic waveform built using Python's CRC reference.
        data = bytes.fromhex("A1 B2 C3 CD A0")
        data += binascii.crc_hqx(data, 0).to_bytes(2, "big")
        halves = []
        for i, byte in enumerate(data):
            halves.extend([0, 1, 1])
            payload = (byte << 1) | int(i == 0)
            word = 0x801 | (payload << 2) | ((bin(payload).count("1") % 2) << 1)
            for bit in range(11, -1, -1):
                one = (word >> bit) & 1
                halves.extend([one, 1 - one])
        pulses = []
        for high in halves:
            value = 414 if high else -414
            if pulses and (pulses[-1] > 0) == bool(high):
                pulses[-1] += value
            else:
                pulses.append(value)
        valid = "RX_BURST_BEGIN\n" + "\n".join(map(str, pulses)) + "\nRX_BURST_END\n"
        for content, expected in ((valid, 0), ("no bursts\n", 1),
                                  ("RX_BURST_BEGIN\n500\n", 2),
                                  ("RX_BURST_BEGIN\ninvalid\nRX_BURST_END\n", 2)):
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "synthetic.log"
                path.write_text(content)
                result = subprocess.run([os.environ["MCZ_DECODER"], str(path)], capture_output=True)
                self.assertEqual(result.returncode, expected, result.stderr)


if __name__ == "__main__":
    unittest.main()
