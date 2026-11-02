"""Record RX firmware output locally. Opening the port may reset the ESP32."""
import argparse
from datetime import datetime
from pathlib import Path
import time
import serial


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--label", choices=["baseline", "buttons", "diagnostic"], default="diagnostic")
    parser.add_argument("--diagnostics", action="store_true")
    parser.add_argument("--raw", action="store_true", help="Arm one raw burst every 3 seconds")
    parser.add_argument("--trigger", action="store_true", help="Enable the firmware's RSSI-triggered raw capture")
    parser.add_argument("--continuous-raw", action="store_true", help="Rearm raw capture after each burst; may be combined with --trigger")
    args = parser.parse_args()
    if not 3 <= args.seconds <= 3600:
        parser.error("--seconds must be between 3 and 3600")
    if args.raw and args.trigger:
        parser.error("Choose --raw or --trigger")
    folder = Path(__file__).resolve().parents[1] / "captures"
    folder.mkdir(exist_ok=True)
    path = folder / (datetime.now().strftime("%Y%m%d-%H%M%S") + "_" + args.label + ".log")
    try:
        with serial.Serial(args.port, 115200, timeout=0.1) as port, path.open("wb") as log:
            port.dtr = False
            port.rts = False
            start = time.monotonic()
            next_raw = start + 2
            diagnostics_sent = False
            trigger_sent = False
            pending_line = bytearray()
            while time.monotonic() - start < args.seconds:
                data = port.read(port.in_waiting or 1)
                if data:
                    log.write(data)
                    log.flush()
                    print(data.decode("utf-8", errors="replace"), end="", flush=True)
                    if args.continuous_raw:
                        pending_line.extend(data)
                        while b"\n" in pending_line:
                            line, _, rest = pending_line.partition(b"\n")
                            pending_line = bytearray(rest)
                            if line.strip() == b"RX_BURST_END":
                                port.write(b"r")
                        if len(pending_line) > 4096:
                            pending_line.clear()
                now = time.monotonic()
                if args.diagnostics and not diagnostics_sent and now - start >= 2:
                    port.write(b"d")
                    diagnostics_sent = True
                if args.trigger and not trigger_sent and now - start >= 2:
                    port.write(b"t")
                    trigger_sent = True
                if args.raw and now >= next_raw:
                    port.write(b"r")
                    next_raw = now + 3
                if args.continuous_raw and now >= next_raw:
                    # Also rearm periodically when noise consumed the one-shot.
                    port.write(b"r")
                    next_raw = now + 1
            port.write(b"s")
            if trigger_sent:
                port.write(b"t")
            if diagnostics_sent:
                port.write(b"d")
            time.sleep(0.2)
            data = port.read(port.in_waiting)
            log.write(data)
            print(data.decode("utf-8", errors="replace"), end="")
    except (serial.SerialException, OSError) as exc:
        parser.exit(1, f"Recording failed: {exc}\n")
    print(f"\nLog: {path}")


if __name__ == "__main__":
    main()
