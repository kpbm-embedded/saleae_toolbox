# @NAME@

no_std Rust decoder from `saleae-box new rust_decoder @NAME@` (32_16_saleae): PWM period/duty from a
Logic 2 binary export channel (`digital_N.bin`). Same code on the host (unit tests) and on a Cortex-M.
The Rust toolchain is the one pinned in `32_17_embedded_rust` (`BOX_EMBEDDED_RUST`); nothing is installed here.

    saleae-box run bash test.sh            # fixture, host tests, thumbv7em-none-eabihf rlib in out/ (exit 3: no 32_17)

To use it in a firmware crate, copy `@NAME@.rs` as a module; `out/` is build output.
