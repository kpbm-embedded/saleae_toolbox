"""Write a Logic 2-style VCD: Raspberry Pi Pico (RP2040) UART0 TX at 9600 8N1 + a 1 kHz square wave on GP15.

Usage: python gen_vcd.py OUT.vcd
"""
import argparse
from pathlib import Path

BAUD, MSG = 9600, b"pico\n"
HALF_PERIOD_NS = 500_000  # 1 kHz


def uart_events(msg: bytes, baud: int, t0_ns: int = 1_000_000) -> tuple[list[tuple[int, int]], int]:
    """(time_ns, level) changes of an idle-high 8N1 line, and the end time."""
    bit = 1e9 / baud
    t, level, ev = float(t0_ns), 1, []
    for byte in msg:
        for b in [0] + [(byte >> k) & 1 for k in range(8)] + [1]:
            if b != level:
                ev.append((int(round(t)), b))
                level = b
            t += bit
    return ev, int(t)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path, help="VCD file to write")
    a = ap.parse_args()
    ev, end = uart_events(MSG, BAUD)
    square = [(k * HALF_PERIOD_NS, (k + 1) % 2) for k in range(1, end // HALF_PERIOD_NS + 1)]
    events = sorted([(t, "!", v) for t, v in ev] + [(t, '"', v) for t, v in square])
    lines = ["$timescale 1 ns $end", "$scope module top $end", "$var wire 1 ! GP0_UART0_TX $end",
             '$var wire 1 " GP15 $end', "$upscope $end", "$enddefinitions $end", "#0", "1!", '1"']
    last = None
    for t, ident, v in events:
        if t != last:
            lines.append(f"#{t}")
            last = t
        lines.append(f"{v}{ident}")
    a.out.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
