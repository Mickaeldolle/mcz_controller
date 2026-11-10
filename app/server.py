"""Serve the PC-only control page: python -m app.server --serial-port COM3."""
import argparse
import csv
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
from urllib.parse import urlsplit
from .bridge import Bridge

WEB = Path(__file__).with_name("web")


def make_handler(bridge, token, port):
    host = f"127.0.0.1:{port}"
    origin = f"http://{host}"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def send(self, code, payload, content_type="application/json; charset=utf-8"):
            body = json.dumps(payload, ensure_ascii=False).encode() if isinstance(payload, (dict, list)) else payload
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def allowed(self):
            return self.headers.get("Host") == host and self.headers.get("Sec-Fetch-Site") not in ("cross-site",)

        def do_GET(self):
            if not self.allowed():
                return self.send(403, {"error": "Accès local uniquement"})
            path = urlsplit(self.path).path
            if path == "/api/status":
                return self.send(200, {**bridge.status(), "token": token})
            files = {"/": ("index.html", "text/html; charset=utf-8"),
                     "/style.css": ("style.css", "text/css; charset=utf-8"),
                     "/app.js": ("app.js", "text/javascript; charset=utf-8")}
            if path not in files:
                return self.send(404, {"error": "Page inconnue"})
            name, mime = files[path]
            return self.send(200, (WEB / name).read_bytes(), mime)

        def do_POST(self):
            if (not self.allowed() or self.headers.get("Origin") != origin
                    or not secrets.compare_digest(self.headers.get("X-MCZ-Token", "").encode("utf-8"), token.encode("utf-8"))):
                return self.send(403, {"error": "Origine ou jeton invalide"})
            if self.path != "/api/command":
                return self.send(404, {"error": "Route inconnue"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 256 or self.headers.get_content_type() != "application/json":
                    raise ValueError()
                self.connection.settimeout(3)
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict) or set(data) not in ({"action", "id"}, {"action", "id", "profile"}):
                    raise ValueError()
                if data["action"] not in ("on", "off") or not isinstance(data["id"], str) or not re.fullmatch("[0-9a-f]{32}", data["id"]):
                    raise ValueError()
                profile = data.get("profile")
                if "profile" in data and (not isinstance(profile, str)
                                          or not re.fullmatch(r"off|[1-5]:[1-6](?::[0-6])?", profile)
                                          or (profile == "off") != (data["action"] == "off")):
                    raise ValueError()
            except (ValueError, TypeError, OSError, RecursionError):
                return self.send(400, {"error": "Commande invalide"})
            result = (
                bridge.command(data["action"], data["id"], profile=profile)
                if profile is not None else bridge.command(data["action"], data["id"])
            )
            return self.send(200, result)

    return Handler


def main(open_browser=False):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial-port", default="COM3")
    parser.add_argument("--http-port", type=int, default=8765)
    args = parser.parse_args()
    if not 1024 <= args.http_port <= 65535:
        parser.error("Port HTTP invalide")
    try:
        bridge = Bridge(args.serial_port)
    except (OSError, ValueError, csv.Error) as exc:
        parser.exit(2, f"Catalogue indisponible : {exc}\n")
    server = ThreadingHTTPServer(("127.0.0.1", args.http_port), make_handler(bridge, secrets.token_hex(32), args.http_port))
    bridge.start()
    print(f"MCZ : http://127.0.0.1:{args.http_port} — USB {args.serial_port}", flush=True)
    if open_browser:
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{args.http_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        bridge.close()


if __name__ == "__main__":
    main()
