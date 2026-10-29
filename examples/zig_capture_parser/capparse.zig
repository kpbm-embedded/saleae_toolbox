//! Logic 2 binary export (digital, version 0) parser and SPI mode-0 decoder.
//! No allocator and no OS: builds for the host (zig test) and freestanding Cortex-M.
const std = @import("std");

pub const Error = error{ Magic, Version, Truncated };
pub const header_len = 44; // magic 8, version, type, initial, begin f64, end f64, count u64

pub const Header = struct { initial: u1, count: usize };

fn rd32(b: []const u8, o: usize) u32 {
    return std.mem.readInt(u32, b[o..][0..4], .little);
}

fn rd64(b: []const u8, o: usize) u64 {
    return std.mem.readInt(u64, b[o..][0..8], .little);
}

pub fn header(b: []const u8) Error!Header {
    if (b.len < header_len) return error.Truncated;
    if (!std.mem.eql(u8, b[0..8], "<SALEAE>")) return error.Magic;
    if (rd32(b, 8) != 0 or rd32(b, 12) != 0) return error.Version;
    const n: usize = @intCast(rd64(b, 36));
    if (b.len < header_len + 8 * n) return error.Truncated;
    return .{ .initial = @intCast(rd32(b, 16) & 1), .count = n };
}

pub fn time(b: []const u8, i: usize) f64 {
    return @bitCast(rd64(b, header_len + 8 * i));
}

pub fn levelAt(b: []const u8, h: Header, t: f64) u1 {
    var lo: usize = 0;
    var hi: usize = h.count;
    while (lo < hi) {
        const mid = (lo + hi) / 2;
        if (time(b, mid) <= t) lo = mid + 1 else hi = mid;
    }
    return h.initial ^ @as(u1, @intCast(lo & 1));
}

/// Mode 0, MSB first: MOSI sampled on SCK rising edges while CS is low. Returns bytes written.
pub fn spiDecode(sck: []const u8, mosi: []const u8, cs: []const u8, out: []u8) Error!usize {
    const hs = try header(sck);
    const hm = try header(mosi);
    const hc = try header(cs);
    var n: usize = 0;
    var acc: u8 = 0;
    var bits: u4 = 0;
    var i: usize = 0;
    while (i < hs.count and n < out.len) : (i += 1) {
        const rising = (hs.initial ^ @as(u1, @intCast((i + 1) & 1))) == 1;
        if (!rising) continue;
        const t = time(sck, i);
        if (levelAt(cs, hc, t) != 0) continue;
        acc = (acc << 1) | levelAt(mosi, hm, t);
        bits += 1;
        if (bits == 8) {
            out[n] = acc;
            n += 1;
            acc = 0;
            bits = 0;
        }
    }
    return n;
}

/// C ABI entry for firmware: returns the byte count or -1 on a bad file.
export fn capparse_spi(sck: [*]const u8, sck_len: usize, mosi: [*]const u8, mosi_len: usize, cs: [*]const u8, cs_len: usize, out: [*]u8, out_len: usize) isize {
    const n = spiDecode(sck[0..sck_len], mosi[0..mosi_len], cs[0..cs_len], out[0..out_len]) catch return -1;
    return @intCast(n);
}

test "decodes SD CMD0 from the Pico SPI0 capture" {
    var buf: [16]u8 = undefined;
    const n = try spiDecode(@embedFile("digital_1.bin"), @embedFile("digital_2.bin"), @embedFile("digital_0.bin"), &buf);
    try std.testing.expectEqualSlices(u8, &[_]u8{ 0x40, 0, 0, 0, 0, 0x95, 0xFF }, buf[0..n]);
}

test "rejects a bad header" {
    var bad: [header_len]u8 = @splat(0);
    try std.testing.expectError(error.Magic, header(&bad));
    try std.testing.expectError(error.Truncated, header(bad[0..10]));
}
