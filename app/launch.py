"""Open an existing local instance, or start one in this console."""
import json
import urllib.error
import urllib.request
import webbrowser
from . import server

URL = "http://127.0.0.1:8765"


def main():
    try:
        with urllib.request.urlopen(URL + "/api/status", timeout=1) as response:
            data = json.load(response)
        if isinstance(data, dict) and "profiles_ready" in data and "port" in data:
            webbrowser.open(URL)
            return
    except (OSError, ValueError, urllib.error.URLError):
        pass
    server.main(open_browser=True)


if __name__ == "__main__":
    main()
