"""Exploratory RX-only 868 MHz RSSI test; restores the MCZ profile on exit."""
import argparse
from datetime import datetime
from pathlib import Path
import time
import serial

PROFILES = ((b"1", 868300000), (b"2", 868950000), (b"3", 869850000))


def run(port_name: str, seconds: int) -> None:
    folder = Path(__file__).resolve().parents[1] / "captures"
    path = folder / (datetime.now().strftime("%Y%m%d-%H%M%S") + "_garage868.log")
    with serial.Serial(port_name, 115200, timeout=0.1) as port, path.open("wb") as log:
        port.dtr = False
        port.rts = False

        def read_for(duration: float) -> bytes:
            end = time.monotonic() + duration
            received = bytearray()
            while time.monotonic() < end:
                data = port.read(port.in_waiting or 1)
                if data:
                    log.write(data)
                    log.flush()
                    received.extend(data)
                    print(data.decode("utf-8", errors="replace"), end="", flush=True)
            return bytes(received)

        def select(command: bytes, hz: int) -> None:
            port.write(command)
            reply = read_for(0.5)
            expected = f"RX_PROFILE OK FREQ_HZ={hz} STATE=0D".encode()
            if expected not in reply:
                raise RuntimeError(f"RX profile {hz} Hz not acknowledged; inspect log")

        try:
            startup = read_for(2)
            if b"RX READY" not in startup:
                raise RuntimeError("RX startup not confirmed")
            port.write(b"d")
            for command, hz in PROFILES:
                select(command, hz)
                marker = f"TEST_WINDOW FREQ_HZ={hz} seconds={seconds}\n".encode()
                log.write(marker)
                print(marker.decode(), end="", flush=True)
                read_for(seconds)
        finally:
            # Always attempt restoration, including Ctrl+C and failed calibration.
            select(b"0", 434500000)
            port.write(b"ds")
            read_for(0.5)
    print(f"\nLog: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--seconds-per-band", type=int, default=15)
    args = parser.parse_args()
    if not 1 <= args.seconds_per_band <= 60:
        parser.error("--seconds-per-band must be between 1 and 60")
    try:
        run(args.port, args.seconds_per_band)
    except (serial.SerialException, OSError, RuntimeError) as exc:
        parser.exit(1, f"Test failed: {exc}\n")
