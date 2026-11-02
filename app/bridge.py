"""Exclusive USB owner. Read/status traffic never transmits RF."""
import binascii
import json
from pathlib import Path
import threading
import time
import serial

ROOT = Path(__file__).resolve().parents[1]


def load_profiles(path=ROOT / "config/power_profiles.json"):
    profiles = json.loads(path.read_text(encoding="utf-8"))
    for action in ("on", "off"):
        raw = bytes.fromhex(profiles[action])
        if len(raw) != 7 or raw[:3].hex().upper() != "C8CC02":
            raise ValueError("Identifiant ou longueur de trame invalide")
        if binascii.crc_hqx(raw[:5], 0) != int.from_bytes(raw[5:], "big"):
            raise ValueError("CRC invalide")
        if (raw[3] & 3 == 0) != (action == "off"):
            raise ValueError("Mode de commande incohérent")
        # The firmware accepts exactly 14 hex characters, without separators.
        profiles[action] = raw.hex().upper()
    return profiles


class Bridge:
    def __init__(self, port, profiles=None):
        self.port_name = port
        self.profiles = load_profiles() if profiles is None else profiles
        self.lock = threading.Lock()
        self.wire_lock = threading.Lock()
        self.wake = threading.Event()
        self.stop = threading.Event()
        self.device = None
        self.ready = False
        self.seen = 0.0
        self.pending = None
        self.results = {}
        self.last_send = 0.0
        self.last = None
        self.tx_count = None
        self.thread = threading.Thread(target=self._read, daemon=True)

    def start(self):
        self.thread.start()

    def status(self):
        with self.lock:
            return {"connected": self.ready and time.monotonic() - self.seen < 5,
                    "busy": self.pending is not None,
                    "cooldown": max(0, 3 - (time.monotonic() - self.last_send)),
                    "profiles_ready": bool(self.profiles), "last": self.last,
                    "port": self.port_name, "tx_count": self.tx_count}

    def command(self, action, request_id):
        with self.lock:
            if request_id in self.results:
                old = self.results[request_id]
                if old["action"] != action:
                    return {"result": "rejected"}
                return dict(old)
            if self.pending or time.monotonic() - self.last_send < 3:
                return {"result": "busy"}
            if not self.ready or time.monotonic() - self.seen >= 5 or self.device is None:
                return {"result": "unavailable"}
            self.pending = request_id
            self.wake.clear()
            self.last_send = time.monotonic()
            entry = {"id": request_id, "action": action, "result": "uncertain"}
            # Reserve ID BEFORE writing: a timeout or USB failure must never retry it.
            self.results[request_id] = entry
            device = self.device
        try:
            with self.wire_lock:
                device.write(f"!TX {request_id} {self.profiles[action]}\n".encode("ascii"))
            self.wake.wait(4)
        except (serial.SerialException, OSError, KeyError):
            pass
        finally:
            with self.lock:
                self.last = dict(entry)
                self.pending = None
                # Bound history; IDs are random, never reused by the UI.
                if len(self.results) > 512:
                    del self.results[next(iter(self.results))]
        return dict(entry)

    def _read(self):
        while not self.stop.is_set():
            try:
                with serial.Serial(self.port_name, 115200, timeout=0.2, write_timeout=1) as port:
                    port.dtr = False
                    port.rts = False
                    with self.lock:
                        self.device = port
                    next_poll = time.monotonic() + 2
                    partial = bytearray()
                    dropping = False
                    while not self.stop.is_set():
                        chunk = port.readline(2048)
                        # readline may return a fragment on its 200 ms timeout.
                        # Keep it until LF; discard oversized lines through LF.
                        if not dropping:
                            partial.extend(chunk)
                            if len(partial) > 2048:
                                partial.clear()
                                dropping = True
                        if chunk.endswith(b"\n"):
                            if not dropping:
                                self._handle_line(bytes(partial))
                            partial.clear()
                            dropping = False
                        if time.monotonic() >= next_poll:
                            with self.wire_lock:
                                port.write(b"j")
                            next_poll = time.monotonic() + 1
            except (serial.SerialException, OSError):
                pass
            finally:
                with self.lock:
                    self.device = None
                    self.ready = False
                self.wake.set()
            self.stop.wait(2)

    def _handle_line(self, line):
        if not line.startswith(b"APP "):
            return
        try:
            msg = json.loads(line[4:])
        except (ValueError, TypeError, RecursionError):
            return
        if not isinstance(msg, dict):
            return
        with self.lock:
            if msg.get("type") == "status":
                self.ready = msg.get("ready") is True and msg.get("frequency") == 434500000
                self.seen = time.monotonic()
                self.tx_count = msg.get("tx_count")
            elif self.pending is not None and msg.get("type") == "result" and msg.get("id") == self.pending:
                result = msg.get("result")
                if result in ("sent", "uncertain", "busy", "unavailable", "rejected"):
                    self.results[self.pending]["result"] = result
                    self.wake.set()

    def close(self):
        self.stop.set()
        self.thread.join(timeout=3)
