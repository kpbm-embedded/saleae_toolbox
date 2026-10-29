//! @NAME@: PWM measurement from a Logic 2 binary export channel (digital, version 0).
//! no_std, no alloc: the same file is unit-tested on the host and builds for Cortex-M.
#![cfg_attr(not(test), no_std)]

pub const HEADER_LEN: usize = 44;

#[derive(Debug, PartialEq, Clone, Copy)]
pub enum Error {
    Magic,
    Version,
    Truncated,
    TooFewEdges,
}

#[derive(Debug, Clone, Copy)]
pub struct Pwm {
    pub cycles: usize,
    pub period_s: f64,
    pub duty: f64,
}

fn rd(b: &[u8], o: usize) -> u64 {
    let mut a = [0u8; 8];
    a.copy_from_slice(&b[o..o + 8]);
    u64::from_le_bytes(a)
}

fn rd32(b: &[u8], o: usize) -> u32 {
    u32::from_le_bytes([b[o], b[o + 1], b[o + 2], b[o + 3]])
}

/// (initial level, transition count) after checking the header.
pub fn header(b: &[u8]) -> Result<(u8, usize), Error> {
    if b.len() < HEADER_LEN {
        return Err(Error::Truncated);
    }
    if &b[..8] != b"<SALEAE>" {
        return Err(Error::Magic);
    }
    if rd32(b, 8) != 0 || rd32(b, 12) != 0 {
        return Err(Error::Version);
    }
    let n = rd(b, 36) as usize;
    if b.len() < HEADER_LEN + 8 * n {
        return Err(Error::Truncated);
    }
    Ok(((rd32(b, 16) & 1) as u8, n))
}

fn t(b: &[u8], i: usize) -> f64 {
    f64::from_bits(rd(b, HEADER_LEN + 8 * i))
}

/// Mean period and duty over the complete cycles (rising edge to rising edge).
pub fn measure(b: &[u8]) -> Result<Pwm, Error> {
    let (init, n) = header(b)?;
    let first_rise = if init == 0 { 0 } else { 1 };
    let cycles = (n.saturating_sub(first_rise)) / 2;
    if cycles < 2 {
        return Err(Error::TooFewEdges);
    }
    let cycles = cycles - 1; // the last rising edge has no following one
    let (mut per, mut high) = (0.0f64, 0.0f64);
    for c in 0..cycles {
        let r = first_rise + 2 * c;
        per += t(b, r + 2) - t(b, r);
        high += t(b, r + 1) - t(b, r);
    }
    Ok(Pwm { cycles, period_s: per / cycles as f64, duty: high / per })
}

#[cfg(test)]
mod tests {
    use super::*;
    const FIX: &[u8] = include_bytes!("fixture_pwm.bin");

    #[test]
    fn one_khz_thirty_percent() {
        let p = measure(FIX).unwrap();
        assert!(p.cycles >= 18);
        assert!((1.0 / p.period_s - 1000.0).abs() < 0.01);
        assert!((p.duty - 0.30).abs() < 1e-6);
    }

    #[test]
    fn bad_header() {
        assert_eq!(header(&FIX[..10]).unwrap_err(), Error::Truncated);
        let mut b = FIX.to_vec();
        b[1] = b'X';
        assert_eq!(header(&b).unwrap_err(), Error::Magic);
    }
}
