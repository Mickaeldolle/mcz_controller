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
from app.bridge import Bridge, load_profiles
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
    def test_profiles_are_normalized_for_firmware(self):
        profiles = load_profiles()
        for action in ("on", "off"):
            profiles[action] = bytes.fromhex(profiles[action]).hex(" ").lower()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "profiles.json"
            path.write_text(json.dumps(profiles), encoding="utf-8")
            loaded = load_profiles(path)
        self.assertEqual(loaded["on"], "C8CC028FB88E16")
        self.assertEqual(loaded["off"], "C8CC028CB8DB45")

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
        p = load_profiles()
        log = (Path(__file__).resolve().parents[1] / p["source"]).read_text()
        for action in ("on", "off"):
            raw = " ".join(p[action][i:i+2] for i in range(0, 14, 2))
            self.assertEqual(log.count("Raw: " + raw), 5)

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
        self.assertIn(b"C8CC028CB8DB45", b.device.writes[0])

    def test_failure_not_retried(self):
        b = Bridge("FAKE")
        b.device = Device(b)
        b.device.write = lambda data: (_ for _ in ()).throw(OSError("USB unplugged"))
        b.ready = True
        b.seen = time.monotonic()
        self.assertEqual(b.command("on", "a"*32)["result"], "uncertain")
        b.device.write = lambda data: self.fail("Must not retry")
        self.assertEqual(b.command("on", "a"*32)["result"], "uncertain")

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

    def command(self, action, request_id):
        self.commands.append((action, request_id))
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
