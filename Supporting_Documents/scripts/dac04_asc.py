"""DAC core of 6-bit DAC.pdf page 2, drawn with wires (used inside 04_Complete_6Bit_DAC.asc).

Left: VBP2/VCP2 bias (M53/M52 + RB2 + M51/M50) and the ladder-sink bias (M54/M55 + RB3 + M56/M57).
Middle: W-2W ladder - series devices M66/M71/M76 drawn horizontally on the source line, shunt stacks
M62/M63, M67/M68, M72/M73, M77/M78 and the terminator M61/M60, sunk by M59 and the 16 series NMOS M58a-p
(drawn as four columns of four). Right: ladder input source M82/M81 and the unary sources M83/M84, M87/M88, M91/M92.
Every source has its PMOS switch pair (Bk / Dk -> GND, Bk_bar / Dk_bar -> IOUT). IOUT -> RDAC -> GND.
PMOS bodies -> VDD (main rail, or the local VDD line above the switches), NMOS bodies -> GND.
draw_block() returns the sheet and the port coordinates (VDD, GND, VBN, VCN, IOUT and the 14 switch gates).
"""
from ascgen import Sheet
import dac_design

YV, YB2, YC2, Y1, Y2 = 0, 64, 96, 144, 240          # VDD rail, VBP2 bus, VCP2 bus, PMOS rows
YG1, YS, YG2, YVL, YSW, YIO, YNB = 368, 448, 720, 656, 704, 864, 912
YG = 1504                                            # GND rail


def um(v):
    return f"{v * 1e6:g}u"


def draw_block(p=None):
    q = dict(dac_design.DEF, **(p or {}))
    s = Sheet(5200, 1700)
    rail, gnd, b2, c2, g1, g2, vl, io, nb = [], [], [], [], [], [], [], [], []
    gates = {}

    def P(name, x, y, w, m=1, orient="R0"):
        return s.add("pmos_PHL", name, x, y, orient, "PHL", f"l=3u w={w}" + (f" m={m}" if m > 1 else ""), Sheet.MOSWIN)

    def N(name, x, y, w, m=1, orient="R0"):
        return s.add("nmos_NWS", name, x, y, orient, "NWS", f"l=3u w={w}" + (f" m={m}" if m > 1 else ""), Sheet.MOSWIN)

    def tognd(pt):
        s.wire(pt, (pt[0], YG)); gnd.append(pt[0])

    def nbody(x, y):                                  # NMOS R0 at (x, y): body -> GND via x+64
        s.wire((x + 48, y + 64), (x + 64, y + 64), (x + 64, YG)); gnd.append(x + 64)

    def pstack(nt, nc, x, w, m):
        """PMOS source (gate VBP2) over cascode (gate VCP2) at column x; returns the cascode drain (x+48, 336)."""
        t = P(nt, x, Y1, w, m); c = P(nc, x, Y2, w, m)
        s.wire(t.p("S"), (x + 48, YV)); rail.append(x + 48)
        s.wire(t.p("B"), (x + 64, Y1 + 32), (x + 64, YV)); rail.append(x + 64)
        s.wire(c.p("B"), (x + 64, Y2 + 32), (x + 64, Y1 + 32))
        s.wire(t.p("G"), (x - 32, Y1 + 48), (x - 32, YB2)); b2.append(x - 32)
        s.wire(c.p("G"), (x - 16, Y2 + 48), (x - 16, YC2)); c2.append(x - 16)
        return c.p("D")

    def switches(xn, yx, n_gnd, n_out, bit):
        """Switch pair under node (xn, yx): n_gnd (gate bit) -> GND on the left, n_out (gate bit_bar) -> IOUT on the right."""
        x = xn - 48
        s.wire((xn, yx), (xn, YSW - 16)); s.wire((x - 48, YSW - 16), (x + 96, YSW - 16))
        sg = P(n_gnd, x - 96, YSW, um(q["WSW"])); so = P(n_out, x + 144, YSW, um(q["WSW"]), orient="M0")
        s.wire((x - 48, YSW - 16), sg.p("S")); s.wire((x + 96, YSW - 16), so.p("S"))
        s.wire(sg.p("B"), (x - 64, YSW + 32), (x - 64, YVL)); vl.append(x - 64)
        s.wire(so.p("B"), (x + 112, YSW + 32), (x + 112, YVL)); vl.append(x + 112)
        tognd(sg.p("D"))
        s.wire(so.p("D"), (x + 96, YIO)); io.append(x + 96)
        gates[f"clk_{bit}"] = sg.p("G"); gates[f"clk_bar_{bit}"] = so.p("G")
        s.flag((x - 128, YSW + 48), f"clk_{bit}"); s.wire(sg.p("G"), (x - 128, YSW + 48))
        s.flag((x + 176, YSW + 48), f"clk_bar_{bit}"); s.wire(so.p("G"), (x + 176, YSW + 48))

    # ---------------- VBP2 / VCP2 bias: M53 / M52 + RB2 + M51 (VCN) / M50 (VBN)
    X = 256
    d52 = pstack("M53", "M52", X, um(q["WPS"]), q["MBIAS"])
    rb2 = s.add("R_ndiff", "RB2", X + 32, 352, "R0", f"{q['RB2'] / 1e3:g}k", "tc1=1.56e-3 tc2=6.10e-7")
    s.wire(d52, rb2.p("A"))
    s.wire((X + 48, 352), (X - 48, 352), (X - 48, YB2)); b2.append(X - 48)          # VBP2 = top of RB2
    m51 = N("M51", X, 448, um(q["WNB"]), q["M50"]); m50 = N("M50", X, 544, um(q["WNB"]), q["M50"])
    s.wire(rb2.p("B"), (X + 80, 448), (X + 80, YC2)); c2.append(X + 80)               # VCP2 = bottom of RB2
    nbody(X, 448); nbody(X, 544); tognd(m50.p("S"))
    s.wire(m51.p("G"), (X - 96, 496)); s.wire(m50.p("G"), (X - 128, 592))
    port = dict(vcn=(X - 96, 496), vbn=(X - 128, 592))
    # ---------------- ladder sink bias: M54 / M55 + RB3 + M56 / M57 -> NC2 (top of RB3), NB2 (bottom)
    X = 576
    d55 = pstack("M54", "M55", X, um(q["WPS"]), q["MSRC"])
    rb3 = s.add("R_ndiff", "RB3", X + 32, 352, "R0", f"{q['RB3'] / 1e3:g}k", "tc1=1.56e-3 tc2=6.10e-7")
    s.wire(d55, rb3.p("A"))
    m56 = N("M56", X, 448, um(q["WN56"])); m57 = N("M57", X, 544, um(q["WN56"]))
    nbody(X, 448); nbody(X, 544); tognd(m57.p("S"))
    s.wire((X + 48, 352), (X - 48, 352), (X - 48, 496), m56.p("G"))                 # NC2 -> M56 gate
    s.wire(rb3.p("B"), (X + 112, 448), (X + 112, 688), (X - 64, 688), (X - 64, 592), m57.p("G"))   # NB2 -> M57 gate
    s.wire((X + 112, 688), (X + 112, YNB)); nb.append(X + 112)                        # NB2 distribution
    s.flag((X - 48, 416), "NC2"); s.flag((X + 112, 560), "NB2")
    # ---------------- W-2W ladder
    W, W2 = q["WL"], 2 * q["WL"]
    PITCH = 448                                       # column pitch (room for each switch pair and its labels)
    xt, xs = 1152, [1408 + PITCH * k for k in range(4)]   # terminator column; shunt columns for S1..S4 (B6, B5, B4, B3)
    names = [("M62", "M63", "M64", "M65", "B6", 1), ("M67", "M68", "M69", "M70", "B5", 2),
             ("M72", "M73", "M74", "M75", "B4", 4), ("M77", "M78", "M79", "M80", "B3", 8)]
    # terminator M61 (diode, G1) over M60 (diode, G2)
    m61 = P("M61", xt, YS, um(W)); m60 = P("M60", xt, YS + 96, um(q["WCAS"]))
    s.wire(m61.p("G"), (xt - 16, YS + 48), (xt - 16, YG1)); g1.append(xt - 16)
    s.wire(m61.p("D"), (xt - 48, YS + 96), (xt - 48, YG1)); g1.append(xt - 48)
    s.wire(m60.p("G"), (xt - 32, YS + 144), (xt - 32, YG2)); g2.append(xt - 32)
    s.wire(m60.p("D"), (xt + 48, YG2)); g2.append(xt + 48)
    s.wire(m61.p("B"), (xt + 64, YS + 32), (xt + 64, YV)); rail.append(xt + 64)
    s.wire(m60.p("B"), (xt + 64, YS + 128), (xt + 64, YS + 32))
    # M59 (cascode, gate NC2) and the 16-device chain M58a..p (4 columns x 4)
    m59 = N("M59", xt, 784, um(q["WN56"]))
    s.wire((xt + 48, YG2), m59.p("D")); nbody(xt, 784)
    s.wire(m59.p("G"), (xt - 80, 832), (xt - 80, 352), (624, 352))                   # NC2 -> M59 gate
    top = m59.p("S")                                                                   # (xt+48, 880)
    cols = [704, 832, 960, 1088]
    s.wire(top, (xt + 48, 928), (cols[0] + 48, 928), (cols[0] + 48, 960))
    letters = "abcdefghijklmnop"
    for c, cx in enumerate(cols):
        for r in range(4):
            k = 4 * c + r
            y = 960 + 96 * r
            m = N("M58" + letters[k], cx, y, um(q["W58"]))
            nbody(cx, y)
            s.wire(m.p("G"), (cx - 16, y + 48), (cx - 16, YNB)); nb.append(cx - 16)
        bot = (cx + 48, 960 + 96 * 4)                                                  # source of the 4th device
        if c < 3:
            s.wire(bot, (cx + 48, 1376), (cx + 96, 1376), (cx + 96, 944), (cols[c + 1] + 48, 944), (cols[c + 1] + 48, 960))
        else:
            tognd(bot)
    # shunt stacks + switch pairs
    for (nt, nc, ng, no, bit, wt), x in zip(names, xs):
        t = P(nt, x, YS, um(W)); c = P(nc, x, YS + 96, um(q["WCAS"]), wt)
        s.wire(t.p("G"), (x - 16, YS + 48), (x - 16, YG1)); g1.append(x - 16)
        s.wire(c.p("G"), (x - 32, YS + 144), (x - 32, YG2)); g2.append(x - 32)
        s.wire(t.p("B"), (x + 64, YS + 32), (x + 64, YV)); rail.append(x + 64)
        s.wire(c.p("B"), (x + 64, YS + 128), (x + 64, YS + 32))
        switches(x + 48, YS + 192, ng, no, bit)
    # series devices (2W) on the source line: M66 (S2 -> S1), M71 (S3 -> S2), M76 (S4 -> S3); R90: S right, D left, G above
    sline = [(xt + 48, YS), (xs[0] + 48, YS)]
    for nm, k in (("M66", 0), ("M71", 1), ("M76", 2)):
        xr = xs[k + 1] - 64                                                            # source pin x (right)
        dev = s.add("pmos_PHL", nm, xr, YS - 48, "R90", "PHL", f"l=3u w={um(W2)}", ["WINDOW 0 -64 -40 Left 2", "WINDOW 123 -64 -72 Left 2", "WINDOW 3 -64 -104 Left 2"])
        s.wire((xs[k] + 48, YS), (xr - 96, YS)); s.wire((xr, YS), (xs[k + 1] + 48, YS))
        s.wire((xr - 48, YS - 48), (xr - 48, YG1)); g1.append(xr - 48)
        s.wire((xr - 32, YS), (xr - 32, YV)); rail.append(xr - 32)                     # body -> VDD
    s.wire((xt + 48, YS), (xs[0] + 48, YS))
    # ladder input M82 / M81 feeding S4
    X81 = xs[3] + 384
    d81 = pstack("M82", "M81", X81, um(q["WPS"]), q["MSRC"])
    s.wire(d81, (X81 + 48, YS), (xs[3] + 48, YS))
    # unary sources and their switch pairs
    for (nt, nc, ng, no, bit), x in zip((("M83", "M84", "M85", "M86", "D3"), ("M87", "M88", "M89", "M90", "D2"),
                                         ("M91", "M92", "M93", "M94", "D1")), [X81 + 384 * (k + 1) for k in range(3)]):
        d = pstack(nt, nc, x, um(q["WPS"]), q["MSRC"])
        switches(x + 48, 336, ng, no, bit)
    # RDAC on the IOUT bus
    XRD = X81 + 384 * 3 + 352; XE = XRD + 160
    rd = s.add("R_ndiff", "RDAC", XRD - 16, YIO, "R0", f"{q['RDAC'] / 1e3:g}k", "tc1=1.56e-3 tc2=6.10e-7")
    s.wire((XRD, YIO), rd.p("A")); io.append(XRD); tognd(rd.p("B"))
    s.wire((XRD, YIO), (XE, YIO)); io.append(XE)
    # ---------------- rails and buses
    def bus(xs_, y, extra=()):
        xs_ = sorted(set(list(xs_) + list(extra)))
        for a, b in zip(xs_, xs_[1:]):
            s.wire((a, y), (b, y))
        return xs_
    bus(gnd, YG, (0, XE)); bus(b2, YB2); bus(c2, YC2); bus(g1, YG1); bus(g2, YG2)
    bus(io, YIO); bus(nb, YNB)
    bus(vl, YVL, (1312,)); s.wire((1312, YVL), (1312, YV)); rail.append(1312)       # local VDD line for the switch bodies
    bus(rail, YV, (0, XE))
    s.flag((0, YV), "VDD"); s.flag((0, YG), "0"); s.flag((XE, YIO), "IOUT")
    s.flag((min(b2), YB2), "VBP2"); s.flag((min(c2), YC2), "VCP2"); s.flag((min(g1), YG1), "G1"); s.flag((min(g2), YG2), "G2")
    s.flag((xs[0] + 48, YS), "S1"); s.flag((xs[3] + 48, YS), "S4")
    for x, y, t in ((1560, 1440, "16 NMOS transistors in series (M58a-p), each W/L = %s/3u" % um(q["W58"])), (xs[1], 300, "W-2W current mirrors"),
                    (X81 + 400, 1440, "IOUT -> RDAC and op-amp (+)")):
        s.text(x, y, t, 2)
    port.update(vdd=(0, YV), gnd=(0, YG), iout=(XE, YIO), gates=gates, xe=XE)
    return s, port


def test_fixture():
    """DAC core alone with ideal VDD / VBN / VCN, static code inputs and the ideal VCVS (for connectivity checks)."""
    s, port = draw_block()
    def src(name, x, y, val):
        s.add("voltage", name, x, y, "R0", val, windows=["WINDOW 0 24 40 Left 2", "WINDOW 3 24 72 Left 2"])
    src("VDD", -320, 64, "3.62"); s.wire((-320, 80), (-320, YV), (0, YV)); s.wire((-320, 160), (-320, YG), (0, YG))
    src("VCN", -192, 480, "1.47423"); s.wire((-192, 496), port["vcn"]); s.wire((-192, 576), (-192, YG))
    src("VBN", -96, 576, "0.96668"); s.wire((-96, 592), port["vbn"]); s.wire((-96, 672), (-96, YG))
    return s
