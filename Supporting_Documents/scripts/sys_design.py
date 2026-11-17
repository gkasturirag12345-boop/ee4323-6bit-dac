"""Complete 6-bit DAC system (04): regulator (02) + DAC core (page 2) + op-amp (03) + ideal VCVS reference buffer.

One Vunregulated source and one ground. The regulator output (VREF) is the VDD net of the DAC core and the op-amp
(handout page 1: "VREG as VDD"); VBN / VCN are shared. DAC IOUT drives R (RDAC) and the op-amp (+) input M32;
VOUT feeds back to M33 (-). The ideal VCVS E_IDEAL (gain 1e6) buffers the same IOUT node into its own output
VOUT_IDEAL; its input draws no current, so it does not load IOUT or disturb the real op-amp.
"""
import re
import reg_design, dac_design, opamp_design

BITS = dac_design.BITS


def code_schedule(codes, t0, T):
    return [(c, t0 + k * T) for k, c in enumerate(codes)]


def pwl_sources(codes, t0, T, vhi, tr=1e-9):
    """Logic stimuli clk_<bit> and clk_bar_<bit> (exact complements) for a code sequence; edges of length tr."""
    out = []
    for b in BITS:
        lv = [dac_design.code_bits(c)[b] for c in codes]
        for name, inv in ((f"clk_{b}", False), (f"clk_bar_{b}", True)):
            pts = [(0.0, (1 - lv[0] if inv else lv[0]) * vhi)]
            for k in range(1, len(codes)):
                a, bb = lv[k - 1], lv[k]
                if a != bb:
                    t = t0 + k * T
                    va, vb = ((1 - a) if inv else a) * vhi, ((1 - bb) if inv else bb) * vhi
                    pts += [(t, va), (t + tr, vb)]
            out.append(f"V_{name} {name} 0 PWL(" + " ".join(f"{t:.9g} {v:.4g}" for t, v in pts) + ")")
    return "\n".join(out)


def netlist(rp=None, dp=None, op=None, vun="5", loads="", stim="", ideal=True):
    reg = re.sub(r"\bVREF\b", "VDD", reg_design.netlist(rp))
    t = "* ---- voltage regulator (02)\n" + reg
    t += "* ---- DAC core (page 2)\n" + dac_design.netlist(dp, vdd="VDD", iout="IOUT")
    t += "* ---- op-amp (03): M32 (+) = IOUT, M33 (-) = VOUT\n" + opamp_design.netlist(op, vinp="IOUT", vinn="VOUT", vout="VOUT", vdd="VDD")
    if ideal:
        t += "E_IDEAL VOUT_IDEAL 0 IOUT VOUT_IDEAL 1e6\n"
    t += f"VUNREG VUN 0 {vun}\n" + loads + "\n" + stim + "\n"
    return t
