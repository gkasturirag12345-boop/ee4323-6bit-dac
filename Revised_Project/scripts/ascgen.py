"""Minimal LTspice .asc writer with real wires, plus a hierarchical block-symbol writer.

Coordinates are LTspice schematic units (grid 16). Orientation transforms were measured
against LTspice 26 netlisting: R0 (x,y), M0 (-x,y), R90 (-y,x), R180 (-x,-y), R270 (y,-x).
"""
from pathlib import Path

PINS = {
    "nmos_NWS": {"D": (48, 0), "G": (0, 48), "S": (48, 96), "B": (48, 64)},
    "pmos_PHL": {"D": (48, 96), "G": (0, 48), "S": (48, 0), "B": (48, 32)},
    "npn_npn": {"C": (64, 0), "B": (0, 48), "E": (64, 96)},
    "R_ndiff": {"A": (16, 16), "B": (16, 96)},
    "cap": {"A": (16, 0), "B": (16, 64)},
    "voltage": {"P": (0, 16), "N": (0, 96)},
}
XF = {"R0": lambda x, y: (x, y), "M0": lambda x, y: (-x, y), "R90": lambda x, y: (-y, x),
      "R180": lambda x, y: (-x, -y), "R270": lambda x, y: (y, -x), "M180": lambda x, y: (x, -y)}


class Inst:
    def __init__(self, sym, name, x, y, orient):
        self.sym, self.name, self.x, self.y, self.orient = sym, name, x, y, orient

    def p(self, pin):
        px, py = PINS[self.sym][pin]
        dx, dy = XF[self.orient](px, py)
        return (self.x + dx, self.y + dy)


class Sheet:
    def __init__(self, w=3200, h=2000):
        self.w, self.h = w, h
        self.insts, self.lines, self.flags, self.texts = [], [], [], []
        self.symattrs = {}

    def add(self, sym, name, x, y, orient="R0", value=None, value2=None, windows=None, extra=()):
        i = Inst(sym, name, x, y, orient)
        self.insts.append(i)
        self.symattrs[name] = (value, value2, windows, list(extra))
        return i

    MOSWIN = ["WINDOW 0 72 16 Left 2", "WINDOW 3 72 48 Left 2", "WINDOW 123 72 80 Left 2"]

    def nmos(self, name, x, y, w, m=1, orient="R0", l="3u"):
        return self.add("nmos_NWS", name, x, y, orient, "NWS", f"l={l} w={w}" + (f" m={m}" if m > 1 else ""), self.MOSWIN)

    def pmos(self, name, x, y, w, m=1, orient="R0", l="3u"):
        return self.add("pmos_PHL", name, x, y, orient, "PHL", f"l={l} w={w}" + (f" m={m}" if m > 1 else ""), self.MOSWIN)

    def res(self, name, x, y, val, orient="R0"):
        return self.add("R_ndiff", name, x, y, orient, val, "tc1=1.56e-3 tc2=6.10e-7")

    def cap(self, name, x, y, val, orient="R0"):
        return self.add("cap", name, x, y, orient, val)

    def wire(self, *pts):
        pts = [tuple(map(int, p)) for p in pts]
        for a, b in zip(pts, pts[1:]):
            if a != b:
                assert a[0] == b[0] or a[1] == b[1], f"non-Manhattan wire {a}->{b}"
                self.lines.append((a, b))

    def flag(self, pt, name, iopin=None):
        self.flags.append((tuple(map(int, pt)), name, iopin))

    def gnd(self, pt):
        self.flag(pt, "0")

    def text(self, x, y, s, size=2, directive=False):
        self.texts.append((x, y, ("!" if directive else ";") + s, size))

    def write(self, path):
        out = ["Version 4", f"SHEET 1 {self.w} {self.h}"]
        for a, b in self.lines:
            out.append(f"WIRE {a[0]} {a[1]} {b[0]} {b[1]}")
        for (x, y), name, io in self.flags:
            out.append(f"FLAG {x} {y} {name}")
            if io:
                out.append(f"IOPIN {x} {y} {io}")
        for i in self.insts:
            out.append(f"SYMBOL {i.sym} {i.x} {i.y} {i.orient}")
            v, v2, win, extra = self.symattrs[i.name]
            for wline in (win or []):
                out.append(wline)
            out.append(f"SYMATTR InstName {i.name}")
            if v is not None:
                out.append(f"SYMATTR Value {v}")
            if v2 is not None:
                out.append(f"SYMATTR Value2 {v2}")
            out += list(extra)
        for x, y, s, size in self.texts:
            out.append(f"TEXT {x} {y} Left {size} {s.replace(chr(10), chr(92) + 'n')}")
        Path(path).write_text("\n".join(out) + "\n")


def block_symbol(path, title, left, right, top=(), bottom=(), w=320, pitch=64):
    """Write a BLOCK .asy: pins on the left/right/top/bottom edges. Returns {pin: (x, y)} for wiring."""
    n = max(len(left), len(right), 1)
    h = pitch * (n + 1)
    out = ["Version 4", "SymbolType BLOCK", f"RECTANGLE Normal {-w // 2} {-h // 2} {w // 2} {h // 2}",
           f"TEXT 0 {-h // 2 + 24} Center 2 {title}"]
    pins = {}
    def put(name, x, y, just):
        pins[name] = (x, y)
        out.extend([f"PIN {x} {y} {just} 8", f"PINATTR PinName {name}", f"PINATTR SpiceOrder {len(pins)}"])
    for k, nme in enumerate(left):
        put(nme, -w // 2, -h // 2 + pitch * (k + 1), "LEFT")
    for k, nme in enumerate(right):
        put(nme, w // 2, -h // 2 + pitch * (k + 1), "RIGHT")
    for k, nme in enumerate(top):
        put(nme, -w // 2 + (w // (len(top) + 1)) // 16 * 16 * (k + 1), -h // 2, "TOP")
    for k, nme in enumerate(bottom):
        put(nme, -w // 2 + (w // (len(bottom) + 1)) // 16 * 16 * (k + 1), h // 2, "BOTTOM")
    Path(path).write_text("\n".join(out) + "\n")
    return pins
