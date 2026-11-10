import http.client
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.bridge import Bridge
from app.catalog import CATALOG, ROOT, load_command_presets, load_presets, validate_frame
from app.server import make_handler


class Device:
    def __init__(self, bridge):
        self.bridge = bridge
        self.writes = []

    def write(self, data):
        self.writes.append(data)
        with self.bridge.lock:
            self.bridge.results[self.bridge.pending]["result"] = "sent"
            self.bridge.wake.set()


class BridgeTests(unittest.TestCase):
    def test_malformed_usb_messages_do_not_stop_reader(self):
        b = Bridge("FAKE")
        for payload in (b"[]", b"null", b"true", b"42", b'"text"', b"{", b"\xff",
                        b"[" * 1000 + b"0" + b"]" * 1000,
                        b'{"type":"result","result":"sent"}'):
            b._handle_line(b"APP " + payload + b"\n")
        b._handle_line(b'APP {"type":"status","ready":true,"frequency":434500000,"tx_count":0}\n')
        self.assertTrue(b.status()["connected"])
        self.assertEqual(b.status()["tx_count"], 0)
        self.assertFalse(b.results)

    def test_reader_handles_fragments_and_discards_oversized_lines(self):
        b = Bridge("FAKE")
        observations = []
        chunks = iter([
            b"APP []\n",
            b'APP {"type":"status","ready":true,', b"", b'"frequency":434500000,"tx_count":0}\n',
            b"x" * 2048, b"x", b'APP {"type":"status","ready":false}\n',
            b'APP {"type":"status","ready":false,"frequency":434500000}\n',
        ])

        class Port:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def readline(self, limit):
                observations.append(b.status()["connected"])
                try:
                    return next(chunks)
                except StopIteration:
                    b.stop.set()
                    return b""

            def write(port, data):
                self.assertEqual(data, b"j")

        with patch("app.bridge.serial.Serial", return_value=Port()):
            b._read()
        self.assertEqual(observations, [False, False, False, False, True, True, True, True, False])
        self.assertIsNone(b.device)

    def test_disconnect_wakes_pending_command_without_retry(self):
        b = Bridge("FAKE")
        b.ready = True
        b.pending = "a" * 32
        with patch("app.bridge.serial.Serial", side_effect=OSError("USB unplugged")) as serial:
            # End the reconnect delay immediately, after checking cleanup.
            with patch.object(b.stop, "wait", side_effect=lambda _: b.stop.set()):
                b._read()
        self.assertTrue(b.wake.is_set())
        self.assertFalse(b.ready)
        self.assertIsNone(b.device)
        serial.assert_called_once()

    def test_profiles_and_real_capture(self):
        presets = load_presets()
        self.assertEqual(set(presets), {
            "off", *(f"{n}:1" for n in range(1, 6)), *(f"5:{n}" for n in range(2, 7)),
            *(f"3:5:{n}" for n in range(7)),
        })
        self.assertEqual(presets["1:1"], "C8CC0225B87CA3")
        self.assertEqual(presets["off"], "C8CC0224B84F92")
        self.assertEqual(presets["5:6"], "C8CC02D5B86F62")
        self.assertEqual(presets["3:5:0"], "C8CC02AD8059C9")
        self.assertEqual(presets["3:5:1"], "C8CC02AD88D8C1")
        self.assertEqual(presets["3:5:6"], "C8CC02ADB06F9A")

    def test_derived_profiles_preserve_captures_and_cover_manual_ranges(self):
        captures = load_presets()
        presets = load_command_presets()
        self.assertEqual(len(presets), 221)
        self.assertEqual(len(set(presets.values())), len(presets))
        for profile, frame in captures.items():
            self.assertEqual(presets[profile], frame)

        for power in range(1, 6):
            for fan1 in range(1, 7):
                for fan2 in range(7):
                    raw = validate_frame(presets[f"{power}:{fan1}:{fan2}"])
                    self.assertEqual((raw[3] & 3, (raw[3] >> 2) & 7, raw[3] >> 5), (1, power, fan1))
                    self.assertEqual(((raw[4] >> 3) & 7, raw[4] & 0xC7), (fan2, 0x80))

        with patch("app.catalog.load_presets", return_value={"off": captures["off"], "1:1": captures["1:1"]}):
            self.assertEqual(set(load_command_presets()), {"off", "1:1"})

    def test_construct_and_offline_never_write(self):
        with patch("app.bridge.serial.Serial") as serial:
            b = Bridge("FAKE")
            self.assertEqual(b.command("on", "a"*32)["result"], "unavailable")
            self.assertFalse(b.status()["connected"])
            serial.assert_not_called()

    def test_duplicate_exactly_once_and_no_action_change(self):
        b = Bridge("FAKE")
        b.device = Device(b)
        b.ready = True
        b.seen = time.monotonic()
        self.assertEqual(b.command("off", "a"*32)["result"], "sent")
        self.assertEqual(b.command("off", "a"*32)["result"], "sent")
        self.assertEqual(b.command("on", "a"*32)["result"], "rejected")
        self.assertEqual(b.command("on", "b"*32)["result"], "busy")
        self.assertEqual(len(b.device.writes), 1)
        self.assertIn(b"C8CC0224B84F92", b.device.writes[0])

    def test_failure_not_retried(self):
        b = Bridge("FAKE")
        b.device = Device(b)
        b.device.write = lambda data: (_ for _ in ()).throw(OSError("USB unplugged"))
        b.ready = True
        b.seen = time.monotonic()
        self.assertEqual(b.command("on", "a"*32)["result"], "uncertain")
        b.device.write = lambda data: self.fail("Must not retry")
        self.assertEqual(b.command("on", "a"*32)["result"], "uncertain")

    def test_captured_settings_use_only_the_selected_frame(self):
        b = Bridge("FAKE", presets={"1:1": "C8CC0225B87CA3", "3:5:0": "C8CC02AD8059C9", "off": "C8CC0224B84F92"})
        b.device = Device(b)
        b.ready = True
        b.seen = time.monotonic()
        self.assertEqual(b.command("on", "a"*32, "1:6")["result"], "rejected")
        self.assertEqual(b.command("off", "a"*32, "1:1")["result"], "rejected")
        self.assertEqual(b.command("on", "a"*32, "1:1:0")["result"], "rejected")
        self.assertEqual(b.command("on", "a"*32, "3:5:0")["result"], "sent")
        self.assertEqual(b.command("on", "a"*32, "3:5:0")["result"], "sent")
        self.assertEqual(b.command("on", "a"*32, "1:1")["result"], "rejected")
        self.assertEqual(b.device.writes, [b"!TX " + b"a"*32 + b" C8CC02AD8059C9\n"])

    def test_catalog_rejects_valid_frame_in_wrong_capture_group(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalogue.csv"
            data = CATALOG.read_text(encoding="utf-8-sig")
            path.write_text(data.replace("C8CC0225B87CA3", "C8CC0229B839CE", 1), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "groupe RX"):
                load_presets(path, root=ROOT)

    def test_timeout_and_late_reply_never_retry(self):
        b = Bridge("FAKE")
        b.device = Device(b)
        writes = []
        b.device.write = writes.append
        b.ready = True
        b.seen = time.monotonic()
        with patch.object(b.wake, "wait", return_value=False):
            self.assertEqual(b.command("on", "a"*32)["result"], "uncertain")
        b._handle_line(('APP ' + json.dumps({"type": "result", "id": "a"*32, "result": "sent"})).encode())
        self.assertEqual(b.command("on", "a"*32)["result"], "uncertain")
        self.assertEqual(len(writes), 1)

    def test_concurrent_requests_cannot_duplicate_or_queue(self):
        b = Bridge("FAKE")
        b.device = Device(b)
        b.ready = True
        b.seen = time.monotonic()
        entered = threading.Event()
        release = threading.Event()
        writes = []
        completed = []

        def write(data):
            writes.append(data)
            entered.set()
            release.wait(2)
            b._handle_line(('APP ' + json.dumps({"type": "result", "id": "a"*32, "result": "sent"})).encode())

        b.device.write = write
        worker = threading.Thread(target=lambda: completed.append(b.command("on", "a"*32)))
        worker.start()
        try:
            self.assertTrue(entered.wait(2))
            duplicate = b.command("on", "a"*32)
            self.assertEqual(duplicate["result"], "uncertain")
            self.assertEqual(b.command("off", "b"*32)["result"], "busy")
            self.assertEqual(b.command("off", "a"*32)["result"], "rejected")
        finally:
            release.set()
            worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(completed[0]["result"], "sent")
        self.assertEqual(duplicate["result"], "uncertain")
        self.assertEqual(len(writes), 1)


class FakeBridge:
    def __init__(self):
        self.commands = []

    def status(self):
        return {"connected": True, "busy": False, "cooldown": 0, "profiles_ready": True, "last": None, "port": "FAKE"}

    def command(self, action, request_id, profile=None):
        self.commands.append((action, request_id) if profile is None else (action, request_id, profile))
        return {"result": "sent"}


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), lambda *a: None)
        self.port = self.server.server_port
        self.server.RequestHandlerClass = make_handler(self.bridge, "test-token", self.port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, data=None, extra=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Origin": f"http://127.0.0.1:{self.port}", "X-MCZ-Token": "test-token", "Content-Type": "application/json"}
        headers.update(extra or {})
        c.request(method, path, json.dumps(data) if data is not None else None, headers)
        response = c.getresponse()
        code, body = response.status, response.read()
        c.close()
        return code, body

    def test_get_and_start_have_no_side_effect(self):
        for path in ("/", "/api/status", "/app.js", "/style.css"):
            self.assertEqual(self.request("GET", path)[0], 200)
        self.assertEqual(self.bridge.commands, [])

    def test_valid_command(self):
        self.assertEqual(self.request("POST", "/api/command", {"action": "off", "id": "a"*32})[0], 200)
        self.assertEqual(self.bridge.commands, [("off", "a"*32)])

    def test_captured_profile_contract(self):
        valid = {"action": "on", "id": "a"*32}
        for profile in ("1:7", "0:1", "3:5:7", "3:5:0:1", "off", None, "C8CC0225B87CA3"):
            self.assertEqual(self.request("POST", "/api/command", {**valid, "profile": profile})[0], 400)
        self.assertEqual(self.request("POST", "/api/command", {**valid, "profile": "5:6"})[0], 200)
        self.assertEqual(self.request("POST", "/api/command", {**valid, "id": "b"*32, "profile": "3:5:0"})[0], 200)
        self.assertEqual(self.bridge.commands, [("on", "a"*32, "5:6"), ("on", "b"*32, "3:5:0")])

    def test_reject_foreign_origin_host_and_bad_input(self):
        valid = {"action": "on", "id": "a"*32}
        for headers in ({"Origin": "https://example.org"}, {"Host": "example.org"},
                        {"X-MCZ-Token": "wrong"}, {"X-MCZ-Token": "é"},
                        {"Sec-Fetch-Site": "cross-site"}):
            self.assertEqual(self.request("POST", "/api/command", valid, headers)[0], 403)
        for data in ({"action": "toggle", "id": "a"*32}, {"action": "on", "id": "../"}, [], {**valid, "raw": "1234"}):
            self.assertEqual(self.request("POST", "/api/command", data)[0], 400)
        self.assertEqual(self.bridge.commands, [])


if __name__ == "__main__":
    unittest.main()
