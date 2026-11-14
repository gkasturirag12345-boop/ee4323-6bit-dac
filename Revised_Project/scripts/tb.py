"""Test-bench schematics (.asc) built on the verified block schematics. All files go to Revised_Project/LTspice."""
import math
import numpy as np
from ascgen import Sheet
import sys_asc, stim

LT = sys_asc.LT
INC = [".include EE4323_cmos.mos", ".include EE4323_bjt.lib"]


def clocks_for(codes, T, t0=300e-6, tr=1e-9):
    src, sched = stim.pwl_sources(t0, T, codes, tr=tr)
    return {l.split()[1]: l.split(" ", 3)[3] for l in src.splitlines()}, sched


def system_tb(name, codes, T, t0=300e-6, vun=None, temp=None, load=None, tr=1e-9, maxstep=None, extra_dirs=(), title=None,
              ammeters=False):
    clk, sched = clocks_for(codes, T, t0, tr)
    tstop = t0 + T * len(codes)
    d = [f".tran 0 {tstop:.6g} 0 {maxstep or T / 200:.4g}"]
    if temp is not None:
        d.append(f".temp {temp}")
    d += list(extra_dirs)
    sys_asc.system(LT / f"{name}.asc", vun=vun or "PWL(0 0 20u 5)", clocks=clk, directives=d, load=load, title=title,
                   ammeters=ammeters)
    return LT / f"{name}.asc", sched


def ripple_pwl(f, amp=0.05, vdc=5.0, t_ramp=20e-6, t_hold=280e-6, periods=None, pts=24):
    """Single-source supply: 0->Vdc ramp, hold, then a sampled sine ripple of amplitude amp at frequency f."""
    periods = periods or max(4, min(40, int(f * 200e-6)))
    out = [(0, 0), (t_ramp, vdc), (t_hold, vdc)]
    for k in range(1, periods * pts + 1):
        t = t_hold + k / (f * pts)
        out.append((t, vdc + amp * math.sin(2 * math.pi * f * (t - t_hold))))
    return "PWL(" + " ".join(f"{t:.9g} {v:.6g}" for t, v in out) + ")", t_hold + periods / f


def _blk(s, block, name, x, y):
    s.add(block, name, x, y)
    pins = sys_asc.symbols()[block]
    return lambda n: (x + pins[n][0], y + pins[n][1])


def _vsrc(s, name, x, y, val, size=2):
    """Voltage source with + at (x, y+16) and - at (x, y+96) grounded."""
    s.add("voltage", name, x, y, "R0", val, windows=[f"WINDOW 0 24 24 Left {size}", f"WINDOW 3 24 104 Left {size}"])
    s.wire((x, y + 96), (x, y + 128)); s.gnd((x, y + 128))
    return (x, y + 16)


def opamp_tb(name, mode, vbn, vcn, load=None, vcm=0.4, sweep=None, cl=None, extra=()):
    """mode 'ac': open-loop AC with DC feedback through a 1 GH inductor and 1 F AC ground (loop broken for AC only).
    mode 'dc': unity-gain buffer DC sweep of VINP.  mode 'step': unity-gain buffer step response."""
    s = Sheet(1800, 900)
    p = _blk(s, "OpAmp", "XOPAMP", 960, 384)
    vdd = _vsrc(s, "VDD", 160, 96, "3"); vb = _vsrc(s, "VBN", 320, 96, f"{vbn:.5g}"); vc = _vsrc(s, "VCN", 480, 96, f"{vcn:.5g}")
    for src, pn, yy in ((vdd, "VDD", 32), (vb, "VBN", 48), (vc, "VCN", 64)):
        t = p(pn)
        s.wire(src, (src[0], yy), (t[0], yy), t)
        s.flag((src[0], yy), pn)
    inp = {"ac": f"{vcm} AC 1", "dc": "0", "step": "PULSE(0.1 0.7 5u 1n 1n 10u 20u)"}[mode]
    vi = _vsrc(s, "VIN", 640, 368, inp)
    s.wire(vi, (vi[0], p("VINP")[1]), p("VINP")); s.flag((vi[0] + 64, p("VINP")[1]), "VINP") if False else None
    vo, vn = p("VOUT"), p("VINN")
    s.wire(vo, (vo[0] + 96, vo[1]), (vo[0] + 224, vo[1])); s.flag((vo[0] + 224, vo[1]), "VOUT")
    if mode == "ac":
        s.add("ind", "Lfb", vo[0] + 80, vo[1] + 48, "R0", "1G")       # pins (16,16) and (16,96)
        s.wire((vo[0] + 96, vo[1]), (vo[0] + 96, vo[1] + 64))
        s.wire((vo[0] + 96, vo[1] + 144), (vo[0] + 96, vo[1] + 224), (vn[0] - 64, vo[1] + 224), (vn[0] - 64, vn[1]), vn)
        c = s.cap("Cfb", vn[0] - 80, vo[1] + 224, "1")
        s.wire(c.p("B"), (vn[0] - 64, vo[1] + 320)); s.gnd((vn[0] - 64, vo[1] + 320))
    else:
        s.wire((vo[0] + 96, vo[1]), (vo[0] + 96, vo[1] + 224), (vn[0] - 64, vo[1] + 224), (vn[0] - 64, vn[1]), vn)
    if load:
        r = s.add("R_ndiff", "RLOAD", vo[0] + 208, vo[1] - 16, "R0", load, "tc1=1.56e-3 tc2=6.10e-7")
        s.wire(r.p("B"), (vo[0] + 224, vo[1] + 128)); s.gnd((vo[0] + 224, vo[1] + 128))
    if cl:
        c = s.cap("CLOAD", vo[0] + 144, vo[1], cl)
        s.wire(c.p("B"), (vo[0] + 160, vo[1] + 96)); s.gnd((vo[0] + 160, vo[1] + 96))
    d = {"ac": [".ac dec 50 1 1G"], "dc": [f".dc VIN {sweep or '0 2 0.005'}"], "step": [".tran 0 30u 0 2n"]}[mode]
    for k, t in enumerate(INC + d + list(extra)):
        s.text(64, 720 + 36 * k, t, 2, directive=True)
    s.write(LT / f"{name}.asc")
    return LT / f"{name}.asc"


def reg_tb(name, vun, directives, load_r="3k", load_i=None, temp=None):
    s = Sheet(1600, 900)
    p = _blk(s, "Voltage_Regulator", "XREG", 640, 320)
    v = _vsrc(s, "Vunregulated", 160, 336, vun)
    s.wire(v, (v[0], p("VUN")[1]), p("VUN")); s.flag((v[0], p("VUN")[1]), "Vunregulated")
    o = p("VREF")
    s.wire(o, (o[0] + 160, o[1]), (o[0] + 352, o[1])); s.flag((o[0] + 352, o[1]), "VREF")
    if load_r:
        r = s.add("R_ndiff", "RL", o[0] + 144, o[1] - 16, "R0", load_r, "tc1=1.56e-3 tc2=6.10e-7")
        s.wire(r.p("B"), (o[0] + 160, o[1] + 160)); s.gnd((o[0] + 160, o[1] + 160))
    if load_i:
        s.add("current", "IL", o[0] + 288, o[1], "R0", load_i)     # pins (0,0) -> (0,80)
        s.wire((o[0] + 288, o[1] + 80), (o[0] + 288, o[1] + 160)); s.gnd((o[0] + 288, o[1] + 160))
    for net in ("VBN", "VCN"):
        t = p(net); s.wire(t, (t[0] + 96, t[1])); s.flag((t[0] + 96, t[1]), net)
    dd = INC + list(directives) + ([f".temp {temp}"] if temp is not None else [])
    for k, t in enumerate(dd):
        s.text(64, 640 + 36 * k, t, 2, directive=True)
    s.write(LT / f"{name}.asc")
    return LT / f"{name}.asc"
