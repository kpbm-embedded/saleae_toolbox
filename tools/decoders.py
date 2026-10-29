#!/usr/bin/env python3
"""Small protocol decoders and timing checks over logic captures (stdlib only).

Works on saleae_export.Digital (channel -> [(time_s, level)]) loaded from a Logic 2 digital CSV,
VCD, Logic 2 binary export or sigrok .sr (capfmt.load). sigrok-cli / libsigrokdecode are not on
conda-forge, so these are written here in the spirit of sigrok's decoders; frames use the field
names of Logic 2's built-in analyzers where one exists (so HLAs can consume them, hla_host.py).

Usage (saleae-box decode ...):
  decoders.py <capture> uart  --map RX=Channel_0 --baud 115200 [--parity even] [--json]
  decoders.py <capture> spi   --map CLK=..,MOSI=..,MISO=..,CS=.. [--mode 0]
  decoders.py <capture> i2c   --map SCL=..,SDA=..
  decoders.py <capture> can   --map RX=.. --baud 500000
  decoders.py <capture> onewire --map DQ=..
  decoders.py <capture> ws2812 --map DIN=..
  decoders.py <capture> pwm   --map OUT=..
  decoders.py <capture> quadrature --map A=..,B=..
  decoders.py <capture> i2s   --map SCK=..,WS=..,SD=.. [--bits 16]
  decoders.py <capture> swd   --map SWCLK=..,SWDIO=..
  decoders.py <capture> glitch --map CH=.. --min-width 1e-6
"""
from __future__ import annotations

import argparse
import bisect
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from saleae_export import Digital  # noqa: E402


class Line:
    """One channel with O(log n) level lookups."""

    def __init__(self, tr: list[tuple[float, int]]):
        self.tr = tr
        self.t = [x[0] for x in tr]

    def at(self, t: float) -> int:
        i = bisect.bisect_right(self.t, t) - 1
        return self.tr[i][1] if i >= 0 else self.tr[0][1]

    def edges(self, rising: bool | None = None) -> list[float]:
        out = []
        for (_, a), (t, b) in zip(self.tr, self.tr[1:]):
            if a != b and (rising is None or b == int(rising)):
                out.append(t)
        return out

    def pulses(self, level: int) -> list[tuple[float, float]]:
        """(start, width) of every complete pulse at `level`."""
        out = []
        for (t0, v), (t1, _) in zip(self.tr, self.tr[1:]):
            if v == level:
                out.append((t0, round(t1 - t0, 12)))
        return out


def line(d: Digital, name: str) -> Line:
    if name not in d.channels:
        raise KeyError(f"no channel '{name}' (have: {', '.join(d.channels)})")
    return Line(d.channels[name])


# ---------------------------------------------------------------- UART
def uart(d: Digital, ch: str, baud: int, bits: int = 8, parity: str | None = None, stop: int = 1,
         invert: bool = False) -> list[dict]:
    """Frames {start_time, end_time, data, error}; error: '' | 'framing' | 'parity'."""
    ln = line(d, ch)
    bit = 1.0 / baud
    lv = (lambda t: 1 - ln.at(t)) if invert else ln.at
    out: list[dict] = []
    t_end = ln.t[-1] if ln.t else 0.0
    nbits = bits + (1 if parity else 0)
    for t0 in ln.edges(rising=invert):
        if out and t0 < out[-1]["end_time"] - bit * 0.5:
            continue
        if lv(t0 + bit * 0.5) != 0:
            continue                       # too short: glitch, not a start bit
        v = 0
        for k in range(bits):
            v |= lv(t0 + bit * (1.5 + k)) << k
        err = ""
        if parity:
            p = lv(t0 + bit * (1.5 + bits))
            want = (bin(v).count("1") + (0 if parity == "even" else 1)) & 1
            if p != want:
                err = "parity"
        ts = t0 + bit * (1.5 + nbits)
        if ts <= t_end and lv(ts) != 1:
            err = err or "framing"
        out.append({"start_time": round(t0, 9), "end_time": round(t0 + bit * (1 + nbits + stop), 9),
                    "data": v, "error": err})
    return out


def estimate_baud(d: Digital, ch: str, rates=(9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600,
                                              1000000, 1500000, 2000000)) -> int:
    """Nearest standard rate to the shortest pulse (needs at least one single-bit pulse)."""
    widths = [w for _, w in line(d, ch).pulses(0) + line(d, ch).pulses(1)]
    raw = 1.0 / min(widths)
    return min(rates, key=lambda r: abs(r - raw) / r)


# ---------------------------------------------------------------- SPI
def spi(d: Digital, clk: str, mosi: str, miso: str | None, cs: str | None, mode: int = 0, bits: int = 8) -> list[dict]:
    """Transactions {start_time, end_time, mosi: [..], miso: [..]} (MSB first)."""
    c, mo = line(d, clk), line(d, mosi)
    mi = line(d, miso) if miso else None
    cpol, cpha = mode >> 1, mode & 1
    sample_rising = (cpol == 0) == (cpha == 0)
    samples = c.edges(rising=sample_rising)
    windows: list[tuple[float, float]] = []
    if cs:
        s = line(d, cs)
        falls, rises = s.edges(rising=False), s.edges(rising=True)
        for f in falls:
            j = bisect.bisect_right(rises, f)
            windows.append((f, rises[j] if j < len(rises) else float("inf")))
    else:
        windows = [(0.0, float("inf"))]
    out = []
    for a, b in windows:
        ts = [t for t in samples if a < t < b]
        tx, rx = [], []
        for i in range(0, len(ts) - bits + 1, bits):
            vo = vi = 0
            for t in ts[i:i + bits]:
                vo = (vo << 1) | mo.at(t)
                vi = (vi << 1) | (mi.at(t) if mi else 0)
            tx.append(vo); rx.append(vi)
        out.append({"start_time": round(a, 9), "end_time": round(min(b, ts[-1] if ts else a), 9),
                    "mosi": tx, "miso": rx, "partial_bits": len(ts) % bits})
    return out


# ---------------------------------------------------------------- I2C
def i2c(d: Digital, scl: str, sda: str) -> list[dict]:
    """Logic 2 I2C frame stream: start / address{address, read, ack} / data{data, ack} / stop."""
    c, s = line(d, scl), line(d, sda)
    events = sorted([(t, "scl", v) for t, v in c.tr[1:]] + [(t, "sda", v) for t, v in s.tr[1:]], key=lambda e: (e[0], e[1] == "sda"))
    frames: list[dict] = []
    bitbuf: list[tuple[float, int]] = []
    in_frame = False
    first = True
    for t, who, v in events:
        if who == "sda" and c.at(t) == 1:
            if v == 0:
                frames.append({"type": "start", "start_time": t, "end_time": t})
                in_frame, first, bitbuf = True, True, []
            else:
                frames.append({"type": "stop", "start_time": t, "end_time": t})
                in_frame = False
            continue
        if who == "scl" and v == 1 and in_frame:
            bitbuf.append((t, s.at(t)))
            if len(bitbuf) == 9:
                w = 0
                for _, b in bitbuf[:8]:
                    w = (w << 1) | b
                ack = bitbuf[8][1] == 0
                if first:
                    frames.append({"type": "address", "start_time": bitbuf[0][0], "end_time": t,
                                   "address": w >> 1, "read": bool(w & 1), "ack": ack})
                    first = False
                else:
                    frames.append({"type": "data", "start_time": bitbuf[0][0], "end_time": t, "data": w, "ack": ack})
                bitbuf = []
    return frames


def i2c_transactions(frames: list[dict]) -> list[dict]:
    """Group frames: {addr, read, data: [..], nak: bool} per address phase."""
    out: list[dict] = []
    for f in frames:
        if f["type"] == "address":
            out.append({"addr": f["address"], "read": f["read"], "data": [], "nak": not f["ack"], "start_time": f["start_time"]})
        elif f["type"] == "data" and out:
            out[-1]["data"].append(f["data"])
            if not f["ack"] and not out[-1]["read"]:
                out[-1]["nak"] = True
    return out


def i2c_timing(d: Digital, scl: str) -> dict:
    """Shortest SCL low/high and the clock rate (compare with UM10204 table 10)."""
    c = line(d, scl)
    lows = [w for _, w in c.pulses(0)][1:]   # first low ends after START hold
    highs = [w for _, w in c.pulses(1)][1:]
    rises = c.edges(rising=True)
    per = [b - a for a, b in zip(rises, rises[1:]) if b - a < 3 * (min(lows) + min(highs))]
    return {"t_low_min_s": round(min(lows), 9), "t_high_min_s": round(min(highs), 9),
            "f_scl_hz": round(1.0 / min(per)) if per else None}


I2C_SPEC = {  # UM10204 rev.7 table 10: (f_max, tLOW_min, tHIGH_min)
    "standard": (100e3, 4.7e-6, 4.0e-6),
    "fast": (400e3, 1.3e-6, 0.6e-6),
    "fast-plus": (1e6, 0.5e-6, 0.26e-6),
}


# ---------------------------------------------------------------- CAN (classic)
def can(d: Digital, ch: str, bitrate: int) -> list[dict]:
    """Frames {start_time, id, extended, rtr, dlc, data, crc_ok, ack, error}. Hard sync on SOF only."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from logicsim import can_crc15
    ln = line(d, ch)
    bit = 1.0 / bitrate
    out: list[dict] = []
    busy_until = -1.0
    for sof in ln.edges(rising=False):
        if sof < busy_until:
            continue
        # bus idle: at least 11 recessive bits before SOF (or start of capture)
        if ln.at(sof - bit * 0.5) != 1:
            continue
        pos = [0]
        raw: list[int] = []
        state = {"run": 0, "last": None, "err": ""}

        def rawbit() -> int:
            v = ln.at(sof + bit * (pos[0] + 0.5)); pos[0] += 1
            return v

        def nxt() -> int:
            v = rawbit()
            if state["run"] == 5:
                if v == state["last"]:
                    state["err"] = state["err"] or "stuff"
                state["run"], state["last"] = 1, v
                v = rawbit()
            state["run"] = state["run"] + 1 if v == state["last"] else 1
            state["last"] = v
            raw.append(v)
            return v

        def take(n: int) -> int:
            v = 0
            for _ in range(n):
                v = (v << 1) | nxt()
            return v

        take(1)  # SOF
        ident = take(11)
        rtr_srr = take(1)
        ide = take(1)
        rtr = rtr_srr
        if ide:
            ident = (ident << 18) | take(18)
            rtr = take(1)
            take(2)
        else:
            take(1)
        dlc = take(4)
        data = [take(8) for _ in range(min(dlc, 8) if not rtr else 0)]
        crc_calc = can_crc15(raw)
        crc = take(15)
        crc_delim, ack_slot = rawbit(), rawbit()
        err = state["err"] or ("" if crc_delim == 1 else "form")
        out.append({"start_time": round(sof, 9), "id": ident, "extended": bool(ide), "rtr": bool(rtr), "dlc": dlc,
                    "data": data, "crc": crc, "crc_ok": crc == crc_calc and not state["err"], "ack": ack_slot == 0,
                    "error": err})
        busy_until = sof + bit * (pos[0] + 9)
    return out


# ---------------------------------------------------------------- 1-Wire
def onewire(d: Digital, ch: str) -> list[dict]:
    """Segments {reset_time, presence, bytes: [..]} between reset pulses (standard speed)."""
    ln = line(d, ch)
    segs: list[dict] = []
    bits: list[int] = []
    expect_presence = False
    for t, w in ln.pulses(0):
        if w >= 480e-6 * 0.9:
            if segs:
                segs[-1]["bytes"] = pack_lsb(bits)
            segs.append({"reset_time": round(t, 9), "presence": False, "bytes": []})
            bits, expect_presence = [], True
        elif expect_presence and 60e-6 <= w <= 240e-6:
            segs[-1]["presence"] = True
            expect_presence = False
        elif segs:
            expect_presence = False
            bits.append(1 if w < 15e-6 else 0)
    if segs:
        segs[-1]["bytes"] = pack_lsb(bits)
    return segs


def pack_lsb(bits: list[int]) -> list[int]:
    return [sum(b << k for k, b in enumerate(bits[i:i + 8])) for i in range(0, len(bits) - 7, 8)]


# ---------------------------------------------------------------- WS2812
def ws2812(d: Digital, ch: str, t0h=(0.25e-6, 0.55e-6), t1h=(0.65e-6, 0.95e-6), reset_min=50e-6) -> dict:
    """{frames: [[(r,g,b),..]], violations: [..]} with WS2812B datasheet windows (+-150 ns)."""
    ln = line(d, ch)
    frames: list[list[tuple[int, int, int]]] = []
    viol: list[str] = []
    bits: list[int] = []

    def flush() -> None:
        if bits:
            px = []
            for i in range(0, len(bits) - 23, 24):
                g, r, b = (sum(bits[i + j * 8 + k] << (7 - k) for k in range(8)) for j in range(3))
                px.append((r, g, b))
            if len(bits) % 24:
                viol.append(f"frame with {len(bits)} bits (not a multiple of 24)")
            frames.append(px)
            bits.clear()

    for (t0, v), (t1, _) in zip(ln.tr, ln.tr[1:]):
        w = t1 - t0
        if v == 0:
            if w >= reset_min:
                flush()
            continue
        if t0h[0] <= w <= t0h[1]:
            bits.append(0)
        elif t1h[0] <= w <= t1h[1]:
            bits.append(1)
        else:
            viol.append(f"high pulse {w * 1e9:.0f} ns at {t0 * 1e6:.3f} us outside T0H/T1H")
            bits.append(1 if w > (t0h[1] + t1h[0]) / 2 else 0)
    flush()
    return {"frames": frames, "violations": viol}


# ---------------------------------------------------------------- PWM, quadrature, glitches, latency
def pwm(d: Digital, ch: str) -> dict:
    ln = line(d, ch)
    rises = ln.edges(rising=True)
    periods = [b - a for a, b in zip(rises, rises[1:])]
    highs = [w for t, w in ln.pulses(1) if rises and t >= rises[0]][:len(periods)]
    if not periods:
        return {"cycles": 0}
    mean = sum(periods) / len(periods)
    return {"cycles": len(periods), "freq_hz": round(1 / mean, 3), "period_s": round(mean, 12),
            "duty": round(sum(highs) / sum(periods[:len(highs)]), 6),
            "high_min_s": round(min(highs), 12), "high_max_s": round(max(highs), 12),
            "jitter_pp_s": round(max(periods) - min(periods), 12)}


def quadrature(d: Digital, a: str, b: str) -> dict:
    """4x count, direction changes and illegal transitions (both inputs changed together)."""
    la, lb = line(d, a), line(d, b)
    seq = {(0, 0): 0, (1, 0): 1, (1, 1): 2, (0, 1): 3}
    times = sorted(set(la.t[1:] + lb.t[1:]))
    st = seq[(la.tr[0][1], lb.tr[0][1])]
    count = illegal = reversals = 0
    last_dir = 0
    for t in times:
        n = seq[(la.at(t), lb.at(t))]
        diff = (n - st) % 4
        if diff == 1 or diff == 3:
            dirn = 1 if diff == 1 else -1
            if last_dir and dirn != last_dir:
                reversals += 1
            count += dirn
            last_dir = dirn
        elif diff == 2:
            illegal += 1
        st = n
    return {"count": count, "illegal": illegal, "reversals": reversals}


def glitches(d: Digital, ch: str, min_width: float) -> list[dict]:
    return [{"time": round(t, 12), "width_s": w, "level": lv}
            for lv in (0, 1) for t, w in line(d, ch).pulses(lv) if w < min_width]


def deglitch(d: Digital, ch: str, min_width: float) -> Digital:
    """Copy of d with pulses shorter than min_width removed from ch (like Logic 2's glitch filter)."""
    tr = list(d.channels[ch])
    changed = True
    while changed:
        changed = False
        for i in range(1, len(tr) - 1):
            if tr[i + 1][0] - tr[i][0] < min_width:
                del tr[i:i + 2]
                changed = True
                break
    out = Digital(dict(d.channels))
    out.channels[ch] = tr
    return out


def latency(d: Digital, src: str, dst: str, src_rising: bool = True, dst_rising: bool = True) -> list[float]:
    """For every src edge, time to the next dst edge (before the next src edge)."""
    s = line(d, src).edges(src_rising)
    t = line(d, dst).edges(dst_rising)
    out = []
    for i, e in enumerate(s):
        j = bisect.bisect_left(t, e)
        nxt = s[i + 1] if i + 1 < len(s) else float("inf")
        if j < len(t) and t[j] < nxt:
            out.append(round(t[j] - e, 12))
    return out


# ---------------------------------------------------------------- I2S, SWD
def i2s(d: Digital, sck: str, ws: str, sd: str, bits: int = 16) -> list[tuple[int, int]]:
    """Philips I2S: (left, right) signed samples; sampled on SCK rising."""
    c, w, s = line(d, sck), line(d, ws), line(d, sd)
    r = c.edges(rising=True)
    wv = [w.at(t) for t in r]
    sv = [s.at(t) for t in r]
    words: list[tuple[int, int]] = []
    starts = [0] + [i for i in range(1, len(wv)) if wv[i] != wv[i - 1]]
    for i in starts:
        if i + bits >= len(sv):
            break
        v = 0
        for k in range(1, bits + 1):
            v = (v << 1) | sv[i + k]
        if v & (1 << (bits - 1)):
            v -= 1 << bits
        words.append((wv[i], v))
    pairs = []
    for (c1, v1), (c2, v2) in zip(words, words[1:]):
        if c1 == 0 and c2 == 1:
            pairs.append((v1, v2))
    return pairs


SWD_ACK = {1: "OK", 2: "WAIT", 4: "FAULT", 7: "NO_RESPONSE"}


def swd(d: Digital, clk: str, dio: str) -> list[dict]:
    """Line resets and transfers {op, apndp, addr, ack, data, parity_ok}; bits sampled on SWCLK rising."""
    c, io = line(d, clk), line(d, dio)
    bits = [io.at(t) for t in c.edges(rising=True)]
    out: list[dict] = []
    i, ones, synced = 0, 0, False
    while i < len(bits):
        if bits[i] == 1:
            ones += 1
        else:
            if ones >= 50:
                out.append({"op": "line_reset"}); synced = True
            ones = 0
        if not synced or bits[i] != 1 or ones != 1 or i + 8 > len(bits):
            i += 1
            continue
        req = bits[i:i + 8]
        ap, rnw, a2, a3, par, stop, park = req[1:8]
        if (ap + rnw + a2 + a3) & 1 != par or stop != 0 or park != 1:
            synced = False                 # not a request: wait for the next line reset
            i += 1
            continue
        j = i + 8 + 1                      # turnaround
        ack = bits[j] | bits[j + 1] << 1 | bits[j + 2] << 2
        j += 3
        rec = {"op": "read" if rnw else "write", "apndp": "AP" if ap else "DP", "addr": a2 << 2 | a3 << 3,
               "ack": SWD_ACK.get(ack, f"0b{ack:03b}")}
        if ack == 1:
            if not rnw:
                j += 1
            v = sum(bits[j + k] << k for k in range(32))
            rec["data"] = v
            rec["parity_ok"] = bits[j + 32] == bin(v).count("1") & 1
            j += 33 + (1 if rnw else 0)
        out.append(rec)
        i, ones = j, 0
    return out


# ---------------------------------------------------------------- CLI
def parse_map(s: str) -> dict[str, str]:
    m = {}
    for part in s.split(","):
        k, v = part.split("=", 1)
        m[k.strip().upper()] = v.strip()
    return m


def main(argv: list[str] | None = None) -> int:
    import capfmt
    ap = argparse.ArgumentParser(description="Decode a protocol from a logic capture (CSV, VCD, Logic 2 .bin dir, sigrok .sr).")
    ap.add_argument("capture", type=Path)
    ap.add_argument("protocol", choices=["uart", "spi", "i2c", "can", "onewire", "ws2812", "pwm", "quadrature", "i2s", "swd", "glitch"])
    ap.add_argument("--map", required=True, help="ROLE=channel,... ('_' in a channel name means a space)")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--parity", choices=["even", "odd"], default=None)
    ap.add_argument("--mode", type=int, default=0)
    ap.add_argument("--bits", type=int, default=16)
    ap.add_argument("--min-width", type=float, default=1e-6)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    d = capfmt.load(a.capture)
    m = {k: v if v in d.channels else v.replace("_", " ") for k, v in parse_map(a.map).items()}
    try:
        p = a.protocol
        if p == "uart":
            fr = uart(d, m["RX"], a.baud, parity=a.parity)
            res: object = {"frames": len(fr), "errors": sum(1 for f in fr if f["error"]),
                           "text": bytes(f["data"] for f in fr).decode("latin-1")}
        elif p == "spi":
            res = spi(d, m["CLK"], m["MOSI"], m.get("MISO"), m.get("CS"), a.mode)
        elif p == "i2c":
            res = i2c_transactions(i2c(d, m["SCL"], m["SDA"]))
        elif p == "can":
            res = can(d, m["RX"], a.baud)
        elif p == "onewire":
            res = onewire(d, m["DQ"])
        elif p == "ws2812":
            res = ws2812(d, m["DIN"])
        elif p == "pwm":
            res = pwm(d, m["OUT"])
        elif p == "quadrature":
            res = quadrature(d, m["A"], m["B"])
        elif p == "i2s":
            res = i2s(d, m["SCK"], m["WS"], m["SD"], a.bits)
        elif p == "swd":
            res = swd(d, m["SWCLK"], m["SWDIO"])
        else:
            res = glitches(d, m["CH"], a.min_width)
    except KeyError as e:
        print(f"decode: missing role or channel {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(res, indent=2))
    elif isinstance(res, list):
        for r in res:
            print(r)
    else:
        print(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
