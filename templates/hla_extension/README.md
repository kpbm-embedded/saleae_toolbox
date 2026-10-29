# @NAME@

Logic 2 High Level Analyzer from `saleae-box new hla_extension @NAME@` (32_16_saleae): joins Async
Serial bytes into text lines (settings: line end, max length).

    saleae-box python -m pytest -q -p no:cacheprovider .     # host test, no Logic 2
    saleae-box hla . capture.csv uart --map RX=Channel_0 --setting max_len=128

In Logic 2: Extensions > Load Existing Extension > `extension.json`. Edit `HighLevelAnalyzer.py`;
the input frame fields are those of Logic 2's built-in analyzers (see `tools/hla_host.py`).
