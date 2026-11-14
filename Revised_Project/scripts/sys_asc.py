"""Top-level system schematic (and test benches) built from the hierarchical block schematics.

All .asc/.asy files live in Revised_Project/LTspice so the hierarchy resolves. Blocks:
  Voltage_Regulator (VUN, VREF, VBN, VCN), DAC_Core (VDD, VBN, VCN, IOUT, clk_*, clk_bar_*),
  OpAmp (VINP, VINN, VOUT, VDD, VBN, VCN). Ground is the single global node 0.
"""
from pathlib import Path
from ascgen import Sheet, block_symbol
import stim

LT = Path(__file__).resolve().parents[1] / "LTspice"
CLK = [x for b in stim.BITS for x in (f"clk_{b}", f"clk_bar_{b}")]


def symbols():
    LT.mkdir(exist_ok=True)
    return {
        "Voltage_Regulator": block_symbol(LT / "Voltage_Regulator.asy", "Voltage Regulator", ["VUN"], ["VREF", "VBN", "VCN"], w=384),
        "OpAmp": block_symbol(LT / "OpAmp.asy", "OpAmp", ["VINP", "VINN"], ["VOUT"], top=["VDD", "VBN", "VCN"], w=320),
        "DAC_Core": block_symbol(LT / "DAC_Core.asy", "DAC Core: 3 unary + 4 binary cells", ["VDD", "VBN", "VCN"], ["IOUT"],
                                 bottom=CLK, w=1920),
    }


def system(path, vun="PWL(0 0 20u 5)", clocks=None, directives=(), load=None, title=None, ammeters=False):
    pins = symbols()
    pin = lambda blk, n, x, y: (x + pins[blk][n][0], y + pins[blk][n][1])
    s = Sheet(3900, 1500)
    RX, RY, DX, DY = 512, 320, 1888, 320
    OX, OY = 3264, 288
    s.add("Voltage_Regulator", "XREG", RX, RY)
    s.add("DAC_Core", "XDAC", DX, DY)
    s.add("OpAmp", "XOPAMP", OX, OY)
    # single Vunregulated source -> regulator
    s.add("voltage", "Vunregulated", 96, 336, "R0", vun, windows=["WINDOW 0 24 24 Left 2", "WINDOW 3 24 112 Left 2"])
    vun_pin = pin("Voltage_Regulator", "VUN", RX, RY)
    s.wire((96, 352), (96, vun_pin[1]), vun_pin); s.flag((96, vun_pin[1]), "Vunregulated")
    s.wire((96, 432), (96, 464)); s.gnd((96, 464))
    # regulator outputs -> DAC (straight wires), taps up and over to the op-amp top pins
    taps = {"VDD": (RX + 224, 48), "VBN": (RX + 256, 80), "VCN": (RX + 288, 112)}
    for src, dst in (("VREF", "VDD"), ("VBN", "VBN"), ("VCN", "VCN")):
        a, d = pin("Voltage_Regulator", src, RX, RY), pin("DAC_Core", dst, DX, DY)
        assert a[1] == d[1]
        xt, yt = taps[dst]
        o = pin("OpAmp", dst, OX, OY)
        if ammeters and dst == "VDD":
            # 0 V current monitors: VI_DAC (VDD -> DAC core) and VI_OPAMP (VDD -> op-amp); + terminal on the VDD side
            s.add("voltage", "VI_DAC", d[0] - 112, a[1], "R270", "0", windows=["WINDOW 0 48 -24 Center 1", "WINDOW 3 48 32 Center 0"])
            s.wire(a, (xt, a[1]), (d[0] - 96, a[1])); s.wire((d[0] - 16, a[1]), d)
            s.add("voltage", "VI_OPAMP", o[0] - 176, yt, "R270", "0", windows=["WINDOW 0 48 -24 Center 1", "WINDOW 3 48 32 Center 0"])
            s.wire((xt, a[1]), (xt, yt), (o[0] - 160, yt)); s.wire((o[0] - 80, yt), (o[0], yt), o)
        else:
            s.wire(a, (xt, a[1]), d)
            s.wire((xt, a[1]), (xt, yt), (o[0], yt), o)
        s.flag((xt, yt), dst)
    # DAC output current into the op-amp (+) input; unity-gain feedback VOUT -> VINN
    io, vp = pin("DAC_Core", "IOUT", DX, DY), pin("OpAmp", "VINP", OX, OY)
    assert io[1] == vp[1]
    s.wire(io, (io[0] + 96, io[1]), vp); s.flag((io[0] + 96, io[1]), "IOUT")
    vo, vn = pin("OpAmp", "VOUT", OX, OY), pin("OpAmp", "VINN", OX, OY)
    s.wire(vo, (vo[0] + 64, vo[1]), (vo[0] + 192, vo[1])); s.flag((vo[0] + 192, vo[1]), "VOUT")
    s.wire((vo[0] + 64, vo[1]), (vo[0] + 64, OY + 160), (vn[0] - 64, OY + 160), (vn[0] - 64, vn[1]), vn)
    if load:
        r = s.add("R_ndiff", "RLOAD", vo[0] + 176, vo[1] - 16, "R0", load, "tc1=1.56e-3 tc2=6.10e-7")
        s.wire(r.p("B"), (vo[0] + 192, vo[1] + 128)); s.gnd((vo[0] + 192, vo[1] + 128))
    # logic stimuli: one source per clk / clk_bar, all on the common ground
    for k, name in enumerate(CLK):
        px, py = pin("DAC_Core", name, DX, DY)
        ly = py + (64 if k % 2 == 0 else 128)
        s.add("voltage", f"V_{name}", px, py + 192, "R0", (clocks or {}).get(name, "0"),
              windows=["WINDOW 0 -8 40 Right 1", "WINDOW 3 -8 136 Right 0"])
        s.wire((px, py), (px, ly), (px, py + 208))
        s.flag((px, ly), name)
        s.wire((px, py + 288), (px, py + 320)); s.gnd((px, py + 320))
    y = 1040
    s.text(64, y, title or "Complete 6-bit segmented current-steering DAC: one Vunregulated (5 V) source and one ground. "
           "The regulator output VREF is the VDD of the DAC core and the op-amp; VBN/VCN are shared bias lines; "
           "DAC IOUT drives the unity-gain op-amp buffer (VOUT).", 2)
    for k, d in enumerate([".include EE4323_cmos.mos", ".include EE4323_bjt.lib"] + list(directives)):
        s.text(64, y + 64 + 40 * k, d, 2, directive=True)
    s.write(path)
    return s
