"""Configure or inspect the ESP32 Wi-Fi over USB, without sending radio commands."""
import argparse
from getpass import GetPassWarning, getpass
import json
import re
import time
import warnings

import serial


def wait_message(port, kind, timeout):
    deadline = time.monotonic() + timeout
    pending = bytearray()
    dropping = False
    while time.monotonic() < deadline:
        chunk = port.readline(512)
        if not dropping:
            pending.extend(chunk)
            dropping = len(pending) > 512
        if not chunk.endswith(b"\n"):
            continue
        if not dropping and pending.startswith(b"APP "):
            try:
                message = json.loads(pending[4:])
                if isinstance(message, dict) and message.get("type") == kind:
                    return message
            except (ValueError, RecursionError):
                pass
        pending.clear()
        dropping = False
    return None


def status(port, timeout=1):
    port.write(b"!NET\n")
    return wait_message(port, "network", timeout)


def credentials():
    ssid = input("Nom du Wi-Fi 2,4 GHz : ").encode()
    with warnings.catch_warnings():
        warnings.simplefilter("error", GetPassWarning)
        password = getpass("Mot de passe Wi-Fi : ")
        key = getpass("Clé API (64 caractères hexadécimaux minuscules) : ")
    if not 1 <= len(ssid) <= 32 or b"\0" in ssid:
        raise ValueError("Le SSID doit contenir de 1 à 32 octets.")
    if not re.fullmatch(r"[ -~]{8,63}", password):
        raise ValueError("Le mot de passe WPA2 doit contenir de 8 à 63 caractères ASCII imprimables.")
    if not re.fullmatch("[0-9a-f]{64}", key):
        raise ValueError("La clé API doit contenir 64 caractères hexadécimaux minuscules.")
    return f"!WIFI {ssid.hex()} {password.encode().hex()} {key}\n".encode("ascii")


def show_status(state):
    if state["connected"]:
        print(f"Page de commande : http://{state['ip']}/")
        print(f"API Wi-Fi : http://{state['ip']}/api/v1/status")
    elif state["configured"]:
        print("Wi-Fi enregistré, connexion non établie.")
    else:
        print("Wi-Fi désactivé.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="COM3")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--status", action="store_true")
    action.add_argument("--forget", action="store_true")
    args = parser.parse_args()
    try:
        command = None if args.status else b"!WIFI CLEAR\n" if args.forget else credentials()
        with serial.Serial(args.port, 115200, timeout=.2, write_timeout=2) as port:
            port.dtr = port.rts = False
            # Opening USB can reboot the ESP32. Only status queries may be repeated.
            state = None
            for _ in range(4):
                state = status(port)
                if state is not None:
                    break
            if state is None:
                raise ValueError("Firmware API v1 non détecté sur ce port.")
            if command is None:
                show_status(state)
                return 0
            port.write(command)
            result = wait_message(port, "network_config", 5)
            if result is None or result.get("result") != "saved":
                raise ValueError("Configuration non confirmée. Vérifie le statut avant de recommencer.")
            for _ in range(25):
                state = status(port)
                if state is not None and (args.forget or state["connected"]):
                    show_status(state)
                    return 0
                time.sleep(1)
            print("Wi-Fi enregistré. Vérifie le SSID, le mot de passe et le signal avec --status.")
            return 1
    except (ValueError, OSError, serial.SerialException, GetPassWarning) as exc:
        parser.exit(2, f"MCZ : {exc}\n")
    except (KeyboardInterrupt, EOFError):
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
