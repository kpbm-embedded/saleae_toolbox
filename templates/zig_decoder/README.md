# @NAME@

Zig decoder from `saleae-box new zig_decoder @NAME@` (32_16_saleae): glitch and edge count in a Logic 2
binary export channel. Host `zig test` plus a freestanding Cortex-M33 object (`export fn glitch_count`
for C or MicroZig firmware). Zig is the one pinned in `32_24_microzig` (`BOX_MICROZIG`); nothing is installed here.

    saleae-box run bash test.sh            # fixture, zig test, out/decoder_m33.o (exit 3: no 32_24)
