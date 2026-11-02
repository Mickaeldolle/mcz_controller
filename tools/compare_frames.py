"""Offline comparison of two seven-byte hex frames; no external dependencies."""
import argparse
import binascii


def frame(value: str) -> bytes:
    try:
        result = bytes.fromhex(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Sept octets hexadecimaux attendus") from exc
    if len(result) != 7:
        raise argparse.ArgumentTypeError("La trame doit contenir exactement 7 octets")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=frame)
    parser.add_argument("after", type=frame)
    args = parser.parse_args()
    for label, data in (("Avant", args.before), ("Apres", args.after)):
        crc_ok = binascii.crc_hqx(data[:5], 0) == int.from_bytes(data[5:], "big")
        print(f"{label}: ID={data[:3].hex().upper()} CRC={'OK' if crc_ok else 'INVALIDE'} "
              f"mode={data[3]&3} power={(data[3]>>2)&7} fan1={data[3]>>5} "
              f"fan2={(data[4]>>3)&7} user={data[4]>>6} reserved={data[4]&7}")
    for i, (a, b) in enumerate(zip(args.before, args.after)):
        mask = a ^ b
        if mask:
            bits = ",".join(str(bit) for bit in range(7, -1, -1) if mask & (1 << bit))
            print(f"Octet {i}: {a:02X} -> {b:02X}, XOR={mask:08b}, bits modifies={bits}")


if __name__ == "__main__":
    main()
