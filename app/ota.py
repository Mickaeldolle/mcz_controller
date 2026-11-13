"""Configure ou téléverse le firmware ESP32 sur le réseau local."""
import argparse
from getpass import GetPassWarning, getpass
import hashlib
import hmac
from http.client import HTTPConnection, HTTPException
from ipaddress import IPv4Address
import json
from pathlib import Path
import re
import warnings

import serial

from .network_setup import wait_for_firmware, wait_message


OTA_PORT = 8081
OTA_PATH = "/api/v1/ota"
MAX_FIRMWARE_BYTES = 0x140000
DEFAULT_FIRMWARE = Path(".pio/build/esp32dev-alexa-temperature/firmware.bin")


def read_key(confirm=False):
    with warnings.catch_warnings():
        warnings.simplefilter("error", GetPassWarning)
        key = getpass("Clé OTA : ")
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", key):
            raise ValueError("Saisis la clé OTA de 43 caractères générée avec secrets.token_urlsafe(32).")
        if confirm and key != getpass("Confirme la clé OTA : "):
            raise ValueError("Les deux saisies sont différentes.")
    return key


def configure(port_name, key):
    command = b"!OTA CLEAR\n" if key is None else f"!OTA SET {key}\n".encode("ascii")
    with serial.Serial(port_name, 115200, timeout=.2, write_timeout=2) as port:
        port.dtr = port.rts = False
        wait_for_firmware(port)
        port.write(command)
        response = wait_message(port, "ota_config", 5)
    if response is None:
        raise ValueError("Configuration OTA non confirmée. Vérifie que la carte utilise la variante OTA.")
    if response.get("result") != "saved":
        raise ValueError("La carte a refusé d’enregistrer la configuration OTA.")


def read_firmware(path):
    with path.open("rb") as binary:
        firmware = binary.read(MAX_FIRMWARE_BYTES + 1)
    if len(firmware) > MAX_FIRMWARE_BYTES:
        raise ValueError("Le fichier dépasse la taille d’un emplacement OTA (1,25 Mio).")
    if firmware[:1] != b"\xe9" or firmware[32:36] != b"\x32\x54\xcd\xab":
        raise ValueError("Sélectionne le fichier firmware.bin compilé pour l’ESP32.")
    return firmware


def read_response(connection):
    with connection.getresponse() as response:
        if response.status != 200:
            reasons = {
                400: "taille ou requête invalide",
                403: "clé refusée, demande expirée ou accès interdit",
                409: "radio occupée",
                422: "image refusée ou écriture interrompue",
                503: "emplacement OTA indisponible",
            }
            reason = reasons.get(response.status, "réponse inattendue")
            raise ValueError(f"ESP32 a refusé la requête OTA (HTTP {response.status}, {reason}).")
        try:
            data = json.loads(response.read(1025))
        except (ValueError, RecursionError) as exc:
            raise ValueError("Réponse OTA illisible.") from exc
        if not isinstance(data, dict):
            raise ValueError("Réponse OTA inattendue.")
        return data


def upload(ip, firmware, key):
    connection = HTTPConnection(str(ip), OTA_PORT, timeout=10)
    try:
        connection.request("GET", f"{OTA_PATH}/challenge")
        nonce = read_response(connection).get("nonce")
        if not isinstance(nonce, str) or not re.fullmatch(r"[0-9a-f]{32}", nonce):
            raise ValueError("L’ESP32 n’a pas fourni de demande OTA valide.")
        digest = hashlib.sha256(firmware).hexdigest()
        message = f"mcz-ota-v1:{nonce}:{digest}".encode("ascii")
        mac = hmac.digest(key.encode("ascii"), message, "sha256").hex()
        headers = {
            "Content-Type": "application/octet-stream",
            "X-MCZ-Nonce": nonce,
            "X-MCZ-SHA256": digest,
            "X-MCZ-MAC": mac,
        }
        connection.timeout = 100
        if connection.sock is not None:
            connection.sock.settimeout(100)
        try:
            connection.request("POST", OTA_PATH, body=firmware, headers=headers)
            result = read_response(connection)
        except (OSError, HTTPException) as exc:
            raise ValueError("Téléversement non confirmé. Vérifie si l’ESP32 a redémarré avant de recommencer.") from exc
        if result.get("result") != "rebooting":
            raise ValueError("Redémarrage non confirmé. Vérifie l’état de la carte avant de recommencer.")
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    setup = actions.add_parser("configure", help="enregistrer une clé OTA par USB")
    setup.add_argument("--port", default="COM3")
    forget = actions.add_parser("forget", help="effacer la clé OTA par USB")
    forget.add_argument("--port", default="COM3")
    send = actions.add_parser("upload", help="envoyer firmware.bin à l’ESP32 par Wi-Fi")
    send.add_argument("ip", type=IPv4Address)
    send.add_argument("--firmware", type=Path, default=DEFAULT_FIRMWARE)
    args = parser.parse_args()

    try:
        if args.action == "upload":
            firmware = read_firmware(args.firmware)
            upload(args.ip, firmware, read_key())
            print("Firmware vérifié et installé. L’ESP32 redémarre.")
        elif args.action == "configure":
            configure(args.port, read_key(confirm=True))
            print("Clé OTA enregistrée. Le service OTA démarre dès que l’ESP32 est connecté au Wi-Fi.")
        else:
            configure(args.port, None)
            print("Clé effacée. Le téléversement Wi-Fi est désactivé.")
    except (ValueError, OSError, HTTPException, GetPassWarning) as exc:
        parser.exit(2, f"MCZ : {exc}\n")
    except (KeyboardInterrupt, EOFError):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
