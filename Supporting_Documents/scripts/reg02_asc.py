"""02_VREF_Regulator.asc: the buffered current-mode voltage reference / LDO of 6-bit DAC.pdf page 3, drawn with wires.

Layout follows the handout: Vunregulated rail on top, GND rail at the bottom, the VBP and VCP gate buses under the
rail, then (left to right) the I_CONST,Gm quad M1-M7 + R1, the VBP diode M9/M8 and Mc + Cc1 + R2, the core mirrors
M10-M13 with Mb (A=1) / Ma (A=8) + R3, R4, the bias legs M14-M20 (VCN, VBN), M21/M22 + R5 (VX), and the LDO
(M26/M27 tail, M23/M25 pair, M24a/b-M28a/b load, M29, Cc2 + Rnull, R7/R6).
PMOS bodies -> Vunregulated, NMOS bodies -> GND (handout rule for the VREF block).
draw_block() returns the sheet and the port coordinates so 04 can reuse the identical drawing.
"""
from ascgen import Sheet
import reg_design

YV, YBP, YT, YCP, YC, YG = 0, 64, 112, 256, 288, 1152       # rail, VBP bus, top PMOS row, VCP bus, cascode row, GND rail
YVCN, YVBN = 1056, 1088                                       # VCN / VBN distribution buses
XR = 3392                                                     # right edge (ports)


def um(v):
    return f"{v * 1e6:g}u"


def kohm(v):
    return f"{v / 1e3:g}k"


def draw_block(p=None):
    q = dict(reg_design.DEF, **(p or {}))
    s = Sheet(3700, 1300)
    rail, gnd, bp, cp, vcn, vbn = [], [], [], [], [], []
    pu = q["WPU"]

    def P(name, x, y, w, m=1, orient="R0", l="3u"):
        return s.add("pmos_PHL", name, x, y, orient, "PHL", f"l={l} w={w}" + (f" m={m}" if m > 1 else ""), Sheet.MOSWIN)

    def N(name, x, y, w, m=1, orient="R0"):
        return s.add("nmos_NWS", name, x, y, orient, "NWS", f"l=3u w={w}" + (f" m={m}" if m > 1 else ""), Sheet.MOSWIN)

    def R(name, x, y, val):
        return s.add("R_ndiff", name, x, y, "R0", val, "tc1=1.56e-3 tc2=6.10e-7")

    def pbody(dev, x, y):                         # PMOS (R0 at x,y): body -> Vunregulated rail via x+64
        s.wire(dev.p("B"), (x + 64, y + 32), (x + 64, YV)); rail.append(x + 64)

    def nbody(dev, x, y, side=+1):                # NMOS: body -> GND rail via x+64 (R0) or x-64 (M0)
        bx = x + 64 * side if side > 0 else x - 64
        s.wire(dev.p("B"), (bx, y + 64), (bx, YG)); gnd.append(bx)

    def tognd(pt):
        s.wire(pt, (pt[0], YG)); gnd.append(pt[0])

    def leg(nm_top, nm_cas, x, m):
        """PMOS cascode leg at column x: top device (gate VBP) over cascode (gate VCP)."""
        t = P(nm_top, x, YT, um(pu), m); c = P(nm_cas, x, YC, um(pu), m)
        s.wire(t.p("S"), (x + 48, YV)); rail.append(x + 48)
        s.wire(t.p("D"), c.p("S"))
        pbody(t, x, YT)
        s.wire(c.p("B"), (x + 64, YC + 32), (x + 64, YT + 32))
        s.wire(t.p("G"), (x - 32, YT + 48), (x - 32, YBP)); bp.append(x - 32)
        s.wire(c.p("G"), (x - 16, YC + 48), (x - 16, YCP)); cp.append(x - 16)
        return c.p("D")                            # (x+48, 384)

    # ---------------- I_CONST,Gm: M1 (gate GND) feeding the cross-coupled quad M2/M3/M6/M7 + R1
    m1 = P("M1", 128, YT, um(q["W1"]), l=um(q["L1"]))
    s.wire(m1.p("S"), (176, YV)); rail.append(176); pbody(m1, 128, YT)
    s.wire(m1.p("G"), (80, 160), (80, YG)); gnd.append(80)
    m2 = N("M2", 128, 576, um(q["W2"])); m3 = N("M3", 128, 672, um(q["W3"]))
    s.wire(m1.p("D"), (176, 576))                                          # N1
    s.wire(m2.p("G"), (112, 624), (112, 560), (176, 560))                  # M2 diode
    nbody(m2, 128, 576); nbody(m3, 128, 672); tognd(m3.p("S"))
    m4 = N("M4", 448, 624, um(q["W4"]), q["M4"])
    s.wire((176, 672), (448, 672))                                         # N2 -> M4 gate
    s.wire((416, 672), (416, 800), (704, 800), (704, 720), (736, 720))     # N2 -> M6 gate
    nbody(m4, 448, 624); tognd(m4.p("S"))
    m5 = P("M5", 448, YT, um(q["W5"]))                                     # VCP diode
    s.wire(m5.p("S"), (496, YV)); rail.append(496); pbody(m5, 448, YT)
    s.wire(m5.p("G"), (432, 160), (432, YCP)); cp.append(432)
    s.wire(m5.p("D"), (496, YCP)); cp.append(496)
    s.wire((496, YCP), m4.p("D"))
    # M9/M8 (VBP diode through the cascode), M7, M6, R1
    d8 = leg("M9", "M8", 736, q["MP"])
    m7 = N("M7", 736, 576, um(q["W7"])); m6 = N("M6", 736, 672, um(q["W7"]), q["M6"])
    s.wire(d8, (784, 576))                                                 # VBP column
    s.wire((784, 416), (688, 416), (688, YBP)); bp.append(688)
    s.wire((176, 544), (672, 544), (672, 624), (736, 624))                 # N1 -> M7 gate
    nbody(m7, 736, 576); nbody(m6, 736, 672)
    r1 = R("R1", 768, 752, kohm(q["R1"])); s.wire(m6.p("S"), r1.p("A")); tognd(r1.p("B"))
    s.wire((784, 672), (720, 672), (720, 848), (96, 848), (96, 720), (128, 720))   # N3 -> M3 gate
    # Mc (mirrored, gate faces the core), Cc1, R2
    mc = s.add("nmos_NWS", "Mc", 1072, 576, "M0", "NWS", f"l=3u w={um(q['WC'])}", Sheet.MOSWIN)
    s.wire(mc.p("D"), (1024, YBP)); bp.append(1024)
    tognd(mc.p("S")); s.wire(mc.p("B"), (1008, 640), (1008, YG)); gnd.append(1008)
    s.wire(mc.p("G"), (1104, 624), (1104, 480), (1328, 480))               # node G bus
    cc1 = s.cap("Cc1", 1152, 400, f"{q['CC1'] * 1e12:g}p")
    s.wire(cc1.p("A"), (1168, YBP)); bp.append(1168); s.wire(cc1.p("B"), (1168, 480))
    r2 = R("R2", 1184, 512, kohm(q["R2"])); s.wire(r2.p("A"), (1200, 480)); tognd(r2.p("B"))
    # core: M11/M10 -> Mb (A=1, mirrored), M13/M12 -> Ma (A=8, diode) + R3, R4
    d10 = leg("M11", "M10", 1280, q["MP"])
    mb = s.add("npn_npn", "Mb", 1392, 576, "M0", "npn_EE4323", "1")
    s.wire(d10, mb.p("C")); tognd(mb.p("E"))
    d12 = leg("M13", "M12", 1536, q["MP"])
    ma = s.add("npn_npn", "Ma", 1520, 576, "R0", "npn_EE4323", f"{q['AREA']}")
    s.wire(d12, ma.p("C"))
    s.wire(ma.p("B"), (1488, 624), (1488, 528), (1584, 528))               # Ma diode (node A)
    s.wire(mb.p("B"), (1488, 624))                                         # Mb base -> node A
    r3 = R("R3", 1568, 672, kohm(q["R3"])); s.wire(ma.p("E"), r3.p("A")); tognd(r3.p("B"))
    r4 = R("R4", 1632, 512, kohm(q["R4"])); s.wire((1584, 528), r4.p("A")); tognd(r4.p("B"))
    # bias leg M16/M15 -> M14 diode (VCN)
    d15 = leg("M16", "M15", 1856, q["MP"])
    m14 = N("M14", 1856, 576, um(q["W14"]))
    s.wire(d15, m14.p("D")); nbody(m14, 1856, 576); tognd(m14.p("S"))
    s.wire(m14.p("G"), (1840, 624), (1840, 528), (1904, 528))
    s.wire((1840, 624), (1840, YVCN)); vcn.append(1840)
    # bias leg M20/M19 -> M18 (gate VCN) over M17 (gate = M18 drain = VBN)
    d19 = leg("M20", "M19", 2112, q["MP"])
    m18 = N("M18", 2112, 576, um(q["WNU"]), q["M18"]); m17 = N("M17", 2112, 672, um(q["WNU"]), q["M17"])
    s.wire(d19, m18.p("D")); nbody(m18, 2112, 576); nbody(m17, 2112, 672); tognd(m17.p("S"))
    s.wire(m17.p("G"), (2080, 720), (2080, 528), (2160, 528))
    s.wire((2080, 720), (2080, YVBN)); vbn.append(2080)
    s.wire(m18.p("G"), (2096, 624), (2096, YVCN)); vcn.append(2096)
    # bias leg M22/M21 -> R5 (VX)
    d21 = leg("M22", "M21", 2368, q["MP"])
    r5 = R("R5", 2400, 560, kohm(q["R5"])); s.wire(d21, r5.p("A")); tognd(r5.p("B"))
    # LDO: tail M26/M27 (2 I_CONST), PMOS pair M23 (VX) / M25 (FB, mirrored), NMOS cascode mirror load
    dt = leg("M26", "M27", 2624, q["MTAIL"])
    s.wire(dt, (2672, 448)); s.wire((2544, 448), (2832, 448))
    m23 = P("M23", 2496, 480, um(q["WPAIR"]))
    m25 = s.add("pmos_PHL", "M25", 2880, 480, "M0", "PHL", f"l=3u w={um(q['WPAIR'])}", Sheet.MOSWIN)
    s.wire(m23.p("S"), (2544, 448)); s.wire(m25.p("S"), (2832, 448))
    s.wire(m23.p("B"), (2560, 512), (2560, YV)); rail.append(2560)
    s.wire(m25.p("B"), (2816, 512), (2816, YV)); rail.append(2816)
    s.wire((2416, 528), m23.p("G"))                                        # VX -> M23 gate
    m24b = N("M24b", 2496, 640, um(q["WNU"]), q["MLD"]); m24a = N("M24a", 2496, 736, um(q["WNU"]), q["MLD"])
    m28b = s.add("nmos_NWS", "M28b", 2880, 640, "M0", "NWS", f"l=3u w={um(q['WNU'])} m={q['MLD']}", Sheet.MOSWIN)
    m28a = s.add("nmos_NWS", "M28a", 2880, 736, "M0", "NWS", f"l=3u w={um(q['WNU'])} m={q['MLD']}", Sheet.MOSWIN)
    s.wire(m23.p("D"), m24b.p("D")); s.wire(m25.p("D"), m28b.p("D"))
    s.wire(m24b.p("B"), (2560, 704), (2560, YG)); gnd.append(2560); s.wire(m24a.p("B"), (2560, 800))
    s.wire(m28b.p("B"), (2816, 704), (2816, YG)); gnd.append(2816); s.wire(m28a.p("B"), (2816, 800))
    tognd(m24a.p("S")); tognd(m28a.p("S"))
    s.wire(m24b.p("G"), (2880, 688))                                       # VCN -> cascode gates
    s.wire((2528, 688), (2528, YVCN)); vcn.append(2528)
    s.wire(m24a.p("G"), (2880, 784))                                       # D25 -> M24a / M28a gates
    s.wire((2832, 624), (2928, 624), (2928, 784), (2880, 784))
    # pass device M29, Cc2 + Rnull, R7/R6, VREF
    m29 = P("M29", 3040, YT, um(q["W29"]), l=um(q["L29"]))
    s.wire(m29.p("S"), (3088, YV)); rail.append(3088); pbody(m29, 3040, YT)
    s.wire((2544, 592), (3008, 592), (3008, 160), m29.p("G"))              # GP (error-amp output) -> M29 gate
    s.wire(m29.p("D"), (3088, 240), (XR, 240))                             # VREF
    r7 = R("R7", 3312, 256, kohm(q["R7"])); r6 = R("R6", 3312, 368, kohm(q["R6"]))
    s.wire((3328, 240), r7.p("A")); s.wire(r7.p("B"), r6.p("A")); tognd(r6.p("B"))
    s.wire((3328, 368), (2944, 368), (2944, 528), m25.p("G"))              # FB -> M25 gate
    cc2 = s.cap("Cc2", 3152, 400, f"{q['CC2'] * 1e12:g}p")
    rn = R("Rnull", 3152, 448, kohm(q["RNULL"]))
    s.wire(cc2.p("A"), (3168, 240)); s.wire(cc2.p("B"), rn.p("A")); s.wire(rn.p("B"), (3168, 592), (3008, 592))
    # ---------------- rails and buses
    def bus(xs, y, x_extra=()):
        xs = sorted(set(list(xs) + list(x_extra)))
        for a, b in zip(xs, xs[1:]):
            s.wire((a, y), (b, y))
        return xs
    bus(rail, YV, (0,)); bus(gnd, YG, (0,)); bus(bp, YBP); bus(cp, YCP)
    bus(vcn, YVCN, (XR,)); bus(vbn, YVBN, (XR,))
    # labels
    s.flag((0, YV), "Vunregulated"); s.flag((0, YG), "0")
    s.flag((min(bp), YBP), "VBP"); s.flag((min(cp), YCP), "VCP")
    s.flag((XR, 240), "VREF"); s.flag((XR, YVCN), "VCN"); s.flag((XR, YVBN), "VBN")
    s.flag((2416, 448), "VX"); s.flag((1328, 528), "G"); s.flag((1584, 448), "A")
    s.flag((3328, 368), "FB"); s.flag((3008, 400), "GP")
    for x, y, t in ((240, 448, "I_CONST,Gm (start-up / constant-gm)"), (1232, 432, "I_CONST (= IREF)"),
                    (1600, 800, "IPTAT (R3)"), (1664, 640, "ICTAT (R4)"), (1216, 640, "ICTAT (R2)"),
                    (2640, 416, "2 I_CONST"), (3104, 288, "VREF = VDD of DAC + OpAmp")):
        s.text(x, y, t, 1)
    return s, dict(vun=(0, YV), gnd=(0, YG), vref=(XR, 240), vcn=(XR, YVCN), vbn=(XR, YVBN))


RUNS = {
    "op": ".op",
    "tc": ".dc temp 0 80 1",
    "line": ".dc VUNREG 3.5 6 0.01",
    "load": ".dc IL 0 55m 0.25m",
    "startup": ".tran 0 300u 0 50n",
    "loadstep": ".tran 0 500u 0 20n",
}


def draw_file(active="op", vun="PWL(0 0 20u 5)", il="0", temp=None):
    s, port = draw_block()
    # test fixture: one Vunregulated source, 3 kohm load on VREF and an optional current load IL
    s.add("voltage", "VUNREG", -160, 112, "R0", vun, windows=["WINDOW 0 -120 40 Left 2", "WINDOW 3 -120 72 Left 2"])
    s.wire((-160, 128), (-160, YV), (0, YV)); s.wire((-160, 208), (-160, YG), (0, YG))
    rl = s.add("R_ndiff", "RL", XR + 48, 240, "R0", "3k", "tc1=1.56e-3 tc2=6.10e-7")
    s.wire((XR, 240), (XR + 64, 240), (XR + 64, 256)); s.wire(rl.p("B"), (XR + 64, YG), (XR, YG))
    s.add("current", "IL", XR + 192, 256, "R0", il)
    s.wire((XR + 64, 240), (XR + 192, 240), (XR + 192, 256)); s.wire((XR + 192, 336), (XR + 192, YG), (XR + 64, YG))
    s.flag((XR + 64, YG), "0")
    y = 1248
    s.text(0, y, ".include EE4323_cmos.mos", 2, directive=True)
    s.text(0, y + 40, ".include EE4323_bjt.lib", 2, directive=True)
    if temp is not None:
        s.text(0, y + 80, f".temp {temp}", 2, directive=True)
    s.text(1200, y, "Analyses (one active; the others kept as comments):", 2)
    for k, (key, d) in enumerate(RUNS.items()):
        s.text(1200, y + 40 + 36 * k, d, 2, directive=(key == active))
        s.text(2000, y + 40 + 36 * k, f"<- {key}", 2)
    return s


INTENDED_EXTRA = "VUNREG VUN 0 5\nRL VREF 0 3k\nIL VREF 0 0\n"


if __name__ == "__main__":
    import sim
    draw_file().write(sim.ROOT / "02_VREF_Regulator.asc")
    print("written")
