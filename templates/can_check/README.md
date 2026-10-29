# @NAME@

CAN traffic check from `saleae-box new can_check @NAME@` (32_16_saleae): frame errors (CRC, stuffing,
missing ACK), unknown IDs, DLC and period per ID from `spec.json`. Probe the transceiver's RX pin.

    saleae-box python @NAME@.py my_export.vcd
    saleae-box python -m pytest -q -p no:cacheprovider .
