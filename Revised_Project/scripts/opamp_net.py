"""Folded-cascode op-amp (handout page 4) netlist generator. Supplies: VDD, GND; biases VBN, VCN in."""

DEF = dict(
    WNU=5e-6, W49=26e-6, W48=26e-6, RB=60e3,   # VBP1/VCP1 bias branch (10 uA)
    W30=105e-6, W31=105e-6,          # tail current source (40 uA)
    W32=120e-6,                      # PMOS input pair
                # NMOS folding sinks (VBN) and cascodes (VCN)
    W37=53e-6, W36=53e-6,            # PMOS cascode mirror load
    W42=60e-6, W44=262e-6, W43=262e-6,  # second stage
    W45=2000e-6, L45=0.6e-6, ROUT=2e3, CA=2e-12,
)


def netlist(p=None, vinp="VINP", vinn="VINN", vout="VOUT", vdd="VDD", extra=""):
    q = dict(DEF)
    q.update(p or {})
    L = "3u"
    pm = lambda n, d, g, s, w, l=L: f"{n} {d} {g} {s} {vdd} PHL l={l} w={w:g}"
    nm = lambda n, d, g, s, w, l=L, m=1: f"{n} {d} {g} {s} 0 NWS l={l} w={w:g}" + (f" m={m}" if m > 1 else "")
    lines = [
        "* Folded-cascode op-amp with source-follower output",
        # bias: VDD - M49 - M48 - RB - M47 - M46 - GND
        pm("M49", "n49", "VBP1", vdd, q["W49"]), pm("M48", "VBP1", "VCP1", "n49", q["W48"]),
        f"RB VBP1 VCP1 {q['RB']:g} tc1=1.56e-3 tc2=6.10e-7",
        nm("M47", "VCP1", "VCN", "n47", q["WNU"], m=2), nm("M46", "n47", "VBN", "0", q["WNU"], m=2),
        # tail and input pair (M32 = inverting, M33 = non-inverting)
        pm("M30", "n30", "VBP1", vdd, q["W30"]), pm("M31", "TAIL", "VCP1", "n30", q["W31"]),
        pm("M32", "F1", vinn, "TAIL", q["W32"]), pm("M33", "F2", vinp, "TAIL", q["W32"]),
        # folded cascode
        nm("M34", "F1", "VBN", "0", q["WNU"], m=9), nm("M41", "F2", "VBN", "0", q["WNU"], m=9),
        nm("M35", "LFT", "VCN", "F1", q["WNU"], m=4), nm("M40", "O1", "VCN", "F2", q["WNU"], m=4),
        pm("M37", "n37", "LFT", vdd, q["W37"]), pm("M36", "LFT", "VCP1", "n37", q["W36"]),
        pm("M38", "n38", "LFT", vdd, q["W37"]), pm("M39", "O1", "VCP1", "n38", q["W36"]),
        # second stage and output follower
        nm("M42", "G45", "O1", "0", q["W42"]),
        pm("M44", "n44", "VBP1", vdd, q["W44"]), pm("M43", "G45", "VCP1", "n44", q["W43"]),
        f"CA G45 F2 {q['CA']:g}",
        f"M45 {vdd} G45 {vout} 0 NWS l={q['L45']:g} w={q['W45']:g}",
        f"ROUT {vout} 0 {q['ROUT']:g} tc1=1.56e-3 tc2=6.10e-7",
        extra,
    ]
    return "\n".join(lines) + "\n"
