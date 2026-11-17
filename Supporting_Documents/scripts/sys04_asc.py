"""04_Complete_6Bit_DAC.asc: the complete system drawn flat (no hierarchy, so the submission stays at four .asc files).

The three block drawings are the same code that draws 02 (regulator), 03 (op-amp) and the page-2 DAC core, placed at
offsets and joined with wires: one Vunregulated source, one ground network, VREF -> VDD of the DAC core and of the
op-amp (through the 0 V current monitors V_IDAC and V_IOPAMP), VBN / VCN to both blocks, IOUT -> RDAC and the op-amp
(+) input M32, VOUT -> M33 (-), the ideal VCVS E_IDEAL on its own output VOUT_IDEAL, the optional 50 ohm RLOAD and the
14 logic sources (clk_* / clk_bar_*) wired to the current-steering switch gates.
"""
from ascgen import Sheet
import reg02_asc, dac04_asc, opamp03_asc, sys_design

OX_D, OY_D = 0, 1600          # DAC core origin
OY_O = 1600                   # op-amp origin y (x follows the DAC core width)
Y_STIM, Y_SGND = 3456, 3616   # logic sources and their ground line


def draw(codes=None, T=20e-6, t0=200e-6, vhi=3.62, tr=5e-9, vun="PWL(0 0 20u 5)", rload="50", directives=(),
         stim_text=None, title=None):
    s = Sheet(8400, 3800)
    reg, rp = reg02_asc.draw_block(); s.merge(reg, 0, 0)
    dac, dp = dac04_asc.draw_block(); s.merge(dac, OX_D, OY_D)
    XE = dp["xe"]; OX_O = XE + 448
    oa = opamp03_asc.draw(None); s.merge(oa, OX_O, OY_O)
    D = lambda pt: (pt[0] + OX_D, pt[1] + OY_D)
    O = lambda pt: (pt[0] + OX_O, pt[1] + OY_O)
    # ---- Vunregulated source (the only supply) and the common ground
    s.add("voltage", "VUNREG", -320, 112, "R0", vun, windows=["WINDOW 0 -150 40 Left 2", "WINDOW 3 -150 72 Left 2"])
    s.wire((-320, 128), (-320, 0), rp["vun"])
    s.wire((-320, 208), (-320, 1152), (-160, 1152)); s.wire(rp["gnd"], (-160, 1152), (-160, Y_SGND))
    s.wire((-160, OY_D + 1504), D(dp["gnd"]))
    s.wire(D((XE, 1504)), (O((432, 816))[0], OY_D + 1504), O((432, 816)))              # DAC GND rail -> op-amp GND rail
    # ---- VREF -> VDD: one wired net feeds the DAC core rail and the op-amp rail (handout p.1 "VREG as VDD")
    s.wire(rp["vref"], (3600, 240), (3600, OY_D))                                    # onto the DAC VDD rail
    s.wire((3600, 240), (OX_O + 304, 240), (OX_O + 304, OY_D), O((432, 0)))           # onto the op-amp VDD rail
    s.flag((3600, 240), "VDD"); s.text(3424, 200, "VREF = VDD (VREG used as VDD)", 2)
    # one name per net: drop the block-level labels that would give a wired net a second name
    s.flags = [f for f in s.flags if not ((f[1] == "VREF" and f[0] == rp["vref"]) or f[1] in ("VINP", "VINN"))]
    # ---- VCN / VBN from the regulator to the DAC core and the op-amp
    s.wire(rp["vcn"], (3504, 1056), (3504, 1520), (-64, 1520), (-64, D(dp["vcn"])[1]), D(dp["vcn"]))
    s.wire((3504, 1520), (OX_O + 64, 1520), (OX_O + 64, O((128, 528))[1]), O((128, 528)))
    s.wire(rp["vbn"], (3472, 1088), (3472, 1552), (-96, 1552), (-96, D(dp["vbn"])[1]), D(dp["vbn"]))
    s.wire((3472, 1552), (OX_O + 32, 1552), (OX_O + 32, O((128, 624))[1]), O((128, 624)))
    # ---- IOUT -> op-amp (+) (M32 gate, VINP); unity feedback VOUT -> M33 (-)
    iout = D(dp["iout"])
    s.wire(iout, (O((704, 464))[0], iout[1]), O((704, 464)))
    s.wire(O((2608, 592)), O((2608, 880)), O((1184, 880)), O((1184, 464)))
    if rload:
        s.add("R_ndiff", "RLOAD", O((2672, 592))[0], O((2672, 592))[1], "R0", rload, "tc1=1.56e-3 tc2=6.10e-7")
        s.wire(O((2608, 592)), O((2688, 592)), O((2688, 608))); s.wire(O((2688, 688)), O((2688, 816)), O((2464, 816)))
    # ---- ideal VCVS reference path: E_IDEAL VOUT_IDEAL 0 IOUT VOUT_IDEAL 1e6 (input draws no current)
    ex = iout[0] + 160
    s.add("e", "E_IDEAL", ex, 2560, "R0", "1e6", windows=["WINDOW 0 24 104 Left 2", "WINDOW 3 24 136 Left 2"])
    s.wire((ex - 96, iout[1]), (ex - 96, 2592), (ex - 48, 2592))
    s.wire((ex, 2576), (ex + 96, 2576), (ex + 96, 2704), (ex - 80, 2704), (ex - 80, 2640), (ex - 48, 2640))
    s.wire((ex, 2656), (ex, OY_D + 1504))
    s.flag((ex + 96, 2576), "VOUT_IDEAL"); s.flag(iout, "IOUT"); s.flag(O((2608, 880)), "VOUT")
    # ---- 14 logic sources (staggered below the DAC GND rail, wired up to the switch gates)
    gates = sorted(((name, D(pt)) for name, pt in dp["gates"].items()), key=lambda kv: kv[1][0])
    flagpt = {}
    for name, (gx, gy) in gates:                       # the gate wires end on the label points left/right of each gate
        flagpt[name] = (gx - 32, gy) if name.startswith("clk_bar") is False else (gx + 32, gy)
    codes = codes if codes is not None else list(range(64))
    stim = stim_text if stim_text is not None else sys_design.pwl_sources(codes, t0, T, vhi, tr)
    vals = {l.split()[1]: l.split(" ", 3)[3] for l in stim.splitlines()}
    gx_all = [flagpt[n][0] for n, _ in gates]
    xs_list, x = [], 1232
    while len(xs_list) < len(gates):                       # source positions clear of every gate riser
        if all(abs(x - gx) >= 64 for gx in gx_all):
            xs_list.append(x); x += 224
        else:
            x += 16
    for k, (name, _) in enumerate(gates):
        xs = xs_list[k]; yk = 3184 + 16 * k
        fx, fy = flagpt[name]
        s.add("voltage", f"V_{name}", xs, Y_STIM, "R0", vals[name], windows=["WINDOW 0 -8 140 Right 1", "WINDOW 3 -8 160 Right 0"])
        s.wire((xs, Y_STIM + 16), (xs, yk), (fx, yk), (fx, fy))
        s.wire((xs, Y_STIM + 96), (xs, Y_SGND))
    s.wire((-160, Y_SGND), (xs_list[-1], Y_SGND))
    s.flag((-160, Y_SGND), "0")
    # ---- text and directives
    y = 3700
    s.text(0, y, title or "Complete 6-bit segmented current-steering DAC (6-bit DAC.pdf pages 1-4): voltage regulator (top), "
           "DAC core (bottom left), folded-cascode op-amp (right). One Vunregulated source, one ground.", 2)
    for k, d in enumerate([".include EE4323_cmos.mos", ".include EE4323_bjt.lib"] + list(directives or
                          [f".tran 0 {t0 + len(codes) * T:.6g} 0 {T / 200:.4g}"])):
        s.text(0, y + 48 + 40 * k, d, 2, directive=True)
    return s


def intended(rload="50", stim=""):
    loads = f"RLOAD VOUT 0 {rload}\n" if rload else ""
    return sys_design.netlist(vun="PWL(0 0 20u 5)", loads=loads, stim=stim)
