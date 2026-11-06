"""One recorded ON command for a supervised pairing trial; no automatic retry."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import secrets
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.bridge import Bridge, load_profiles


def pairing_profiles(path):
    profiles = load_profiles(path)
    if profiles["on"] != "C8CC0245B87789" or profiles["off"] != "C8CC0244B844B8":
        raise ValueError("Cet essai exige les captures manuelles puissance 1, ventilation 2")
    source = (ROOT / profiles["source"]).resolve()
    if not source.is_relative_to((ROOT / "captures").resolve()):
        raise ValueError("La provenance doit se trouver dans captures")
    frames = re.findall(r"\b[0-9A-F]{2}(?: [0-9A-F]{2}){6}\b", source.read_text(encoding="utf-8"))
    for action in ("on", "off"):
        if frames.count(bytes.fromhex(profiles[action]).hex(" ").upper()) < 5:
            raise ValueError("Provenance insuffisante pour " + action)
    return profiles


def wait_status(bridge, after, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with bridge.lock:
            fresh = bridge.seen > after
        if fresh:
            return bridge.status()
        time.sleep(.05)
    return None


def run_trial(bridge, emit, confirm=input):
    started = time.monotonic()
    bridge.start()
    try:
        before = wait_status(bridge, started)
        if before is None or not before["connected"] or type(before["tx_count"]) is not int:
            emit("ABANDON : statut USB/RX indisponible. Aucun ordre envoye.")
            return 2
        emit("PRET : USB/RX connecte. " + json.dumps(before, ensure_ascii=True))
        emit("Trame prevue : C8 CC 02 45 B8 77 89 ; une commande, cinq repetitions.")
        emit("Ce rejeu est un essai d'apprentissage, pas une trame speciale identifiee.")
        emit("Mettre le poele en apprentissage selon sa notice ; attendre les trois traits ---.")
        emit("La commande peut declencher un allumage. Rester devant le poele.")
        if confirm("Taper ENVOYER quand --- est affiche, ou ANNULER pour quitter : ").strip() != "ENVOYER":
            emit("ANNULE : aucun ordre envoye.")
            return 0
        # Read the baseline again: the operator may have waited several minutes.
        before = bridge.status()
        if not before["connected"] or before["busy"] or type(before["tx_count"]) is not int:
            emit("ABANDON : liaison non prete au moment du declenchement. Aucun ordre envoye.")
            return 2
        request_id = secrets.token_hex(16)
        emit(f"ENVOI UNIQUE id={request_id} trame={bridge.profiles['on']} TX_avant={before['tx_count']}")
        result = bridge.command("on", request_id)
        completed = time.monotonic()
        emit("RESULTAT USB : " + json.dumps(result, ensure_ascii=True))
        after = wait_status(bridge, completed, timeout=5)
        emit("STATUT APRES : " + json.dumps(after, ensure_ascii=True))
        emit("Aucun renvoi automatique. Relever bip, disparition de --- et reaction du poele.")
        success = (result.get("result") == "sent" and after is not None
                   and after["connected"] and after["tx_count"] == before["tx_count"] + 1)
        emit("Bilan technique : " + ("signal termine, compteur +1 et retour RX confirme." if success
                                     else "emission ou retour RX non entierement confirme."))
        emit("Ce bilan n'est pas un accuse de reception du poele.")
        return 0 if success else 1
    except (EOFError, KeyboardInterrupt):
        emit("INTERROMPU : aucune relance ; si l'envoi avait debute, observer le poele.")
        return 1
    finally:
        bridge.close()
        emit("Port USB libere.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="COM3")
    args = parser.parse_args()
    try:
        profiles = pairing_profiles(ROOT / "config/manual_capture_profiles.json")
        folder = ROOT / "captures"
        folder.mkdir(exist_ok=True)
        path = folder / (datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "_pairing.log")
        with path.open("x", encoding="utf-8", buffering=1) as log:
            def emit(message):
                output = datetime.now().astimezone().isoformat(timespec="milliseconds") + "  " + message
                print(output, flush=True)
                log.write(output + "\n")
            emit("ESSAI ESP32 : aucune emission avant ENVOYER. Journal : " + str(path))
            return run_trial(Bridge(args.port, profiles=profiles), emit)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"Preparation impossible : {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
