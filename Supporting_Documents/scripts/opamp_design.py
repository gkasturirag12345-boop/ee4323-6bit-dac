"""Ground-compatible buffered folded-cascode op-amp of 6-bit DAC.pdf page 4: intended netlist (names as drawn).

Input pair M32 (+, drain to the right fold node F2 = M40 source / M41 drain) and M33 (-, drain to the left fold
F1 = M35 source / M34 drain); tail M30/M31 (VBP1/VCP1); folding sinks M34/M41 (VBN) and cascodes M35/M40 (VCN);
PMOS cascode mirror M37/M38 (gates = M36 drain LFT) with cascodes M36/M39 (VCP1); second stage M42 with PMOS
cascode load M44/M43; Ahuja capacitor CA from the M42 drain (G45) to F2; NMOS source follower M45 (L = 0.6 um)
with ROUT; bias M49/M48 + RB (dV) + M47 (VCN) / M46 (VBN) generating VBP1 / VCP1.
PMOS bodies -> VDD, NMOS bodies -> GND (handout rule for blocks other than VREF).
"""

DEF = dict(
    WNU=5e-6, W49=26e-6, W48=26e-6, RB=60e3, M46=2,
    W30=105e-6, W31=105e-6, W32=120e-6,
    M34=18, M35=8,                  # folding sinks ~2x tail current (Ahuja large-signal stability)
    W37=53e-6, W36=53e-6,
    W42=60e-6, W44=262e-6, W43=262e-6,
    W45=2000e-6, L45=0.6e-6, ROUT=2e3, CA=2e-12,
)


def um(v):
    return f"{v * 1e6:g}u"


def netlist(p=None, vinp="VINP", vinn="VINN", vout="VOUT", vdd="VDD"):
    q = dict(DEF, **(p or {}))
    P = lambda n, d, g, s, w, l="3u": f"{n} {d} {g} {s} {vdd} PHL l={l} w={um(w)}"
    N = lambda n, d, g, s, m: f"{n} {d} {g} {s} 0 NWS l=3u w={um(q['WNU'])}" + (f" m={m}" if m > 1 else "")
    rt = "tc1=1.56e-3 tc2=6.10e-7"
    return "\n".join([
        P("M49", "N49", "VBP1", vdd, q["W49"]), P("M48", "VBP1", "VCP1", "N49", q["W48"]),
        f"RB VBP1 VCP1 {q['RB']:g} {rt}",
        N("M47", "VCP1", "VCN", "N47", q["M46"]), N("M46", "N47", "VBN", "0", q["M46"]),
        P("M30", "N30", "VBP1", vdd, q["W30"]), P("M31", "TAIL", "VCP1", "N30", q["W31"]),
        P("M32", "F2", vinp, "TAIL", q["W32"]), P("M33", "F1", vinn, "TAIL", q["W32"]),
        N("M34", "F1", "VBN", "0", q["M34"]), N("M41", "F2", "VBN", "0", q["M34"]),
        N("M35", "LFT", "VCN", "F1", q["M35"]), N("M40", "O1", "VCN", "F2", q["M35"]),
        P("M37", "N37", "LFT", vdd, q["W37"]), P("M36", "LFT", "VCP1", "N37", q["W36"]),
        P("M38", "N38", "LFT", vdd, q["W37"]), P("M39", "O1", "VCP1", "N38", q["W36"]),
        f"M42 G45 O1 0 0 NWS l=3u w={um(q['W42'])}",
        P("M44", "N44", "VBP1", vdd, q["W44"]), P("M43", "G45", "VCP1", "N44", q["W43"]),
        f"CA G45 F2 {q['CA']:g}",
        f"M45 {vdd} G45 {vout} 0 NWS l={um(q['L45'])} w={um(q['W45'])}",
        f"ROUT {vout} 0 {q['ROUT']:g} {rt}",
    ]) + "\n"
