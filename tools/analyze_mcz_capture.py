"""Offline MCZ waveform diagnostics. Never repairs bytes or bypasses CRC checks."""
import argparse
import binascii
import collections
import json
from pathlib import Path
import re
import statistics


def read_blocks(path: Path) -> list[list[int]]:
    text = path.read_text(errors="replace")
    blocks = []
    for body in re.findall(r"RX_BURST_BEGIN\s+(.*?)RX_BURST_END", text, re.S):
        values = [int(v) for v in body.split()]
        if len(values) > 2048 or any(v == 0 or abs(v) > 1000000 for v in values):
            raise ValueError(f"Invalid capture in {path}")
        blocks.append(values)
    return blocks


def normalize(pulses: list[int], glitch_us: int) -> list[int]:
    result: list[int] = []
    for value in pulses:
        if result and (result[-1] > 0) == (value > 0):
            result[-1] += value
        else:
            result.append(value)
    # Remove only a short excursion enclosed by the same electrical level.
    # Preserve total elapsed time; this is a diagnostic hypothesis, not raw evidence.
    i = 1
    while glitch_us and i + 1 < len(result):
        if abs(result[i]) < glitch_us and (result[i - 1] > 0) == (result[i + 1] > 0):
            sign = 1 if result[i - 1] > 0 else -1
            result[i - 1:i + 2] = [sign * sum(abs(v) for v in result[i - 1:i + 2])]
            i = max(1, i - 1)
        else:
            i += 1
    return result


def decode(pulses: list[int], half_us: int = 414) -> tuple[list[str], int]:
    halves: list[int] = []
    for value in pulses:
        duration = abs(value)
        level = int(value > 0)
        if duration >= 2500:
            halves.extend([level, -1])
            continue
        n = int(duration / half_us + 0.5)
        if 1 <= n <= 3 and abs(duration - n * half_us) <= 104:
            halves.extend([level] * n)
        else:
            halves.append(-1)
    words: dict[tuple[int, int], tuple[int, int]] = {}
    for pos in range(len(halves) - 23):
        bits = halves[pos:pos + 24]
        if any(a < 0 or b < 0 or a == b for a, b in zip(bits[::2], bits[1::2])):
            continue
        for invert in (0, 1):
            word = 0
            for value in bits[::2]:
                word = (word << 1) | (value ^ invert)
            if word & 0x801 != 0x801:
                continue
            if sum((word >> bit) & 1 for bit in range(1, 11)) % 2:
                continue
            words[pos, invert] = ((word >> 3) & 255, (word >> 2) & 1)
    frames = []
    longest = 0
    for (pos, invert), (byte, first) in words.items():
        if not first:
            continue
        data = [byte]
        nxt = pos + 27
        while len(data) < 7 and (nxt, invert) in words and words[nxt, invert][1] == 0:
            separator = halves[nxt - 3:nxt]
            if separator != [invert, 1 ^ invert, 1 ^ invert]:
                break
            data.append(words[nxt, invert][0])
            nxt += 27
        longest = max(longest, len(data))
        if len(data) == 7:
            raw = bytes(data)
            if binascii.crc_hqx(raw[:5], 0) == int.from_bytes(raw[5:], "big"):
                frames.append(raw.hex(" ").upper())
    return frames, longest


def analyze(path: Path) -> dict:
    blocks = read_blocks(path)
    if not blocks:
        raise ValueError(f"No raw capture in {path}")
    all_pulses = [v for block in blocks for v in block]
    prefixes = [abs(v) for v in all_pulses if 85000 <= abs(v) <= 115000]
    modes = []
    # Keep each transform explicit. No changes to firmware or captured files.
    for mode, glitch in (("raw", None), ("merge_same_level", 0), ("glitch_under_80us", 80),
                         ("glitch_under_120us", 120), ("glitch_under_180us", 180), ("glitch_under_240us", 240)):
        for half in (400, 414, 428):
            frames: list[str] = []
            longest = 0
            for block in blocks:
                candidates, chain = decode(block if glitch is None else normalize(block, glitch), half)
                frames.extend(candidates)
                longest = max(longest, chain)
            modes.append({"mode": mode, "half_us": half, "crc_valid_frames": frames,
                          "longest_consecutive_bytes_with_framing": longest})
    return {
        "file": path.name, "blocks": len(blocks), "pulses": len(all_pulses),
        "prefix_count_85_to_115ms": len(prefixes),
        "prefix_median_us": statistics.median(prefixes) if prefixes else None,
        "prefix_min_us": min(prefixes) if prefixes else None,
        "prefix_max_us": max(prefixes) if prefixes else None,
        "pulses_under_250us_percent": round(100 * sum(abs(v) < 250 for v in all_pulses) / len(all_pulses), 2),
        "adjacent_same_sign": sum(a * b > 0 for block in blocks for a, b in zip(block, block[1:])),
        "duration_histogram_50us": collections.Counter(str(round(abs(v) / 50) * 50) for v in all_pulses if abs(v) < 2500),
        "decode_hypotheses": modes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", type=Path, nargs="+")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = {"warning": "Offline hypotheses. Only complete frames passing framing, parity and CRC are valid.",
                  "captures": [analyze(path) for path in args.captures]}
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Analysis failed: {exc}\n")
    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
