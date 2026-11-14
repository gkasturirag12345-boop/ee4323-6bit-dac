"""Draw the voltage regulator (current-mode bandgap + LDO) as a wired LTspice block schematic.
Ports: VUN (Vunregulated), VREF (= VDD for the rest of the system), VBN, VCN. Ground is the global node 0."""
from ascgen import Sheet
import reg_net

q = reg_net.DEF


def um(v):
    return f"{v * 1e6:g}u"


def kohm(v):
    return f"{v / 1e3:g}k"


def draw(path):
    s = Sheet(5200, 1100)
    YV, YPG, Y1, YCP, Y2, Y4, Y5, YCN, YBN, YSU, YG = 0, 64, 112, 240, 288, 480, 576, 688, 720, 760, 816
    YA, YB, YAO = 400, 416, 464
    rail, gnd, pg, cp, cn, bn, su, cha = [], [], [], [], [], [], [], []
    wp, nu = um(q["WP"]), um(q["WNU"])

    def body_p(dev, x, y):
        s.wire(dev.p("B"), (x + 64, y + 32), (x + 64, YV)); rail.append(x + 64)

    def pcol(top, cas, x, top_on_pg=True):
        s.wire(top.p("S"), (x + 48, YV)); rail.append(x + 48)
        s.wire(top.p("D"), cas.p("S"))
        body_p(top, x, Y1)
        s.wire(cas.p("B"), (x + 64, Y2 + 32), (x + 64, Y1 + 32))
        if top_on_pg:
            s.wire(top.p("G"), (x - 16, Y1 + 48), (x - 16, YPG)); pg.append(x - 16)
        s.wire(cas.p("G"), (x - 16, Y2 + 48), (x - 16, YCP)); cp.append(x - 16)

    def ngnd(dev, x, y):
        """NMOS source and body to the GND rail."""
        s.wire(dev.p("S"), (x + 48, YG)); gnd.append(x + 48)
        s.wire(dev.p("B"), (x + 64, y + 64), (x + 64, YG)); gnd.append(x + 64)

    # ---------- PG generator: diode M9, gain device Mc (driven by AO)
    X = 320
    m9 = s.pmos("M9", X, Y1, wp)
    s.wire(m9.p("S"), (X + 48, YV)); rail.append(X + 48); body_p(m9, X, Y1)
    s.wire(m9.p("G"), (X - 16, Y1 + 48), (X - 16, YPG)); pg.append(X - 16)
    s.wire(m9.p("D"), (X + 48, 256), (X - 32, 256), (X - 32, YPG)); pg.append(X - 32)
    mc = s.nmos("Mc", X, Y4, um(q["WC"]))
    s.wire(mc.p("D"), (X + 48, 256)); ngnd(mc, X, Y4)
    s.wire(mc.p("G"), (X - 16, Y4 + 48), (X - 16, YAO))                                # AO channel (left end)

    # ---------- PTAT/CTAT core, left branch: M11/M10 -> node A, Qb (diode) || R2
    X = 640
    m11 = s.pmos("M11", X, Y1, wp); m10 = s.pmos("M10", X, Y2, wp); pcol(m11, m10, X)
    qb = s.add("npn_npn", "Qb", 624, 496, "R0", "npn_EE4323", "1")                            # C (688,496) B (624,544) E (688,592)
    r2 = s.res("R2", 720, 480, kohm(q["R2"]))                                          # A (736,496) B (736,576)
    s.wire(m10.p("D"), (688, YA), (688, 432), (688, 480), qb.p("C"))
    s.wire((688, 432), (736, 432), r2.p("A"))
    s.wire((688, 480), (608, 480), (608, 544), qb.p("B"))
    s.wire(qb.p("E"), (688, YG)); gnd.append(688)
    s.wire(r2.p("B"), (736, YG)); gnd.append(736)
    cha.append(688)
    # ---------- right branch: M13/M12 -> node B, R3 + Qa (area 8) || R4
    X = 1024
    m13 = s.pmos("M13", X, Y1, wp); m12 = s.pmos("M12", X, Y2, wp); pcol(m13, m12, X)
    r3 = s.res("R3", 1056, 480, kohm(q["R3"]))                                         # A (1072,496) B (1072,576)
    qa = s.add("npn_npn", "Qa", 1008, 592, "R0", "npn_EE4323", f"{q['AREA']}")                 # C (1072,592) B (1008,640) E (1072,688)
    r4 = s.res("R4", 1104, 464, kohm(q["R4"]))                                         # A (1120,480) B (1120,560)
    s.wire(m12.p("D"), (1072, YB), (1072, 432), r3.p("A"))
    s.wire((1072, 432), (1120, 432), r4.p("A"))
    s.wire(r3.p("B"), qa.p("C"))
    s.wire(qa.p("B"), (992, 640), (992, 592), qa.p("C"))
    s.wire(qa.p("E"), (1072, YG)); gnd.append(1072)
    s.wire(r4.p("B"), (1120, YG)); gnd.append(1120)

    # ---------- core error amplifier: tail Mt (PG), PMOS pair Ma (A) / Mb (B), NMOS mirror Mn1/Mn2, Cc1
    X = 1440
    mt = s.pmos("Mt", X, Y1, um(q["WT"]))
    s.wire(mt.p("S"), (X + 48, YV)); rail.append(X + 48); body_p(mt, X, Y1)
    s.wire(mt.p("G"), (X - 16, Y1 + 48), (X - 16, YPG)); pg.append(X - 16)
    ma = s.pmos("Ma", 1328, Y2, um(q["WA"]))                  # S (1376,288) G (1328,336) D (1376,384)
    mb = s.pmos("Mb", 1632, Y2, um(q["WA"]), orient="M0")     # S (1584,288) G (1632,336) D (1584,384)
    s.wire(mt.p("D"), (1488, 272))
    s.wire((1376, 272), (1488, 272), (1584, 272))
    s.wire((1376, 272), ma.p("S")); s.wire((1584, 272), mb.p("S"))
    s.wire(ma.p("B"), (1392, Y2 + 32), (1392, YV)); rail.append(1392)
    s.wire(mb.p("B"), (1568, Y2 + 32), (1568, YV)); rail.append(1568)
    s.wire(ma.p("G"), (1312, 336), (1312, YA)); cha.append(1312)
    s.wire(mb.p("G"), (1648, 336), (1648, YB))
    s.wire((1072, YB), (1648, YB))                                                      # B channel
    mn1 = s.nmos("Mn1", 1328, Y4, um(q["WNL"])); mn2 = s.nmos("Mn2", 1536, Y4, um(q["WNL"]))
    s.wire(ma.p("D"), (1376, 448), mn1.p("D"))                                         # node DL
    s.wire(mn1.p("G"), (1312, 528), (1312, 448), (1376, 448))
    s.wire((1312, 528), (1312, 640), (1520, 640), (1520, 528), mn2.p("G"))
    ngnd(mn1, 1328, Y4); ngnd(mn2, 1536, Y4)
    s.wire(mb.p("D"), (1584, YAO), mn2.p("D"))                                         # node AO
    s.wire((1584, YAO), (1648, YAO), (1648, 496))
    cc1 = s.cap("Cc1", 1632, 496, f"{q['CC1'] * 1e12:g}p")                             # A (1648,496) B (1648,560)
    s.wire(cc1.p("B"), (1648, YG)); gnd.append(1648)
    s.wire((304, YAO), (1584, YAO))                                                     # AO channel to Mc

    # ---------- start-up: M1 (gate to GND, L = 200u) feeds node SU; M2 senses node A; M5/M4/M3 act on SU
    xs = 1888
    m1 = s.pmos("M1", xs, Y1, um(q["W1"]), l=um(q["L1"]))
    s.wire(m1.p("S"), (xs + 48, YV)); rail.append(xs + 48); body_p(m1, xs, Y1)
    s.wire(m1.p("G"), (xs - 16, Y1 + 48), (xs - 16, YG)); gnd.append(xs - 16)
    m2 = s.nmos("M2", xs, Y4, um(q["W2"]))
    s.wire(m1.p("D"), (xs + 48, 448), m2.p("D"))                                       # node SU
    s.wire((xs + 48, 448), (xs + 96, 448), (xs + 96, YSU)); su.append(xs + 96)
    s.wire(m2.p("G"), (xs - 32, Y4 + 48), (xs - 32, YA)); cha.append(xs - 32)
    ngnd(m2, xs, Y4)
    m5 = s.nmos("M5", xs + 192, Y4, um(q["W5"]))
    s.wire(m5.p("D"), (xs + 240, YPG)); pg.append(xs + 240)
    s.wire(m5.p("G"), (xs + 176, Y4 + 48), (xs + 176, YSU)); su.append(xs + 176)
    ngnd(m5, xs + 192, Y4)
    m4 = s.nmos("M4", xs + 384, Y4, um(q["W3"]))
    s.wire(m4.p("D"), (xs + 432, YCP)); cp.append(xs + 432)
    s.wire(m4.p("G"), (xs + 368, Y4 + 48), (xs + 368, YSU)); su.append(xs + 368)
    ngnd(m4, xs + 384, Y4)
    m3 = s.nmos("M3", xs + 576, Y4, um(q["W3"]), l=um(q["L3"]))
    s.wire(m3.p("D"), (xs + 624, YV)); rail.append(xs + 624)
    s.wire(m3.p("G"), (xs + 560, Y4 + 48), (xs + 560, YSU)); su.append(xs + 560)
    s.wire(m3.p("S"), (xs + 672, Y5), (xs + 672, YA)); cha.append(xs + 672)
    s.wire(m3.p("B"), (xs + 640, Y4 + 64), (xs + 640, YG)); gnd.append(xs + 640)

    # ---------- bias outputs: VBN (cascoded diode M14b/M14), VCN (diode M17), internal VCPI (M8 + M7/M18)
    X = 2752
    m16 = s.pmos("M16", X, Y1, wp); m15 = s.pmos("M15", X, Y2, wp); pcol(m16, m15, X)
    m14b = s.nmos("M14b", X, Y4, nu, 6); m14 = s.nmos("M14", X, Y5, nu, 6)
    s.wire(m15.p("D"), (2800, 432), m14b.p("D"))                                       # node VBN
    s.wire(m14b.p("S"), m14.p("D"))
    s.wire((2800, 432), (2720, 432), (2720, Y5 + 48), (2720, YBN)); bn.append(2720)
    s.wire((2720, Y5 + 48), m14.p("G"))
    s.wire(m14b.p("G"), (2736, Y4 + 48), (2736, YCN)); cn.append(2736)
    s.wire(m14b.p("B"), (2816, Y4 + 64), (2816, Y5 + 64))
    ngnd(m14, X, Y5)
    X = 3072
    m20 = s.pmos("M20", X, Y1, wp); m19 = s.pmos("M19", X, Y2, wp); pcol(m20, m19, X)
    m17 = s.nmos("M17", X, Y4, nu)
    s.wire(m19.p("D"), (3120, 432), m17.p("D"))                                        # node VCN
    s.wire((3120, 432), (3056, 432), (3056, Y4 + 48), (3056, YCN)); cn.append(3056)
    s.wire((3056, Y4 + 48), m17.p("G"))
    ngnd(m17, X, Y4)
    X = 3392
    m8 = s.pmos("M8", X, Y1, um(q["WPC"]))
    s.wire(m8.p("S"), (X + 48, YV)); rail.append(X + 48); body_p(m8, X, Y1)
    s.wire(m8.p("G"), (X - 16, Y1 + 48), (X - 16, YCP)); cp.append(X - 16)
    s.wire(m8.p("D"), (X + 48, YCP)); cp.append(X + 48)                                 # M8 diode-connected through the VCPI bus
    m7 = s.nmos("M7", X, Y4, nu, 6); m18 = s.nmos("M18", X, Y5, nu, 6)
    s.wire(m7.p("D"), (X + 48, YCP))
    s.wire(m7.p("S"), m18.p("D"))
    s.wire(m7.p("G"), (X - 16, Y4 + 48), (X - 16, YCN)); cn.append(X - 16)
    s.wire(m18.p("G"), (X - 32, Y5 + 48), (X - 32, YBN)); bn.append(X - 32)
    s.wire(m7.p("B"), (X + 64, Y4 + 64), (X + 64, Y5 + 64))
    ngnd(m18, X, Y5)

    # ---------- reference voltage VX = ICONST x R5
    X = 3712
    m22 = s.pmos("M22", X, Y1, wp); m21 = s.pmos("M21", X, Y2, wp); pcol(m22, m21, X)
    r5 = s.res("R5", 3744, 464, kohm(q["R5"]))                                         # A (3760,480) B (3760,560)
    s.wire(m21.p("D"), (3760, 432), r5.p("A"))
    s.wire(r5.p("B"), (3760, YG)); gnd.append(3760)

    # ---------- LDO error amplifier: PMOS cascode mirror M24a/b, M28a/b; NMOS pair M25 (FB) / M23 (VX); tail M26/M27
    m24a = s.pmos("M24a", 4032, Y1, wp); m24b = s.pmos("M24b", 4032, Y2, wp); pcol(m24a, m24b, 4032, top_on_pg=False)
    m28a = s.pmos("M28a", 4352, Y1, wp); m28b = s.pmos("M28b", 4352, Y2, wp); pcol(m28a, m28b, 4352, top_on_pg=False)
    m25 = s.nmos("M25", 4032, Y4, um(q["WEL"])); m23 = s.nmos("M23", 4352, Y4, um(q["WEL"]))
    s.wire(m24b.p("D"), (4080, 416), m25.p("D"))                                       # node D25
    s.wire((4080, 416), (4000, 416), (4000, Y1 + 48), (4000, 96))
    s.wire((4000, Y1 + 48), m24a.p("G"))
    s.wire((4000, 96), (4320, 96), (4320, Y1 + 48), m28a.p("G"))
    s.wire(m28b.p("D"), (4400, 400), m23.p("D"))                                       # node EOUT
    s.wire((3760, 432), (4320, 432), (4320, Y4 + 48), m23.p("G"))                       # VX -> M23
    s.wire(m25.p("G"), (4016, Y4 + 48), (4016, 448), (4592, 448), (4592, 576), (4624, 576))  # FB -> M25
    s.wire(m25.p("S"), (4080, 592), (4240, 592), (4400, 592), m23.p("S"))              # node TL2
    m26 = s.nmos("M26", 4192, 608, nu, 12); m27 = s.nmos("M27", 4192, 704, nu, 12)
    s.wire((4240, 592), m26.p("D")); s.wire(m26.p("S"), m27.p("D"))
    s.wire(m27.p("S"), (4240, YG)); gnd.append(4240)
    s.wire(m26.p("G"), (4176, 656), (4176, YCN)); cn.append(4176)
    s.wire(m27.p("G"), (4160, 752), (4160, YBN)); bn.append(4160)
    s.wire(m26.p("B"), (4256, 672), (4256, 768), m27.p("B")); s.wire((4256, 768), (4256, YG)); gnd.append(4256)
    s.wire(m25.p("B"), (4096, Y4 + 64), (4096, YG)); gnd.append(4096)
    s.wire(m23.p("B"), (4416, Y4 + 64), (4416, YG)); gnd.append(4416)

    # ---------- pass device M29 (L = 0.6u), divider R7/R6, compensation Cc2 + Rnull, output capacitor CL
    m29 = s.pmos("M29", 4576, Y1, um(q["W29"]), l=um(q["L29"]))
    s.wire(m29.p("S"), (4624, YV)); rail.append(4624)
    s.wire(m29.p("B"), (4640, Y1 + 32), (4640, YV)); rail.append(4640)
    s.wire((4400, 400), (4544, 400), (4544, 288), (4544, Y1 + 48), m29.p("G"))
    r7 = s.res("R7", 4608, 464, kohm(q["R7"]))                                         # A (4624,480) B (4624,560)
    r6 = s.res("R6", 4608, 576, kohm(q["R6"]))                                         # A (4624,592) B (4624,672)
    s.wire(m29.p("D"), (4624, 432), r7.p("A"))
    s.wire(r7.p("B"), (4624, 576), r6.p("A"))
    s.wire(r6.p("B"), (4624, YG)); gnd.append(4624)
    cc2 = s.cap("Cc2", 4688, 288, f"{q['CC2'] * 1e12:g}p")                             # A (4704,288) B (4704,352)
    rnull = s.res("Rnull", 4688, 336, kohm(q["RNULL"]))                                # A (4704,352) B (4704,432)
    s.wire((4544, 288), cc2.p("A")); s.wire(cc2.p("B"), rnull.p("A"))
    s.wire(rnull.p("B"), (4624, 432))
    cl = s.cap("CL", 4848, 208, f"{q['CL'] * 1e9:g}n")                                 # A (4864,208) B (4864,272)
    s.wire(m29.p("D"), (4864, 208), (4992, 208)); s.flag((4992, 208), "VREF", "Out")
    s.wire(cl.p("B"), (4864, YG)); gnd.append(4864)

    def chain(xs, y):
        xs = sorted(set(xs))
        for x0, x1 in zip(xs, xs[1:]):
            s.wire((x0, y), (x1, y))
    chain(rail + [4992], YV); s.flag((4992, YV), "VUN", "BiDir")
    chain(pg, YPG); chain(cp, YCP); chain(cha, YA); chain(su, YSU); chain(gnd, YG)
    chain(cn + [2624], YCN); s.flag((2624, YCN), "VCN", "Out")
    chain(bn + [2624], YBN); s.flag((2624, YBN), "VBN", "Out")
    s.wire((4864, YG), (4864, YG + 32)); s.gnd((4864, YG + 32))
    for name, pt in (("PG", (800, YPG)), ("VCPI", (800, YCP)), ("A", (900, YA)), ("B", (1200, YB)), ("AO", (900, YAO)),
                     ("SU", (2300, YSU)), ("VX", (3900, 432)), ("D25", (4000, 300)), ("EOUT", (4544, 220)),
                     ("FB", (4300, 448)), ("TL2", (4320, 592)), ("TL", (1500, 272))):
        s.flag(pt, name)
    s.text(96, YG + 96, "Voltage regulator (current-mode bandgap + LDO) on Vunregulated: NPN PTAT core Qb (A=1) / Qa (A=8) with R3, "
           "CTAT resistors R2/R4 (Banba-type), equal-current PMOS mirrors M10-M13 driven by error amp Ma/Mb/Mn1/Mn2 + Mc/M9; "
           "start-up M1-M5; bias outputs VBN/VCN; VX = ICONST*R5 drives LDO amp M23/M25 -> pass device M29 -> VREF = VX(1+R7/R6).", 2)
    s.write(path)
    return s


if __name__ == "__main__":
    import sys
    draw(sys.argv[1] if len(sys.argv) > 1 else "Voltage_Regulator.asc")
