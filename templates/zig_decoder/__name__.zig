//! @NAME@: count glitches (pulses shorter than a minimum width) and full clock edges in a Logic 2
//! binary export channel (digital, version 0). No allocator, no OS.
const std = @import("std");

pub const Error = error{ Magic, Version, Truncated };
const header_len = 44;

pub const Stats = struct { edges: usize, glitches: usize, shortest_ok_s: f64 };

fn rd32(b: []const u8, o: usize) u32 {
    return std.mem.readInt(u32, b[o..][0..4], .little);
}

fn rd64(b: []const u8, o: usize) u64 {
    return std.mem.readInt(u64, b[o..][0..8], .little);
}

pub fn count(b: []const u8) Error!usize {
    if (b.len < header_len) return error.Truncated;
    if (!std.mem.eql(u8, b[0..8], "<SALEAE>")) return error.Magic;
    if (rd32(b, 8) != 0 or rd32(b, 12) != 0) return error.Version;
    const n: usize = @intCast(rd64(b, 36));
    if (b.len < header_len + 8 * n) return error.Truncated;
    return n;
}

fn time(b: []const u8, i: usize) f64 {
    return @bitCast(rd64(b, header_len + 8 * i));
}

/// A pulse narrower than min_width counts as one glitch (its two edges are not counted as edges).
pub fn scan(b: []const u8, min_width: f64) Error!Stats {
    const n = try count(b);
    var s = Stats{ .edges = 0, .glitches = 0, .shortest_ok_s = std.math.inf(f64) };
    var i: usize = 0;
    while (i < n) : (i += 1) {
        if (i + 1 < n and time(b, i + 1) - time(b, i) < min_width) {
            s.glitches += 1;
            i += 1;
            continue;
        }
        s.edges += 1;
        if (i + 1 < n) s.shortest_ok_s = @min(s.shortest_ok_s, time(b, i + 1) - time(b, i));
    }
    return s;
}

export fn glitch_count(b: [*]const u8, len: usize, min_width: f64) isize {
    const s = scan(b[0..len], min_width) catch return -1;
    return @intCast(s.glitches);
}

test "three glitches in a 10 kHz clock" {
    const s = try scan(@embedFile("fixture.bin"), 1e-6);
    try std.testing.expectEqual(@as(usize, 3), s.glitches);
    try std.testing.expectEqual(@as(usize, 60), s.edges);
    try std.testing.expect(s.shortest_ok_s > 1e-6);
}

test "bad header" {
    var bad: [header_len]u8 = @splat(0);
    try std.testing.expectError(error.Magic, count(&bad));
}
