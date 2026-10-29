"""@NAME@: Logic 2 High Level Analyzer that joins Async Serial bytes into text lines.

Load in Logic 2: Extensions > Load Existing Extension > this folder's extension.json, then add it on
top of an Async Serial analyzer. Host test without Logic 2: saleae-box python -m pytest -q <this dir>.
"""
from saleae.analyzers import AnalyzerFrame, ChoicesSetting, HighLevelAnalyzer, NumberSetting


class Hla(HighLevelAnalyzer):
    delimiter = ChoicesSetting(choices=("LF", "CR"), label="Line end")
    max_len = NumberSetting(label="Max line length", min_value=1, max_value=4096)
    result_types = {"line": {"format": "{{data.text}}"}, "overflow": {"format": "line longer than {{data.max}}"}}

    def __init__(self):
        self.end = 10 if self.delimiter == "LF" else 13
        self.buf = bytearray()
        self.t0 = None

    def decode(self, frame: AnalyzerFrame):
        if frame.type != "data" or frame.data.get("error"):
            return None
        if self.t0 is None:
            self.t0 = frame.start_time
        b = frame.data["data"][0]
        if b == self.end:
            text = self.buf.decode("latin-1").rstrip("\r\n")
            out = AnalyzerFrame("line", self.t0, frame.end_time, {"text": text})
            self.buf, self.t0 = bytearray(), None
            return out
        self.buf.append(b)
        if len(self.buf) > self.max_len:
            out = AnalyzerFrame("overflow", self.t0, frame.end_time, {"max": int(self.max_len)})
            self.buf, self.t0 = bytearray(), None
            return out
        return None
