"""Capture validation and manual profiles shared by the PC and firmware."""
import binascii
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "config/catalogue_mcz.csv"
COLUMNS = ("numero", "commande", "trame", "receptions", "capture")
DEFAULT_ON = "1:1"
REMOTE_ID = bytes.fromhex("C8CC02")
MCZ_FREQUENCY_HZ = 434500000


def validate_frame(value: str) -> bytes:
    raw = bytes.fromhex(value)
    if len(raw) != 7 or raw[:3] != REMOTE_ID:
        raise ValueError("Identifiant ou longueur de trame invalide")
    if binascii.crc_hqx(raw[:5], 0) != int.from_bytes(raw[5:], "big"):
        raise ValueError("CRC invalide")
    return raw


def load_presets(path=CATALOG, root=ROOT) -> dict[str, str]:
    """Verify every catalogue group against the original receiver log."""
    captures = (root / "captures").resolve()
    observations: dict[Path, list[str]] = {}
    offsets: dict[Path, int] = {}
    presets: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=";", strict=True)
        if next(reader, None) != list(COLUMNS):
            raise ValueError("En-tête du catalogue invalide")
        for number, (record_number, _, frame, count, source) in enumerate(reader, 1):
            raw = validate_frame(frame)
            frame = raw.hex().upper()
            log = (root / source).resolve()
            if record_number != str(number) or log.parent != captures or log.suffix != ".log" or count != "5":
                raise ValueError(f"Provenance invalide pour la ligne {number}")
            if log not in observations:
                observations[log] = [line for line in log.read_text(encoding="utf-8").splitlines()
                                     if "  RX #" in line]
            first = offsets.get(log, 0)
            group = observations[log][first:first + 5]
            evidence = f"  {raw.hex(' ').upper()}  ["
            if len(group) != 5 or any(
                f"RX #{index:04d} " not in line or evidence not in line or not line.endswith(" CRC=OK")
                for index, line in enumerate(group, first + 1)
            ):
                raise ValueError(f"Trame absente du groupe RX de la ligne {number}")
            offsets[log] = first + 5
            settings = raw[3]
            mode, power, fan = settings & 3, (settings >> 2) & 7, settings >> 5
            fan2 = (raw[4] >> 3) & 7
            if mode == 0 and (power, fan) == (1, 1):
                profile = "off"
            elif mode == 1 and 1 <= power <= 5 and 1 <= fan <= 6:
                profile = f"{power}:{fan}"
                if fan2 <= 6:
                    profile += f":{fan2}"
            else:
                raise ValueError(f"Réglage hors périmètre à la ligne {number}")
            if presets.setdefault(profile, frame) != frame:
                raise ValueError(f"Plusieurs trames pour le réglage {profile}")
    if DEFAULT_ON not in presets or "off" not in presets:
        raise ValueError("Le catalogue doit contenir les commandes ON et OFF")
    return presets


def _encode_manual(template: bytes, power: int, fan1: int, fan2: int) -> str:
    settings = (template[3] & 0x03) | (power << 2) | (fan1 << 5)
    options = (template[4] & 0xC7) | (fan2 << 3)
    payload = template[:3] + bytes((settings, options))
    crc = binascii.crc_hqx(payload, 0)
    return (payload + crc.to_bytes(2, "big")).hex().upper()


def load_command_presets() -> dict[str, str]:
    """Expand the documented manual fields after checking every captured profile."""
    presets = load_presets()
    template = validate_frame(presets[DEFAULT_ON])
    captured_fan2 = set()
    for profile, frame in presets.items():
        if profile == "off":
            continue
        power, fan1, *explicit_fan2 = map(int, profile.split(":"))
        fan2 = explicit_fan2[0] if explicit_fan2 else 7
        if _encode_manual(template, power, fan1, fan2) != frame:
            raise ValueError(f"L’encodage ne reproduit pas la capture du profil {profile}")
        if explicit_fan2:
            captured_fan2.add(fan2)

    if captured_fan2 != set(range(7)):
        return presets

    # Keep the captured two-field profiles with fan2=7 and generate explicit 0–6 only.
    for power in range(1, 6):
        for fan1 in range(1, 7):
            for fan2 in range(7):
                presets[f"{power}:{fan1}:{fan2}"] = _encode_manual(template, power, fan1, fan2)
    return presets
