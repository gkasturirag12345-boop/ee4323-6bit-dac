"""01_Characterisation.asc: the test circuits of Characterisation.pdf drawn with real wires.

A  NMOS output characteristic  (M1, W/L = 2u/2u, sources VGS1, VDS1)
B  NMOS transfer + C body effect (M2, W/L = 2u/2u, sources VGS2, VDS2 = 3 V, VSB; body at -VSB)
D  NPN area 1 and area 8, diode connected, each fed 10 uA from VDD (VBE and delta-VBE vs temperature)
E  PMOS transfer characteristic (M3, W/L = 2u/2u) - used only for the M1 and VREF calculations
One analysis directive is active at a time; RUNS maps each experiment to its directive.
"""
from ascgen import Sheet

RUNS = {
    "A_output": ".dc VDS1 0 5 0.2 VGS1 0 5 1",
    "BC_transfer_body": ".dc VGS2 0 3 0.1 VSB 0 0.2 0.1",
    "D_npn_dc_temp": ".dc temp 0 80 1",
    "D_npn_step_temp": ".step temp 0 80 20\n.op",
    "E_pmos_transfer": ".dc VGP 0 -3 -0.1",
}

INTENDED = """
M1 VD1 VG1 0 0 NWS l=2u w=2u
VGS1 VG1 0 0
VDS1 VD1 0 0
M2 VD2 VG2 0 VB2 NWS l=2u w=2u
VGS2 VG2 0 0
VDS2 VD2 0 3
VSB 0 VB2 0
VDD VDD 0 5
I1 VDD VBE1 10u
Q1 VBE1 VBE1 0 npn_EE4323 1
I2 VDD VBE8 10u
Q2 VBE8 VBE8 0 npn_EE4323 8
M3 VD3 VG3 0 0 PHL l=2u w=2u
VGP VG3 0 0
VDP VD3 0 -3
"""


def vsrc(s, name, x, y, val, orient="R0"):
    return s.add("voltage", name, x, y, orient, val, windows=["WINDOW 0 24 40 Left 2", "WINDOW 3 24 72 Left 2"])


def draw(active="A_output"):
    s = Sheet(2700, 1100)
    W = "l=2u w=2u"
    # ---------------- A: NMOS output characteristic
    s.text(64, -64, "A. NMOS output characteristic: ID vs VDS (VDS 0-5 V / 0.2 V, VGS 0-5 V / 1 V). ID = -I(VDS1)", 2)
    vsrc(s, "VGS1", 96, 160, "0"); s.wire((96, 256), (96, 288)); s.gnd((96, 288))
    m1 = s.add("nmos_NWS", "M1", 224, 128, "R0", "NWS", W, Sheet.MOSWIN)
    s.wire((96, 176), m1.p("G")); s.flag((160, 176), "VG1")
    s.wire(m1.p("S"), (272, 288)); s.gnd((272, 288))
    s.wire(m1.p("B"), (336, 192), (336, 288)); s.gnd((336, 288))
    vsrc(s, "VDS1", 448, 160, "0"); s.wire((448, 256), (448, 288)); s.gnd((448, 288))
    s.wire(m1.p("D"), (272, 64), (448, 64), (448, 176)); s.flag((352, 64), "VD1")
    # ---------------- B/C: NMOS transfer characteristic and body effect
    s.text(640, -64, "B/C. NMOS transfer and body effect: VDS = 3 V, VGS 0-3 V / 0.1 V, VSB = 0, 0.1, 0.2 V (body at -VSB)", 2)
    vsrc(s, "VGS2", 736, 160, "0"); s.wire((736, 256), (736, 288)); s.gnd((736, 288))
    m2 = s.add("nmos_NWS", "M2", 864, 128, "R0", "NWS", W, Sheet.MOSWIN)
    s.wire((736, 176), m2.p("G")); s.flag((800, 176), "VG2")
    s.wire(m2.p("S"), (912, 288)); s.gnd((912, 288))
    vsrc(s, "VSB", 1040, 336, "0", "R180")                     # R180: + at (1040,320) to GND, - at (1040,240) to body
    s.wire(m2.p("B"), (1040, 192), (1040, 240)); s.flag((1040, 192), "VB2")
    s.wire((1040, 320), (1040, 352)); s.gnd((1040, 352))
    vsrc(s, "VDS2", 1184, 160, "3"); s.wire((1184, 256), (1184, 288)); s.gnd((1184, 288))
    s.wire(m2.p("D"), (912, 64), (1184, 64), (1184, 176)); s.flag((1056, 64), "VD2")
    # ---------------- D: NPN area 1 and area 8 at 10 uA
    s.text(1408, -64, "D. NPN, area 1 and area 8, 10 uA each: VBE1, VBE8 and dVBE = VBE1 - VBE8 vs temperature", 2)
    vsrc(s, "VDD", 1440, 160, "5"); s.wire((1440, 256), (1440, 288)); s.gnd((1440, 288))
    s.wire((1440, 176), (1440, 48), (1664, 48)); s.wire((1664, 48), (1920, 48)); s.flag((1440, 48), "VDD")
    for k, (xq, nm, area, node) in enumerate(((1600, "Q1", "1", "VBE1"), (1856, "Q2", "8", "VBE8"))):
        xc = xq + 64
        s.add("current", f"I{k + 1}", xc, 48, "R0", "10u")
        q = s.add("npn_npn", nm, xq, 224, "R0", "npn_EE4323", area)
        s.wire((xc, 128), q.p("C"))
        s.wire(q.p("B"), (xq - 32, 272), (xq - 32, 176), (xc, 176)); s.flag((xq - 32, 176), node)
        s.wire(q.p("E"), (xc, 352)); s.gnd((xc, 352))
        s.text(xc + 32, 112, f"10 uA", 2)
        s.text(xc + 32, 336, f"area = {area}", 2)
    # ---------------- E: PMOS transfer characteristic (source and body at GND, negative gate and drain)
    s.text(2048, -64, "E. PMOS transfer (for M1 / VREF calculations): VSD = 3 V, VSG 0-3 V / 0.1 V. ID = I(VDP)", 2)
    m3 = s.add("pmos_PHL", "M3", 2176, 160, "R0", "PHL", W, Sheet.MOSWIN)
    s.wire(m3.p("S"), (2224, 112)); s.gnd((2224, 112))
    s.wire(m3.p("B"), (2288, 192), (2288, 112)); s.gnd((2288, 112))
    vsrc(s, "VGP", 2080, 224, "0"); s.wire((2080, 240), (2080, 208), m3.p("G")); s.flag((2128, 208), "VG3")
    s.wire((2080, 320), (2080, 352)); s.gnd((2080, 352))
    vsrc(s, "VDP", 2400, 288, "-3"); s.wire(m3.p("D"), (2224, 304), (2400, 304)); s.flag((2320, 304), "VD3")
    s.wire((2400, 384), (2400, 416)); s.gnd((2400, 416))
    # ---------------- directives
    y = 560
    s.text(64, y, ".include EE4323_cmos.mos", 2, directive=True)
    s.text(64, y + 40, ".include EE4323_bjt.lib", 2, directive=True)
    s.text(64, y + 96, "Analyses (exactly one active; the others are kept as comments):", 2)
    for k, (key, d) in enumerate(RUNS.items()):
        s.text(96, y + 136 + 72 * k, d, 2, directive=(key == active))
        s.text(1120, y + 136 + 72 * k, f"<- {key}", 2)
    return s


if __name__ == "__main__":
    import sys
    from pathlib import Path
    import sim
    draw().write(sim.ROOT / "01_Characterisation.asc")
    print("written")
