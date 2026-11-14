"""6-bit segmented current-steering DAC core netlist generator (3 unary MSB cells + 4 binary LSB cells)."""

DEF = dict(
    WU=5e-6,            # unit PMOS current source / cascode width (I_LSB = 2 uA)
    WNU=5e-6, RB2=28e3,   # VBP2/VCP2 bias branch: NMOS sink from VBN/VCN (16 uA)
    WSU=20e-6, WSB=(10e-6, 5e-6, 5e-6, 5e-6),  # switch widths: unary, binary B3..B6
    RDAC=5.445e3,
)

# (bit name, units, transistor names: source, cascode, switch-to-output, switch-to-dump)
CELLS = [
    ("D1", 16, ("M83", "M84", "M85", "M86")),
    ("D2", 16, ("M87", "M88", "M89", "M90")),
    ("D3", 16, ("M91", "M92", "M93", "M94")),
    ("B3", 8, ("M64", "M65", "M66", "M67")),
    ("B4", 4, ("M68", "M69", "M70", "M71")),
    ("B5", 2, ("M72", "M73", "M74", "M75")),
    ("B6", 1, ("M76", "M77", "M78", "M79")),
]


def netlist(p=None, vdd="VDD", out="IOUT", extra=""):
    q = dict(DEF)
    q.update(p or {})
    L = "3u"
    pm = lambda n, d, g, s, w, m=1: f"{n} {d} {g} {s} {vdd} PHL l={L} w={w:g}" + (f" m={m}" if m > 1 else "")
    nm = lambda n, d, g, s, w, m=1: f"{n} {d} {g} {s} 0 NWS l={L} w={w:g}" + (f" m={m}" if m > 1 else "")
    lines = [
        "* DAC core",
        # bias: VDD - M53 (VBP2) - M52 (VCP2) - RB2 - M51 (VCN) - M50 (VBN) - GND, 8 units (16 uA)
        pm("M53", "n53", "VBP2", vdd, q["WU"], 8), pm("M52", "VBP2", "VCP2", "n53", q["WU"], 8),
        f"RB2 VBP2 VCP2 {q['RB2']:g} tc1=1.56e-3 tc2=6.10e-7",
        nm("M51", "VCP2", "VCN", "n51", q["WNU"], 4), nm("M50", "n51", "VBN", "0", q["WNU"], 4),
    ]
    wsb = dict(zip(["B3", "B4", "B5", "B6"], q["WSB"]))
    for bit, m, (ms, mc, mo, md) in CELLS:
        ws = q["WSU"] if bit.startswith("D") else wsb[bit]
        s, c = f"s_{bit}", f"c_{bit}"
        lines += [
            pm(ms, s, "VBP2", vdd, q["WU"], m),
            pm(mc, c, "VCP2", s, q["WU"], m),
            pm(mo, out, f"clk_bar_{bit}", c, ws),   # on when clk_bar low, i.e. bit = 1
            pm(md, "0", f"clk_{bit}", c, ws),       # dump to analog ground when bit = 0
        ]
    lines += [f"RDAC {out} 0 {q['RDAC']:g} tc1=1.56e-3 tc2=6.10e-7", extra]
    return "\n".join(lines) + "\n"


def code_sources(vdd="VDD", amp="3", code="code"):
    """Static logic sources for a given .param code (thermometer MSBs, binary LSBs) and complements."""
    bits = {
        "D1": f"({code}>=16)", "D2": f"({code}>=32)", "D3": f"({code}>=48)",
        "B3": f"(floor({code}/8)-2*floor({code}/16))", "B4": f"(floor({code}/4)-2*floor({code}/8))",
        "B5": f"(floor({code}/2)-2*floor({code}/4))", "B6": f"({code}-2*floor({code}/2))",
    }
    out = []
    for b, e in bits.items():
        out.append(f"V_{b} clk_{b} 0 {{{amp}*{e}}}")
        out.append(f"V_bar_{b} clk_bar_{b} 0 {{{amp}*(1-{e})}}")
    return "\n".join(out)
