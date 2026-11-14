"""Voltage regulator (current-mode bandgap + LDO) netlist generator."""

DEF = dict(
    # PTAT/CTAT core
    R3=5.38e3, R2=42.7e3, R4=42.7e3, AREA=8,
    WP=66e-6,      # PTAT-core PMOS mirrors (M10-M13), and all ICONST copies
    WPC=16e-6,     # PMOS wide-swing cascode bias diode (M8)
    WA=20e-6, WNL=10e-6, WT=33e-6,  # core error amp: PMOS pair Ma/Mb, NMOS load, tail
    WC=10e-6, CC1=2e-12,
    WNU=5e-6,          # NMOS VBN diode (M14) / VCN diode (M17)
    W1=1e-6, L1=200e-6, W2=50e-6, W3=1e-6, L3=3e-6, W5=10e-6,  # start-up
    # LDO
    R5=72.8e3, R7=100e3, R6=200e3,
    WEP=66e-6, WEL=20e-6, WT2=60e-6,
    W29=2000e-6, L29=0.6e-6, CC2=5e-12, RNULL=2e3, CL=100e-9,
)


def netlist(p=None, extra=""):
    q = dict(DEF)
    q.update(p or {})
    L = "3u"
    pm = lambda n, d, g, s, w, l=L, b="VUN": f"{n} {d} {g} {s} {b} PHL l={l} w={w:g}"
    nm = lambda n, d, g, s, w, l=L, m=1: f"{n} {d} {g} {s} 0 NWS l={l} w={w:g}" + (f" m={m}" if m > 1 else "")
    R = lambda n, a, b, v: f"{n} {a} {b} {v:g} tc1=1.56e-3 tc2=6.10e-7"
    lines = [
        "* Voltage regulator: current-mode bandgap + LDO",
        # --- start-up
        pm("M1", "SU", "0", "VUN", q["W1"], l=f"{q['L1']:g}"),
        nm("M2", "SU", "A", "0", q["W2"]),
        f"M3 VUN SU A 0 NWS l={q['L3']:g} w={q['W3']:g}",
        nm("M5", "PG", "SU", "0", q["W5"]),
        nm("M4", "VCPI", "SU", "0", q["W3"]),
        # --- PTAT/CTAT core (equal branch currents)
        pm("M11", "n11", "PG", "VUN", q["WP"]), pm("M10", "A", "VCPI", "n11", q["WP"]),
        pm("M13", "n13", "PG", "VUN", q["WP"]), pm("M12", "B", "VCPI", "n13", q["WP"]),
        "Qb A A 0 npn_EE4323 1",
        R("R2", "A", "0", q["R2"]),
        R("R3", "B", "QA", q["R3"]),
        f"Qa QA QA 0 npn_EE4323 {q['AREA']}",
        R("R4", "B", "0", q["R4"]),
        # --- core error amp: PMOS pair (Ma: A, Mb: B), NMOS mirror load, gain stage Mc + diode M9
        pm("Mt", "TL", "PG", "VUN", q["WT"]),
        pm("Ma", "DL", "A", "TL", q["WA"]), pm("Mb", "AO", "B", "TL", q["WA"]),
        nm("Mn1", "DL", "DL", "0", q["WNL"]), nm("Mn2", "AO", "DL", "0", q["WNL"]),
        f"Cc1 AO 0 {q['CC1']:g}",
        nm("Mc", "PG", "AO", "0", q["WC"]),
        pm("M9", "PG", "PG", "VUN", q["WP"]),
        # --- bias generation: VBN, VCN (exported) and VCPI (internal PMOS cascode bias)
        pm("M16", "n16", "PG", "VUN", q["WP"]), pm("M15", "VBN", "VCPI", "n16", q["WP"]),
        nm("M14b", "VBN", "VCN", "n14", q["WNU"], m=6), nm("M14", "n14", "VBN", "0", q["WNU"], m=6),
        pm("M20", "n20", "PG", "VUN", q["WP"]), pm("M19", "VCN", "VCPI", "n20", q["WP"]),
        nm("M17", "VCN", "VCN", "0", q["WNU"]),
        pm("M8", "VCPI", "VCPI", "VUN", q["WPC"]),
        nm("M18", "n18", "VBN", "0", q["WNU"], m=6), nm("M7", "VCPI", "VCN", "n18", q["WNU"], m=6),
        # --- reference voltage VX = ICONST * R5
        pm("M22", "n22", "PG", "VUN", q["WP"]), pm("M21", "VX", "VCPI", "n22", q["WP"]),
        R("R5", "VX", "0", q["R5"]),
        # --- LDO error amp: NMOS pair, PMOS cascode mirror load, NMOS cascode tail (2*ICONST)
        nm("M27", "n27", "VBN", "0", q["WNU"], m=12), nm("M26", "TL2", "VCN", "n27", q["WNU"], m=12),
        nm("M25", "D25", "FB", "TL2", q["WEL"]), nm("M23", "EOUT", "VX", "TL2", q["WEL"]),
        pm("M24a", "n24", "D25", "VUN", q["WEP"]), pm("M24b", "D25", "VCPI", "n24", q["WEP"]),
        pm("M28a", "n28", "D25", "VUN", q["WEP"]), pm("M28b", "EOUT", "VCPI", "n28", q["WEP"]),
        # --- pass device and feedback divider
        f"M29 VREF EOUT VUN VUN PHL l={q['L29']:g} w={q['W29']:g}",
        R("R7", "VREF", "FB", q["R7"]), R("R6", "FB", "0", q["R6"]),
        f"Cc2 EOUT nz {q['CC2']:g}", f"Rnull nz VREF {q['RNULL']:g} tc1=1.56e-3 tc2=6.10e-7",
        f"CL VREF 0 {q['CL']:g}",
        extra,
    ]
    return "\n".join(lines) + "\n"
