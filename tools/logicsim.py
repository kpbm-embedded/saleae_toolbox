#!/usr/bin/env python3
"""Generate ideal logic-analyser captures of embedded buses (no hardware, no Logic 2).

Each generator appends to a Builder: per-channel transition lists [(time_s, level)], the same
model as saleae_export.Digital. Write the result with capfmt (Logic 2 CSV, VCD, Logic 2 binary,
sigrok .sr). Used by the examples and templates as fixtures for the decoders in decoders.py.

Protocols: UART, SPI (modes 0-3), I2C, classic CAN (stuffing + CRC15), 1-Wire, WS2812, PWM,
quadrature, I2S (Philips), SWD; plus glitch injection.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from saleae_export import Digital  # noqa: E402


class Builder:
    """Multi-channel waveform builder with one shared time cursor."""

    def __init__(self, idle: dict[str, int], lead: float = 10e-6):
        self.t = lead                 # idle time before the first edge
        self.ch: dict[str, list[tuple[float, int]]] = {n: [(0.0, v)] for n, v in idle.items()}

    def set(self, name: str, level: int) -> None:
        tr = self.ch[name]
        t = round(self.t, 12)
        if tr[-1][1] == level:
            return
        if tr[-1][0] == t and len(tr) > 1:   # two changes at the same instant: keep the last one
            tr.pop()
            if tr and tr[-1][1] == level:
                return
        tr.append((t, level))

    def wait(self, dt: float) -> None:
        self.t += dt

    def level(self, name: str) -> int:
        return self.ch[name][-1][1]

    def digital(self) -> Digital:
        return Digital({n: list(tr) for n, tr in self.ch.items()})


# ---------------------------------------------------------------- UART
def uart(b: Builder, ch: str, baud: int, data: bytes, parity: str | None = None, stop: int = 1,
         gap_bits: float = 1.0) -> None:
    """8 data bits LSB first, optional parity 'even'/'odd', idle high."""
    bit = 1.0 / baud
    for byte in data:
        bits = [0] + [(byte >> k) & 1 for k in range(8)]
        if parity:
            p = bin(byte).count("1") & 1
            bits.append(p if parity == "even" else p ^ 1)
        bits += [1] * stop
        for v in bits:
            b.set(ch, v)
            b.wait(bit)
        b.wait(bit * gap_bits)


# ---------------------------------------------------------------- SPI
def spi(b: Builder, txns: list[tuple[bytes, bytes]], freq: float, mode: int = 0,
        clk: str = "CLK", mosi: str = "MOSI", miso: str = "MISO", cs: str = "CS", gap: float = 2e-6) -> None:
    """One CS-low transaction per (mosi, miso) pair, MSB first."""
    cpol, cpha = mode >> 1, mode & 1
    half = 0.5 / freq
    b.set(clk, cpol)
    for tx, rx in txns:
        b.set(cs, 0)
        b.wait(half)
        for bo, bi in zip(tx, rx.ljust(len(tx), b"\0")):
            for k in range(7, -1, -1):
                if cpha == 0:
                    b.set(mosi, (bo >> k) & 1); b.set(miso, (bi >> k) & 1)
                    b.wait(half); b.set(clk, 1 - cpol); b.wait(half); b.set(clk, cpol)
                else:
                    b.set(clk, 1 - cpol); b.set(mosi, (bo >> k) & 1); b.set(miso, (bi >> k) & 1)
                    b.wait(half); b.set(clk, cpol); b.wait(half)
        b.wait(half)
        b.set(cs, 1)
        b.wait(gap)


# ---------------------------------------------------------------- I2C
def i2c(b: Builder, ops: list[tuple], freq: float = 100e3, scl: str = "SCL", sda: str = "SDA",
        t_low: float | None = None, t_high: float | None = None) -> None:
    """ops: ('w', addr7, bytes[, nak_at]) or ('r', addr7, bytes); consecutive ops use a repeated
    START, one STOP at the end. Master NAKs the last read byte. nak_at: index (0 = address) the
    target NAKs (then STOP)."""
    period = 1.0 / freq
    tl = t_low if t_low is not None else period / 2
    th = t_high if t_high is not None else period / 2

    def clock_bit(v: int) -> None:
        b.wait(tl / 2); b.set(sda, v); b.wait(tl / 2)
        b.set(scl, 1); b.wait(th); b.set(scl, 0)

    def start() -> None:
        if b.level(scl) == 0:         # repeated START: release SDA, raise SCL
            b.wait(tl / 2); b.set(sda, 1); b.wait(tl / 2); b.set(scl, 1); b.wait(th / 2)
        b.set(sda, 0); b.wait(th / 2); b.set(scl, 0)

    def stop() -> None:
        b.wait(tl / 2); b.set(sda, 0); b.wait(tl / 2); b.set(scl, 1); b.wait(th / 2); b.set(sda, 1); b.wait(period)

    b.wait(period)
    for op in ops:
        kind, addr, data = op[0], op[1], op[2]
        nak_at = op[3] if len(op) > 3 else None
        start()
        words = [(addr << 1) | (kind == "r")] + list(data)
        stopped = False
        for i, w in enumerate(words):
            for k in range(7, -1, -1):
                clock_bit((w >> k) & 1)
            if kind == "r" and i > 0:
                ack = 1 if i == len(words) - 1 else 0
            else:
                ack = 1 if nak_at == i else 0
            clock_bit(ack)
            if ack and not (kind == "r" and i > 0):
                stop(); stopped = True
                break
        if stopped:
            return
    stop()


# ---------------------------------------------------------------- CAN (classic, 2.0A/B)
def can_crc15(bits: list[int]) -> int:
    crc = 0
    for bit in bits:
        nxt = bit ^ ((crc >> 14) & 1)
        crc = (crc << 1) & 0x7FFF
        if nxt:
            crc ^= 0x4599
    return crc


def can_bits(ident: int, data: bytes, extended: bool = False, rtr: bool = False) -> list[int]:
    """Unstuffed bits SOF..CRC (the part that is bit-stuffed)."""
    def nb(v: int, n: int) -> list[int]:
        return [(v >> k) & 1 for k in range(n - 1, -1, -1)]
    bits = [0]
    if extended:
        bits += nb(ident >> 18, 11) + [1, 1] + nb(ident & 0x3FFFF, 18) + [int(rtr), 0, 0]
    else:
        bits += nb(ident, 11) + [int(rtr), 0, 0]
    bits += nb(len(data), 4)
    for x in data:
        bits += nb(x, 8)
    return bits + nb(can_crc15(bits), 15)


def stuff(bits: list[int]) -> list[int]:
    out, run, last = [], 0, None
    for x in bits:
        out.append(x)
        run = run + 1 if x == last else 1
        last = x
        if run == 5:
            out.append(1 - x); last = 1 - x; run = 1
    return out


def can(b: Builder, ch: str, bitrate: int, ident: int, data: bytes, extended: bool = False,
        ack: bool = True, break_stuffing: bool = False) -> None:
    """One frame on a logic-level CAN RX/TX line (dominant = 0)."""
    bit = 1.0 / bitrate
    raw = stuff(can_bits(ident, data, extended))
    if break_stuffing:   # 6 equal bits inside the frame: a stuff error
        i = next(i for i in range(5, len(raw)) if raw[i - 5:i].count(raw[i - 1]) == 5)
        raw[i] = raw[i - 1]
    raw += [1, 0 if ack else 1, 1] + [1] * 7 + [1] * 3   # CRC delim, ACK slot, ACK delim, EOF, IFS
    for v in raw:
        b.set(ch, v); b.wait(bit)


# ---------------------------------------------------------------- 1-Wire (standard speed)
def ow_reset(b: Builder, ch: str, presence: bool = True) -> None:
    b.set(ch, 0); b.wait(480e-6); b.set(ch, 1); b.wait(70e-6)
    if presence:
        b.set(ch, 0); b.wait(120e-6); b.set(ch, 1)
        b.wait(290e-6)
    else:
        b.wait(410e-6)


def ow_bytes(b: Builder, ch: str, data: bytes) -> None:
    """Write (or, slave-driven, read) slots: 1 = 6 us low, 0 = 60 us low; slot 70 us."""
    for x in data:
        for k in range(8):
            low = 6e-6 if (x >> k) & 1 else 60e-6
            b.set(ch, 0); b.wait(low); b.set(ch, 1); b.wait(70e-6 - low)


def crc8_maxim(data: bytes) -> int:
    crc = 0
    for x in data:
        for _ in range(8):
            mix = (crc ^ x) & 1
            crc >>= 1
            if mix:
                crc ^= 0x8C
            x >>= 1
    return crc


# ---------------------------------------------------------------- WS2812
def ws2812(b: Builder, ch: str, pixels: list[tuple[int, int, int]], t0h: float = 0.40e-6, t1h: float = 0.80e-6,
           period: float = 1.25e-6, reset: float = 80e-6) -> None:
    """pixels as (r, g, b); sent G, R, B MSB first."""
    b.set(ch, 0); b.wait(reset)
    for r, g, bl in pixels:
        for byte in (g, r, bl):
            for k in range(7, -1, -1):
                th = t1h if (byte >> k) & 1 else t0h
                b.set(ch, 1); b.wait(th); b.set(ch, 0); b.wait(period - th)
    b.wait(reset)


# ---------------------------------------------------------------- PWM / quadrature
def pwm(b: Builder, ch: str, freq: float, duty: float, cycles: int, jitter: list[float] | None = None) -> None:
    per = 1.0 / freq
    for i in range(cycles):
        j = jitter[i % len(jitter)] if jitter else 0.0
        b.set(ch, 1); b.wait(per * duty + j); b.set(ch, 0); b.wait(per * (1 - duty) - j)


def quadrature(b: Builder, steps: list[int], step_s: float, a: str = "A", bch: str = "B") -> None:
    """steps: +1 / -1 quarter steps (Gray code 00 -> 01 -> 11 -> 10 forward, A leads)."""
    seq = [(0, 0), (1, 0), (1, 1), (0, 1)]
    pos = seq.index((b.level(a), b.level(bch)))
    for s in steps:
        pos = (pos + s) % 4
        b.set(a, seq[pos][0]); b.set(bch, seq[pos][1]); b.wait(step_s)


def glitch(b: Builder, ch: str, at: float, width: float) -> None:
    """Insert a short inverted pulse at absolute time `at` (after generation)."""
    tr = b.ch[ch]
    lvl = 1
    for t, v in tr:
        if t > at:
            break
        lvl = v
    tr += [(round(at, 12), 1 - lvl), (round(at + width, 12), lvl)]
    tr.sort()


# ---------------------------------------------------------------- I2S (Philips), SWD
def i2s(b: Builder, samples: list[tuple[int, int]], fs: int, bits: int = 16,
        sck: str = "SCK", ws: str = "WS", sd: str = "SD") -> None:
    """Stereo, WS low = left, MSB one SCK after the WS edge, data changes on SCK falling."""
    half = 0.5 / (fs * 2 * bits)
    stream: list[int] = []
    for left, right in samples:
        for v in (left, right):
            stream += [((v & ((1 << bits) - 1)) >> k) & 1 for k in range(bits - 1, -1, -1)]
    for n in range(len(stream) + 1):
        b.set(sck, 0)
        b.set(ws, (n // bits) % 2 if n < len(stream) else 0)
        b.set(sd, stream[n - 1] if n else 0)
        b.wait(half); b.set(sck, 1); b.wait(half)
    b.set(sck, 0)


def swd_parity(v: int) -> int:
    return bin(v).count("1") & 1


def swd_request(apndp: int, rnw: int, addr: int) -> list[int]:
    a2, a3 = (addr >> 2) & 1, (addr >> 3) & 1
    return [1, apndp, rnw, a2, a3, (apndp + rnw + a2 + a3) & 1, 0, 1]


def swd(b: Builder, ops: list[tuple], freq: float = 1e6, clk: str = "SWCLK", dio: str = "SWDIO") -> None:
    """ops: ('reset',) line reset; ('bits', [..]) raw; ('read'|'write', apndp, addr, value[, ack])."""
    half = 0.5 / freq

    def clock(bits: list[int]) -> None:
        for v in bits:
            b.set(dio, v); b.wait(half); b.set(clk, 1); b.wait(half); b.set(clk, 0)

    def word(v: int) -> list[int]:
        return [(v >> k) & 1 for k in range(32)] + [swd_parity(v)]

    for op in ops:
        if op[0] == "reset":
            clock([1] * 56)
        elif op[0] == "bits":
            clock(op[1])
        else:
            rnw = 1 if op[0] == "read" else 0
            ack = op[4] if len(op) > 4 else 1
            clock(swd_request(op[1], rnw, op[2]) + [1])          # request + turnaround
            clock([(ack >> k) & 1 for k in range(3)])
            if ack == 1:
                clock(word(op[3]) + [0] if rnw else [0] + word(op[3]))
            clock([0, 0])                                         # idle
