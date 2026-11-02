"""UI verification only: this process NEVER opens USB or imports a radio bridge."""
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import time
import json
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.server import make_handler


class Preview:
    def __init__(self):
        self.until = 0
    def status(self):
        state = self.state()
        return {"connected": state.get("connected", True), "profiles_ready": True, "busy": False,
                "cooldown": max(0, self.until-time.monotonic()), "port": "SIMULATION", "last": None, "preview": True}
    def command(self, action, request_id):
        self.until = time.monotonic()+3
        time.sleep(0.5)
        return {"result": self.state().get("result", "sent"), "simulation": True}
    def state(self):
        try:
            return json.loads((Path(__file__).resolve().parents[1]/".pio/preview-state.json").read_text())
        except (OSError, ValueError):
            return {}


if __name__ == "__main__":
    print("PREVIEW ONLY, NO USB — http://127.0.0.1:8766", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8766), make_handler(Preview(), "preview-token", 8766)).serve_forever()
