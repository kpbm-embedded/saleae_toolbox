"""Write a Logic 2 digital raw-data CSV of an Arduino Nano (ATmega328P) Serial.print at 115200 8N1.

Usage: python gen_fixture.py OUT.csv [--baud 115200] [--text 'hello nano']
"""
import argparse
from pathlib import Path


def transitions(msg: bytes, baud: int, t0: float = 0.001) -> list[tuple[float, int]]:
    """Level changes of an idle-high 8N1 line sending msg (one idle bit between frames)."""
    bit = 1.0 / baud
    level, t, out = 1, t0, [(0.0, 1)]
    for byte in msg:
        for b in [0] + [(byte >> k) & 1 for k in range(8)] + [1]:
            if b != level:
                out.append((round(t, 9), b))
                level = b
            t += bit
        t += bit
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path, help="CSV file to write")
    ap.add_argument("--baud", type=int, default=115200, help="bit rate (default 115200)")
    ap.add_argument("--text", default="hello nano\r\n", help="text sent (escapes \\r \\n allowed)")
    a = ap.parse_args()
    msg = a.text.encode().decode("unicode_escape").encode("latin-1")
    lines = ["Time [s],Channel 0"] + [f"{t:.9f},{v}" for t, v in transitions(msg, a.baud)]
    a.out.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
