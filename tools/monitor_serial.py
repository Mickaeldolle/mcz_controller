"""Live MCZ receive monitor. Only sends the firmware's read-only j/s queries."""
import argparse
import binascii
from datetime import datetime
import json
from pathlib import Path
import re
import time

import serial

ROOT = Path(__file__).resolve().parents[1]
KNOWN = {"C8CC028FB88E16": "Allumer enregistre", "C8CC028CB8DB45": "Eteindre enregistre"}


class Lines:
    """Keep timeout fragments, discarding an oversized line through its LF."""
    def __init__(self):
        self.pending = bytearray()
        self.dropping = False

    def feed(self, data):
        for byte in data:
            if byte == 10:
                if not self.dropping:
                    yield self.pending.decode("ascii", errors="replace").strip()
                self.pending.clear()
                self.dropping = False
            elif not self.dropping:
                self.pending.append(byte)
                if len(self.pending) > 2048:
                    self.pending.clear()
                    self.dropping = True


class Monitor:
    def __init__(self, emit):
        self.emit = emit
        self.count = 0
        self.last_frame = None
        self.last_status = None
        self.status_seen = None

    def receive(self, line, now):
        if line.startswith("Raw:"):
            value = line[4:].strip()
            if not re.fullmatch(r"[0-9A-Fa-f]{2}(?:\s+[0-9A-Fa-f]{2}){6}", value):
                self.emit("ATTENTION : trame USB mal formee : " + value)
                return
            raw = bytes.fromhex(value)
            if binascii.crc_hqx(raw[:5], 0) != int.from_bytes(raw[5:], "big"):
                self.emit("ATTENTION : CRC invalide : " + raw.hex(" ").upper())
                return
            self.count += 1
            gap = "premiere" if self.last_frame is None else f"+{(now - self.last_frame) * 1000:.0f} ms"
            label = KNOWN.get(raw.hex().upper(), "autre trame")
            self.emit(f"RX #{self.count:04d}  {gap:>10}  {raw.hex(' ').upper()}  [{label}] CRC=OK")
            self.last_frame = now
        elif line.startswith("APP "):
            try:
                status = json.loads(line[4:])
            except (ValueError, RecursionError):
                return
            if not isinstance(status, dict) or status.get("type") != "status":
                return
            self.status_seen = now
            state = (status.get("ready") is True, status.get("frequency"), status.get("tx_count"))
            if state != self.last_status:
                ready, frequency, count = state
                self.emit(f"USB : RX {'PRET' if ready else 'INDISPONIBLE'} | frequence={frequency} Hz | compteur TX={count}")
                self.last_status = state
        elif any(word in line for word in ("RX READY", "STATE=", "ERREUR", "ERROR", "STOP:", "DROPPED", "BUFFER FULL")):
            self.emit(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="COM3")
    parser.add_argument("--seconds", type=float, help="Optional duration, otherwise listen until Ctrl+C")
    args = parser.parse_args()
    if args.seconds is not None and (not 0 < args.seconds <= 86400):
        parser.error("--seconds doit etre compris entre 0 et 86400")
    folder = ROOT / "captures"
    folder.mkdir(exist_ok=True)
    path = folder / (datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "_live.log")
    try:
        with path.open("x", encoding="utf-8", buffering=1) as log:
            def emit(message):
                stamp = datetime.now().astimezone().isoformat(timespec="milliseconds")
                output = f"{stamp}  {message}"
                print(output, flush=True)
                log.write(output + "\n")

            emit(f"MCZ - ECOUTE SEULE sur {args.port}. Ctrl+C pour arreter.")
            emit("Chaque RX est une trame ; un appui peut produire 5 repetitions.")
            emit("Heure et delais mesures sur le PC apres decodage et transport USB, pas a l'antenne.")
            emit("L'ouverture USB peut redemarrer l'ESP32. Aucun ordre Allumer/Eteindre n'est envoye.")
            emit(f"Journal : {path}")
            monitor = Monitor(emit)
            # Python 3.11 on Windows uses coarse GetTickCount64 for monotonic.
            # perf_counter keeps RX intervals precise and uses one clock here.
            deadline = None if args.seconds is None else time.perf_counter() + args.seconds
            disconnected = False
            try:
                while deadline is None or time.perf_counter() < deadline:
                    try:
                        with serial.Serial(args.port, 115200, timeout=0.1, write_timeout=1) as port:
                            port.dtr = False
                            port.rts = False
                            if disconnected:
                                emit("USB rouvert. Nouvelle verification du recepteur.")
                            disconnected = False
                            monitor.last_frame = None
                            monitor.last_status = None
                            monitor.status_seen = None
                            lines = Lines()
                            started = time.perf_counter()
                            poll_at, heartbeat_at = started + 2, started + 10
                            while deadline is None or time.perf_counter() < deadline:
                                data = port.read(min(port.in_waiting or 1, 4096))
                                for line in lines.feed(data):
                                    monitor.receive(line, time.perf_counter())
                                now = time.perf_counter()
                                if now >= poll_at:
                                    # Firmware status queries, never a radio command.
                                    port.write(b"js" if poll_at == started + 2 else b"j")
                                    poll_at = now + 2
                                if now >= heartbeat_at:
                                    healthy = monitor.status_seen is not None and now - monitor.status_seen < 5
                                    emit(f"En ecoute... {monitor.count} trame(s) | statut USB {'recent' if healthy else 'sans reponse recente'}")
                                    heartbeat_at = now + 10
                    except (serial.SerialException, OSError) as exc:
                        if not disconnected:
                            emit(f"USB indisponible : {exc}")
                            emit("Fermer l'application MCZ et les autres outils utilisant ce port. Nouvel essai automatique.")
                        disconnected = True
                        remaining = 2 if deadline is None else max(0, min(2, deadline - time.perf_counter()))
                        time.sleep(remaining)
            except KeyboardInterrupt:
                pass
            finally:
                emit(f"Ecoute terminee. {monitor.count} trame(s) valide(s). Port USB libere.")
    except OSError as exc:
        parser.exit(1, f"Journal inaccessible : {exc}\n")


if __name__ == "__main__":
    main()
