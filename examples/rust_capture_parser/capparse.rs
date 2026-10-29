//! Logic 2 binary export (digital, version 0) parser and 8N1 UART decoder.
//! no_std and no alloc, so the same code runs on the host (tests) and on a Cortex-M
//! (e.g. a BlackPill checking a capture it received over USB).
#![cfg_attr(not(test), no_std)]

pub const MAGIC: &[u8; 8] = b"<SALEAE>";
/// magic 8 + version i32 + type i32 + initial u32 + begin f64 + end f64 + count u64
pub const HEADER_LEN: usize = 44;

#[derive(Debug, PartialEq, Clone, Copy)]
pub enum Error {
    Magic,
    Version,
    Truncated,
}

#[derive(Debug, PartialEq, Clone, Copy)]
pub struct Header {
    pub initial: u8,
    pub begin: f64,
    pub end: f64,
    pub count: usize,
}

fn u32le(b: &[u8], o: usize) -> u32 {
    u32::from_le_bytes([b[o], b[o + 1], b[o + 2], b[o + 3]])
}

fn u64le(b: &[u8], o: usize) -> u64 {
    let mut a = [0u8; 8];
    a.copy_from_slice(&b[o..o + 8]);
    u64::from_le_bytes(a)
}

pub fn header(b: &[u8]) -> Result<Header, Error> {
    if b.len() < HEADER_LEN {
        return Err(Error::Truncated);
    }
    if &b[..8] != MAGIC {
        return Err(Error::Magic);
    }
    if u32le(b, 8) != 0 || u32le(b, 12) != 0 {
        return Err(Error::Version);
    }
    let count = u64le(b, 36) as usize;
    if b.len() < HEADER_LEN + 8 * count {
        return Err(Error::Truncated);
    }
    Ok(Header {
        initial: (u32le(b, 16) & 1) as u8,
        begin: f64::from_bits(u64le(b, 20)),
        end: f64::from_bits(u64le(b, 28)),
        count,
    })
}

pub fn transition(b: &[u8], i: usize) -> f64 {
    f64::from_bits(u64le(b, HEADER_LEN + 8 * i))
}

/// Level at time t (binary search over the transition times).
pub fn level_at(b: &[u8], h: &Header, t: f64) -> u8 {
    let (mut lo, mut hi) = (0usize, h.count);
    while lo < hi {
        let mid = (lo + hi) / 2;
        if transition(b, mid) <= t {
            lo = mid + 1;
        } else {
            hi = mid;
        }
    }
    h.initial ^ (lo & 1) as u8
}

/// 8N1, LSB first, idle high. Returns the number of bytes written to `out`;
/// frames with a bad stop bit are skipped.
pub fn uart_decode(b: &[u8], baud: u32, out: &mut [u8]) -> Result<usize, Error> {
    let h = header(b)?;
    let bit = 1.0 / baud as f64;
    let (mut n, mut busy_until) = (0usize, f64::MIN);
    for i in 0..h.count {
        let t0 = transition(b, i);
        let after = h.initial ^ ((i + 1) & 1) as u8;
        if after != 0 || t0 < busy_until || n == out.len() {
            continue;
        }
        if level_at(b, &h, t0 + 0.5 * bit) != 0 {
            continue;
        }
        let mut v = 0u8;
        for k in 0..8 {
            v |= level_at(b, &h, t0 + bit * (1.5 + k as f64)) << k;
        }
        busy_until = t0 + 9.5 * bit;
        if level_at(b, &h, busy_until) == 1 {
            out[n] = v;
            n += 1;
        }
    }
    Ok(n)
}

#[cfg(test)]
mod tests {
    use super::*;
    const FIX: &[u8] = include_bytes!("fixture_uart.bin");

    #[test]
    fn header_ok() {
        let h = header(FIX).unwrap();
        assert_eq!(h.initial, 1);
        assert!(h.count > 20 && h.end > h.begin);
    }

    #[test]
    fn decodes_uart() {
        let mut buf = [0u8; 32];
        let n = uart_decode(FIX, 115_200, &mut buf).unwrap();
        assert_eq!(&buf[..n], b"hello rust\r\n");
    }

    #[test]
    fn wrong_baud_does_not_match() {
        let mut buf = [0u8; 32];
        let n = uart_decode(FIX, 57_600, &mut buf).unwrap();
        assert_ne!(&buf[..n], b"hello rust\r\n");
    }

    #[test]
    fn rejects_bad_input() {
        let mut bad = FIX.to_vec();
        bad[0] = b'X';
        assert_eq!(header(&bad), Err(Error::Magic));
        assert_eq!(header(&FIX[..HEADER_LEN + 8]), Err(Error::Truncated));
    }
}
