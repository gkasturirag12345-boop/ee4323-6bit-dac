"""Draw the DAC core as a wired LTspice schematic (hierarchical block: ports VDD, VBN, VCN, IOUT, clk_*, clk_bar_*)."""
from ascgen import Sheet
import dac_net

q = dac_net.DEF
WU = "5u"


def um(v):
    return f"{v * 1e6:g}u"


def draw(path):
    s = Sheet(5800, 1300)
    YV, YBP, Y1, YCP, Y2, YC, Y3, YO, YG = 0, 64, 112, 240, 288, 432, 480, 656, 864
    rail, gndx, bp, cp, io = [], [], [], [], []

    # ---------------- bias column: VDD - M53 - M52 - RB2 - M51 - M50 - GND (generates VBP2, VCP2)
    X = 256
    m53 = s.pmos("M53", X, Y1, WU, 8)
    m52 = s.pmos("M52", X, Y2, WU, 8)
    s.wire(m53.p("S"), (X + 48, YV)); rail.append(X + 48)
    s.wire(m53.p("D"), m52.p("S"))
    s.wire(m53.p("B"), (X + 64, Y1 + 32), (X + 64, YV)); rail.append(X + 64)
    s.wire(m52.p("B"), (X + 64, Y2 + 32), (X + 64, Y1 + 32))
    rb = s.res("RB2", X + 32, Y2 + 144, f"{q['RB2'] / 1e3:g}k")
    nbp = (X + 48, Y2 + 128)                      # VBP2 node = M52 drain = top of RB2
    s.wire(m52.p("D"), nbp, rb.p("A"))
    s.wire(nbp, (X - 96, nbp[1]), (X - 96, YBP)); bp.append(X - 96)
    s.wire(m53.p("G"), (X - 16, Y1 + 48), (X - 16, YBP)); bp.append(X - 16)
    m51 = s.nmos("M51", X, Y2 + 288, WU, 4)
    ncp = (X + 48, Y2 + 256)                      # VCP2 node = bottom of RB2 = M51 drain
    s.wire(rb.p("B"), ncp, m51.p("D"))
    s.wire(ncp, (X - 144, ncp[1]), (X - 144, YCP)); cp.append(X - 144)
    s.wire(m52.p("G"), (X - 48, Y2 + 48), (X - 48, YCP)); cp.append(X - 48)
    m50 = s.nmos("M50", X, m51.y + 128, WU, 4)
    s.wire(m51.p("S"), m50.p("D"))
    s.wire(m50.p("S"), (X + 48, YG)); gndx.append(X + 48)
    s.wire(m51.p("B"), (X + 64, m51.y + 64), (X + 64, m50.y + 64))
    s.wire(m50.p("B"), (X + 64, m50.y + 64), (X + 64, YG)); gndx.append(X + 64)
    s.wire(m51.p("G"), (X - 224, m51.y + 48)); s.flag((X - 224, m51.y + 48), "VCN", "In")
    s.wire(m50.p("G"), (X - 224, m50.y + 48)); s.flag((X - 224, m50.y + 48), "VBN", "In")

    # ---------------- current cells: source (VBP2) / cascode (VCP2) / switch pair
    P = 704
    for k, (bit, m, (ms, mc, mo, md)) in enumerate(dac_net.CELLS):
        X = 928 + P * k
        ws = um(q["WSU"]) if bit.startswith("D") else um(dict(zip(["B3", "B4", "B5", "B6"], q["WSB"]))[bit])
        a = s.pmos(ms, X, Y1, WU, m)
        c = s.pmos(mc, X, Y2, WU, m)
        s.wire(a.p("S"), (X + 48, YV)); rail.append(X + 48)
        s.wire(a.p("D"), c.p("S"))
        s.wire(a.p("B"), (X + 64, Y1 + 32), (X + 64, YV)); rail.append(X + 64)
        s.wire(c.p("B"), (X + 64, Y2 + 32), (X + 64, Y1 + 32))
        s.wire(a.p("G"), (X - 16, Y1 + 48), (X - 16, YBP)); bp.append(X - 16)
        s.wire(c.p("G"), (X - 16, Y2 + 48), (X - 16, YCP)); cp.append(X - 16)
        XL, XR = X - 128, X + 224
        o = s.pmos(mo, XL - 48, Y3, ws)                 # source at (XL, Y3)
        d = s.pmos(md, XR + 48, Y3, ws, orient="M0")    # source at (XR, Y3)
        s.wire(c.p("D"), (X + 48, YC))
        s.wire((XL, YC), (X + 48, YC), (XR, YC))
        s.wire((XL, YC), o.p("S")); s.wire((XR, YC), d.p("S"))
        s.wire(o.p("B"), (XL + 16, Y3 + 32), (XL + 16, YV)); rail.append(XL + 16)
        s.wire(d.p("B"), (XR - 16, Y3 + 32), (XR - 16, YV)); rail.append(XR - 16)
        s.wire(o.p("G"), (XL - 112, Y3 + 48)); s.flag((XL - 112, Y3 + 48), f"clk_bar_{bit}", "In")
        s.wire(d.p("G"), (XR + 112, Y3 + 48)); s.flag((XR + 112, Y3 + 48), f"clk_{bit}", "In")
        s.wire(o.p("D"), (XL, YO)); io.append(XL)
        s.wire(d.p("D"), (XR, YG)); gndx.append(XR)
    XRD = 928 + P * len(dac_net.CELLS) - 128
    r = s.res("RDAC", XRD - 16, YO - 16, f"{q['RDAC'] / 1e3:g}k")
    io.append(XRD)
    s.wire(r.p("B"), (XRD, YG)); gndx.append(XRD)
    s.wire((XRD, YO), (XRD + 192, YO)); s.flag((XRD + 192, YO), "IOUT", "Out")

    def chain(xs, y):
        xs = sorted(set(xs))
        for x0, x1 in zip(xs, xs[1:]):
            s.wire((x0, y), (x1, y))
    chain(rail + [XRD + 192], YV); s.flag((XRD + 192, YV), "VDD", "BiDir")
    chain(bp, YBP); chain(cp, YCP); chain(io, YO); chain(gndx, YG)
    s.wire((XRD, YG), (XRD, YG + 32)); s.gnd((XRD, YG + 32))
    s.flag((928 + P * 3 - 16, YBP), "VBP2"); s.flag((928 + P * 3 - 16, YCP), "VCP2")
    s.text(32, YG + 112, "DAC core: 3 unary cells D1-D3 (16 x I_LSB) + 4 binary cells B3-B6 (8, 4, 2, 1 x I_LSB); unit PMOS W/L = 5u/3u, "
           "I_LSB = 2.3 uA. Each cell: source (VBP2) + cascode (VCP2) + PMOS switch pair; bit = 1 steers the current to IOUT, "
           "bit = 0 dumps it to analog ground. RDAC converts the summed current to the DAC voltage (12.5 mV/LSB).", 2)
    s.write(path)
    return s


if __name__ == "__main__":
    import sys
    draw(sys.argv[1] if len(sys.argv) > 1 else "DAC_Core.asc")
