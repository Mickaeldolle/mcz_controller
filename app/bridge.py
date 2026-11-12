"""Exclusive USB owner. Read/status traffic never transmits RF."""
import json
import threading
import time
import serial

from .catalog import DEFAULT_ON, MCZ_FREQUENCY_HZ, load_command_presets


class Bridge:
    def __init__(self, port, presets=None):
        self.port_name = port
        self.presets = load_command_presets() if presets is None else dict(presets)
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
        self.ambient = None
        self.thread = threading.Thread(target=self._read, daemon=True)

    def start(self):
        self.thread.start()

    def status(self):
        with self.lock:
            now = time.monotonic()
            fresh = now - self.seen < 5
            status = {"connected": self.ready and fresh,
                    "busy": self.pending is not None,
                    "cooldown": max(0, 3 - (now - self.last_send)),
                    "profiles_ready": DEFAULT_ON in self.presets and "off" in self.presets,
                    "presets": sorted(self.presets), "last": self.last,
                    "port": self.port_name, "tx_count": self.tx_count}
            if fresh and self.ambient is not None:
                status["ambient"] = dict(self.ambient)
            return status

    def command(self, action, request_id, profile=None):
        if action not in ("on", "off"):
            return {"result": "rejected"}
        if profile is None:
            profile = "off" if action == "off" else DEFAULT_ON
        with self.lock:
            if request_id in self.results:
                old = self.results[request_id]
                if old["action"] != action or old.get("profile") != profile:
                    return {"result": "rejected"}
                return dict(old)
            if action == ("off" if profile == "off" else "on"):
                frame = self.presets.get(profile)
            else:
                frame = None
            if frame is None:
                return {"result": "rejected"}
            if self.pending or time.monotonic() - self.last_send < 3:
                return {"result": "busy"}
            if not self.ready or time.monotonic() - self.seen >= 5 or self.device is None:
                return {"result": "unavailable"}
            self.pending = request_id
            self.wake.clear()
            self.last_send = time.monotonic()
            entry = {"id": request_id, "action": action, "profile": profile, "result": "uncertain"}
            # Reserve ID BEFORE writing: a timeout or USB failure must never retry it.
            self.results[request_id] = entry
            device = self.device
        try:
            with self.wire_lock:
                device.write(f"!TX {request_id} {frame}\n".encode("ascii"))
            self.wake.wait(4)
        except (serial.SerialException, OSError):
            pass
        finally:
            with self.lock:
                self.last = dict(entry)
                self.pending = None
                # Bound history; IDs are random, never reused by the UI.
                if len(self.results) > 512:
                    del self.results[next(iter(self.results))]
                result = dict(entry)
        return result

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
                    self.ambient = None
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
                self.ready = msg.get("ready") is True and msg.get("frequency") == MCZ_FREQUENCY_HZ
                self.seen = time.monotonic()
                self.tx_count = msg.get("tx_count")
                ambient = msg.get("ambient")
                self.ambient = None
                if isinstance(ambient, dict):
                    self.ambient = {}
                    for name, maximum in (("temperature_c", 50), ("humidity_pct", 100)):
                        value = ambient.get(name)
                        self.ambient[name] = value if type(value) is int and 0 <= value <= maximum else None
            elif self.pending is not None and msg.get("type") == "result" and msg.get("id") == self.pending:
                result = msg.get("result")
                if result in ("sent", "uncertain", "busy", "unavailable", "rejected"):
                    self.results[self.pending]["result"] = result
                    self.wake.set()

    def close(self):
        self.stop.set()
        self.thread.join(timeout=3)
