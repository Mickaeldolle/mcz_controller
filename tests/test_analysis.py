import binascii
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from analyze_mcz_capture import decode, normalize  # noqa: E402


def waveform(invert: bool = False, bad_crc: bool = False) -> list[int]:
    data = bytes.fromhex("A1 B2 C3 CD A0")
    data += (binascii.crc_hqx(data, 0) ^ int(bad_crc)).to_bytes(2, "big")
    pulses = []

    def emit(high: int, duration: int) -> None:
        value = duration if high ^ invert else -duration
        if pulses and (pulses[-1] > 0) == (value > 0):
            pulses[-1] += value
        else:
            pulses.append(value)

    emit(1, 103000)
    for _ in range(5):
        for i, byte in enumerate(data):
            emit(0, 414)
            emit(1, 828)
            payload = (byte << 1) | int(i == 0)
            word = 0x801 | (payload << 2) | ((bin(payload).count("1") % 2) << 1)
            for bit in range(11, -1, -1):
                high = (word >> bit) & 1
                emit(high, 414)
                emit(1 - high, 414)
        emit(0, 3712)
    return pulses


class AnalysisTests(unittest.TestCase):
    def test_known_frames_and_polarity(self):
        for invert in (False, True):
            frames, longest = decode(waveform(invert))
            self.assertEqual(frames, ["A1 B2 C3 CD A0 36 C9"] * 5)
            self.assertEqual(longest, 7)

    def test_bad_crc_remains_rejected(self):
        frames, longest = decode(waveform(bad_crc=True))
        self.assertEqual(frames, [])
        self.assertEqual(longest, 7)

    def test_short_excursion_preserves_elapsed_time(self):
        raw = [100, 100, -20, 200, -414]
        cleaned = normalize(raw, 80)
        self.assertEqual(cleaned, [420, -414])
        self.assertEqual(sum(map(abs, cleaned)), sum(map(abs, raw)))
        self.assertEqual(raw, [100, 100, -20, 200, -414])

    def test_empty_and_truncated(self):
        self.assertEqual(decode([]), ([], 0))
        self.assertEqual(decode(waveform()[:5])[0], [])


if __name__ == "__main__":
    unittest.main()
