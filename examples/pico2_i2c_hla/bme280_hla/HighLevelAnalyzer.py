"""Logic 2 HLA: turn I2C frames into BME280 register accesses (copy this folder into Logic 2:
Extensions > Load Existing Extension). Runs unchanged in saleae-box's host harness (tools/hla_host.py)."""
from saleae.analyzers import AnalyzerFrame, ChoicesSetting, HighLevelAnalyzer

REGS = {0xD0: "id", 0xE0: "reset", 0xF2: "ctrl_hum", 0xF3: "status", 0xF4: "ctrl_meas", 0xF5: "config",
        0xF7: "press_msb", 0xFA: "temp_msb", 0xFD: "hum_msb"}


class Bme280(HighLevelAnalyzer):
    address = ChoicesSetting(choices=("0x76", "0x77"), label="I2C address")
    result_types = {"reg": {"format": "{{data.op}} {{data.reg}} = {{data.value}}"}}

    def __init__(self):
        self.addr = int(self.address, 16)
        self.mine = False
        self.read = False
        self.ptr = None
        self.buf = []
        self.t0 = 0.0

    def decode(self, frame: AnalyzerFrame):
        if frame.type == "start":
            self.buf, self.t0 = [], frame.start_time
        elif frame.type == "address":
            self.mine = frame.data["address"][0] == self.addr and frame.data["ack"]
            self.read = frame.data["read"]
        elif frame.type == "data" and self.mine:
            self.buf.append(frame.data["data"][0])
        elif frame.type == "stop" and self.mine and self.buf:
            return self._finish(frame.end_time)
        return None

    def _finish(self, end: float):
        if self.read:
            reg, data = self.ptr, self.buf
            op = "read"
        else:
            self.ptr = self.buf[0]
            if len(self.buf) == 1:
                return None          # pointer write before a read: wait for the read
            reg, data, op = self.buf[0], self.buf[1:], "write"
        name = REGS.get(reg, f"0x{reg:02X}")
        return AnalyzerFrame("reg", self.t0, end, {"op": op, "reg": name, "value": " ".join(f"{x:02X}" for x in data)})
