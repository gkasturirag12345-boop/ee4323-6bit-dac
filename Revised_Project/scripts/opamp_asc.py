"""Draw the folded-cascode op-amp (handout p.4 arrangement) as a wired LTspice block schematic.
Ports: VDD, VBN, VCN, VINP, VINN, VOUT (ground is the global node 0)."""
from ascgen import Sheet
import opamp_net

q = opamp_net.DEF


def um(v):
    return f"{v * 1e6:g}u"


def draw(path):
    s = Sheet(2900, 1100)
    YV, YBP, Y1, YCP, Y2, YT, Y3, Y4, Y5, YF1, YCN, YBN, YF2, YG = 0, 64, 112, 240, 288, 400, 416, 480, 576, 576, 688, 720, 784, 816
    rail, gnd, bp, cp, cn, bn = [], [], [], [], [], []
    X, Xt = 384, 896
    xa, xb = Xt - 80, Xt + 176
    XL, XR, XS, XO = 1344, 1696, 2080, 2400
    nu = um(q["WNU"])

    def pstack(top, cas, x, gate_top_bus=True):
        """PMOS source (Y1) + cascode (Y2) column at x, bodies to VDD."""
        s.wire(top.p("S"), (x + 48, YV)); rail.append(x + 48)
        s.wire(top.p("D"), cas.p("S"))
        s.wire(top.p("B"), (x + 64, Y1 + 32), (x + 64, YV)); rail.append(x + 64)
        s.wire(cas.p("B"), (x + 64, Y2 + 32), (x + 64, Y1 + 32))
        if gate_top_bus:
            s.wire(top.p("G"), (x - 16, Y1 + 48), (x - 16, YBP)); bp.append(x - 16)
        s.wire(cas.p("G"), (x - 16, Y2 + 48), (x - 16, YCP)); cp.append(x - 16)

    def nstack(casn, botn, x):
        """NMOS cascode (Y4) + sink (Y5) at x: gates to VCN / VBN buses, bodies and source to GND."""
        s.wire(casn.p("S"), botn.p("D"))
        s.wire(botn.p("S"), (x + 48, YG)); gnd.append(x + 48)
        s.wire(casn.p("B"), (x + 64, Y4 + 64), (x + 64, Y5 + 64))
        s.wire(botn.p("B"), (x + 64, Y5 + 64), (x + 64, YG)); gnd.append(x + 64)
        s.wire(casn.p("G"), (x - 16, Y4 + 48), (x - 16, YCN)); cn.append(x - 16)
        s.wire(botn.p("G"), (x - 32, Y5 + 48), (x - 32, YBN)); bn.append(x - 32)

    # ---------- bias: VDD - M49 - M48 - RB - M47 - M46 - GND
    m49 = s.pmos("M49", X, Y1, um(q["W49"])); m48 = s.pmos("M48", X, Y2, um(q["W48"]))
    pstack(m49, m48, X, gate_top_bus=True)
    rb = s.res("RB", X + 32, Y2 + 96, f"{q['RB'] / 1e3:g}k")       # A at (X+48, 400), B at (X+48, 480)
    s.wire(m48.p("D"), rb.p("A"))
    s.wire(rb.p("A"), (X - 112, YT), (X - 112, YBP)); bp.append(X - 112)                 # VBP1 node
    m47 = s.nmos("M47", X, Y4, nu, 2); m46 = s.nmos("M46", X, Y5, nu, 2)
    s.wire(rb.p("B"), m47.p("D"))
    s.wire(rb.p("B"), (X - 144, Y4), (X - 144, YCP)); cp.append(X - 144)                 # VCP1 node
    s.wire(m47.p("S"), m46.p("D"))
    s.wire(m46.p("S"), (X + 48, YG)); gnd.append(X + 48)
    s.wire(m47.p("B"), (X + 64, Y4 + 64), (X + 64, Y5 + 64))
    s.wire(m46.p("B"), (X + 64, Y5 + 64), (X + 64, YG)); gnd.append(X + 64)
    s.wire(m47.p("G"), (X - 64, Y4 + 48), (X - 256, Y4 + 48)); s.flag((X - 256, Y4 + 48), "VCN", "In")
    s.wire((X - 64, Y4 + 48), (X - 64, YCN)); cn.append(X - 64)
    s.wire(m46.p("G"), (X - 96, Y5 + 48), (X - 256, Y5 + 48)); s.flag((X - 256, Y5 + 48), "VBN", "In")
    s.wire((X - 96, Y5 + 48), (X - 96, YBN)); bn.append(X - 96)

    # ---------- tail current source and PMOS input pair
    m30 = s.pmos("M30", Xt, Y1, um(q["W30"])); m31 = s.pmos("M31", Xt, Y2, um(q["W31"]))
    pstack(m30, m31, Xt)
    s.wire(m31.p("D"), (Xt + 48, YT))
    s.wire((xa, YT), (Xt + 48, YT), (xb, YT))
    m32 = s.pmos("M32", xa - 48, Y3, um(q["W32"]))                 # inverting input
    m33 = s.pmos("M33", xb + 48, Y3, um(q["W32"]), orient="M0")    # non-inverting input
    s.wire((xa, YT), m32.p("S")); s.wire((xb, YT), m33.p("S"))
    s.wire(m32.p("B"), (xa + 16, Y3 + 32), (xa + 16, YV)); rail.append(xa + 16)
    s.wire(m33.p("B"), (xb - 16, Y3 + 32), (xb - 16, YV)); rail.append(xb - 16)
    s.wire(m32.p("G"), (xa - 112, Y3 + 48)); s.flag((xa - 112, Y3 + 48), "VINN", "In")
    s.wire(m33.p("G"), (xb + 112, Y3 + 48)); s.flag((xb + 112, Y3 + 48), "VINP", "In")

    # ---------- folded cascode: left column (diode side, node LFT) and right column (output O1)
    m37 = s.pmos("M37", XL, Y1, um(q["W37"])); m36 = s.pmos("M36", XL, Y2, um(q["W36"]))
    m38 = s.pmos("M38", XR, Y1, um(q["W37"])); m39 = s.pmos("M39", XR, Y2, um(q["W36"]))
    pstack(m37, m36, XL, gate_top_bus=False); pstack(m38, m39, XR, gate_top_bus=False)
    m35 = s.nmos("M35", XL, Y4, nu, 4); m34 = s.nmos("M34", XL, Y5, nu, 9)
    m40 = s.nmos("M40", XR, Y4, nu, 4); m41 = s.nmos("M41", XR, Y5, nu, 9)
    nstack(m35, m34, XL); nstack(m40, m41, XR)
    # LFT node: M36 drain - M35 drain, tied to the M37/M38 gates
    s.wire(m36.p("D"), (XL + 48, YT + 16), m35.p("D"))
    s.wire((XL + 48, YT + 16), (XL - 32, YT + 16), (XL - 32, Y1 + 48), (XL - 32, 96))
    s.wire((XL - 32, Y1 + 48), m37.p("G"))
    s.wire((XL - 32, 96), (XR - 32, 96), (XR - 32, Y1 + 48), m38.p("G"))
    # O1 node: M39 drain - M40 drain
    s.wire(m39.p("D"), (XR + 48, Y4 - 16), m40.p("D"))
    # F1: M32 drain -> M35 source / M34 drain
    s.wire(m32.p("D"), (xa, YF1), (XL + 48, YF1))
    # F2: M33 drain routed below the bias buses -> M40 source / M41 drain (and compensation cap CA)
    s.wire(m33.p("D"), (xb, YF2), (XR + 112, YF2), (XR + 112, YF1), (XR + 48, YF1))

    # ---------- second stage M44/M43 (PMOS load) + M42, compensation CA, output follower M45 + ROUT
    m44 = s.pmos("M44", XS, Y1, um(q["W44"])); m43 = s.pmos("M43", XS, Y2, um(q["W43"]))
    pstack(m44, m43, XS)
    m42 = s.nmos("M42", XS, Y4, um(q["W42"]))
    s.wire(m43.p("D"), (XS + 48, 432), m42.p("D"))                                # node G45
    s.wire(m42.p("S"), (XS + 48, YG)); gnd.append(XS + 48)
    s.wire(m42.p("B"), (XS + 64, Y4 + 64), (XS + 64, YG)); gnd.append(XS + 64)
    s.wire((XR + 48, Y4 - 16), (XS - 32, Y4 - 16), (XS - 32, Y4 + 48), m42.p("G"))  # O1 -> M42 gate
    ca = s.cap("CA", XR + 96, 496, f"{q['CA'] * 1e12:g}p")                         # A (XR+112, 496), B (XR+112, 560)
    s.wire(ca.p("B"), (XR + 112, YF1))
    s.wire(ca.p("A"), (XR + 112, 432), (XS + 48, 432), (XO - 32, 432), (XO - 32, Y4 + 48))
    m45 = s.nmos("M45", XO, Y4, um(q["W45"]), l=um(q["L45"]))
    s.wire((XO - 32, Y4 + 48), m45.p("G"))
    s.wire(m45.p("D"), (XO + 48, YV)); rail.append(XO + 48)
    ro = s.res("ROUT", XO + 32, 592, f"{q['ROUT'] / 1e3:g}k")                     # A (XO+48, 608), B (XO+48, 688)
    s.wire(m45.p("S"), (XO + 48, 592), ro.p("A"))
    s.wire((XO + 48, 592), (XO + 208, 592)); s.flag((XO + 208, 592), "VOUT", "Out")
    s.wire(m45.p("B"), (XO + 64, Y4 + 64), (XO + 64, YG)); gnd.append(XO + 64)
    s.wire(ro.p("B"), (XO + 48, YG)); gnd.append(XO + 48)

    def chain(xs, y):
        xs = sorted(set(xs))
        for x0, x1 in zip(xs, xs[1:]):
            s.wire((x0, y), (x1, y))
    chain(rail + [XO + 208], YV); s.flag((XO + 208, YV), "VDD", "BiDir")
    chain(bp, YBP); chain(cp, YCP); chain(cn, YCN); chain(bn, YBN); chain(gnd, YG)
    s.wire((XO + 64, YG), (XO + 64, YG + 32)); s.gnd((XO + 64, YG + 32))
    for name, y, x in (("VBP1", YBP, 1200), ("VCP1", YCP, 1200), ("VCN", YCN, 1200), ("VBN", YBN, 1232)):
        s.flag((x, y), name)
    for name, pt in (("LFT", (XL - 32, 256)), ("O1", (XS - 160, Y4 - 16)), ("G45", (XS + 240, 432)),
                     ("F1", (1150, YF1)), ("F2", (1500, YF2)), ("TAIL", (Xt - 24, YT))):
        s.flag(pt, name)
    s.text(128, YG + 96, "Ground-compatible folded-cascode op-amp: PMOS input pair M32 (-) / M33 (+), NMOS folding M34/M41 + "
           "cascodes M35/M40, PMOS cascode mirror load M36-M39, second stage M42 with M43/M44 load, cascode (Ahuja) "
           "compensation CA to node F2, source-follower output M45 (L = 0.6u) with ROUT pull-down.", 2)
    s.write(path)
    return s


if __name__ == "__main__":
    import sys
    draw(sys.argv[1] if len(sys.argv) > 1 else "OpAmp.asc")
