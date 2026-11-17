"""Segmented current-steering DAC core of 6-bit DAC.pdf page 2: intended netlist (device names and connections as drawn).

Bias: M53 (VBP2) / M52 (VCP2) PMOS + dV resistor RB2 + M51 (VCN) / M50 (VBN) -> VBP2 (top of RB2), VCP2 (bottom).
Binary (LSB) section: PMOS source M82 (VBP2) / M81 (VCP2) feeds node S4 of the W-2W ladder:
  series devices (2W) M76: S4->S3, M71: S3->S2, M66: S2->S1 (gates G1);
  shunt branches (W) M77/M78 (S4, B3), M72/M73 (S3, B4), M67/M68 (S2, B5), M62/M63 (S1, B6), gates G1 / cascodes G2;
  terminator M61 (diode, G1) over M60 (diode, G2) sunk by the NMOS cascode M59 (gate NC2) and the chain M58a..p
  (16 series NMOS, gates NB2). NC2/NB2 come from M54 (VBP2)/M55 (VCP2) + dV resistor RB3 + M56 / M57.
  Switch pairs (PMOS): Bk -> M(odd) to GND, Bk_bar -> M(even) to IOUT: M64/M65 (B6), M69/M70 (B5), M74/M75 (B4), M79/M80 (B3).
Unary (MSB) section: M83/M84 -> M85 (D3) / M86 (D3_bar); M87/M88 -> M89 (D2) / M90 (D2_bar); M91/M92 -> M93 (D1) / M94 (D1_bar).
IOUT -> R (to GND) -> op-amp (+).  PMOS bodies -> VDD, NMOS bodies -> GND.
"""

DEF = dict(
    WPS=20e-6, MSRC=3, MBIAS=2,           # PMOS current-source unit (L=3u): M82/M81, M83/84, M87/88, M91/92, M54/55 = 3 units, M53/52 = 2
    RB2=40e3,                             # dV resistor of the VBP2/VCP2 bias
    WNB=5e-6, M50=4,                      # M50/M51: NMOS unit at the VBN density (I = 4 units = I_CONST)
    WL=1500e-6,                           # W-2W ladder: shunt + terminator M61 = W, series = 2W (weak inversion -> body-effect-insensitive division)
    WCAS=40e-6,                           # terminator diode M60 = WCAS; shunt cascodes M63/M68/M73/M78 = 1/2/4/8 x WCAS (equal density)
    WN56=10e-6, RB3=20e3,                 # M56/M57/M59 (W/L = WN56/3u); dV resistor RB3
    W58=30e-6,                            # each of the 16 series M58x devices (W/L = W58/3u)
    WSW=100e-6,                           # current-steering switches
    RDAC=5.989e3,                         # output resistor R (sets the 12.5 mV LSB)
)

BITS = ["D1", "D2", "D3", "B3", "B4", "B5", "B6"]


def um(v):
    return f"{v * 1e6:g}u"


def netlist(p=None, vdd="VDD", iout="IOUT", clk=lambda b: f"clk_{b}", clkb=lambda b: f"clk_bar_{b}"):
    q = dict(DEF, **(p or {}))
    P = lambda n, d, g, s, w, m=1: f"{n} {d} {g} {s} {vdd} PHL l=3u w={um(w)}" + (f" m={m}" if m > 1 else "")
    N = lambda n, d, g, s, w, m=1: f"{n} {d} {g} {s} 0 NWS l=3u w={um(w)}" + (f" m={m}" if m > 1 else "")
    rt = "tc1=1.56e-3 tc2=6.10e-7"
    L = []
    # bias VBP2 / VCP2
    L += [P("M53", "N53", "VBP2", vdd, q["WPS"], q["MBIAS"]), P("M52", "VBP2", "VCP2", "N53", q["WPS"], q["MBIAS"]),
          f"RB2 VBP2 VCP2 {q['RB2']:g} {rt}",
          N("M51", "VCP2", "VCN", "N51", q["WNB"], q["M50"]), N("M50", "N51", "VBN", "0", q["WNB"], q["M50"])]
    # ladder sink bias NC2 / NB2
    L += [P("M54", "N54", "VBP2", vdd, q["WPS"], q["MSRC"]), P("M55", "NC2", "VCP2", "N54", q["WPS"], q["MSRC"]),
          f"RB3 NC2 NB2 {q['RB3']:g} {rt}",
          N("M56", "NB2", "NC2", "N56", q["WN56"]), N("M57", "N56", "NB2", "0", q["WN56"])]
    # ladder input source
    L += [P("M82", "N82", "VBP2", vdd, q["WPS"], q["MSRC"]), P("M81", "S4", "VCP2", "N82", q["WPS"], q["MSRC"])]
    # W-2W ladder (series 2W, shunt / terminator / cascodes W)
    W, W2 = q["WL"], 2 * q["WL"]
    L += [P("M76", "S3", "G1", "S4", W2), P("M71", "S2", "G1", "S3", W2), P("M66", "S1", "G1", "S2", W2),
          P("M61", "G1", "G1", "S1", W), P("M60", "G2", "G2", "G1", q["WCAS"]),
          N("M59", "G2", "NC2", "C58_0", q["WN56"])]
    for k in range(16):
        nm = "M58" + "abcdefghijklmnop"[k]
        d = f"C58_{k}"; s = f"C58_{k + 1}" if k < 15 else "0"
        L.append(N(nm, d, "NB2", s, q["W58"]))
    for top, cas, src, x, b, sg, so, wt in (("M77", "M78", "S4", "X3", "B3", "M79", "M80", 8), ("M72", "M73", "S3", "X4", "B4", "M74", "M75", 4),
                                            ("M67", "M68", "S2", "X5", "B5", "M69", "M70", 2), ("M62", "M63", "S1", "X6", "B6", "M64", "M65", 1)):
        # shunt device W; its cascode is scaled with the branch weight so every shunt drain sits at the terminator level G1
        L += [P(top, f"N{top}", "G1", src, W), P(cas, x, "G2", f"N{top}", q["WCAS"], wt),
              P(sg, "0", clk(b), x, q["WSW"]), P(so, iout, clkb(b), x, q["WSW"])]
    # unary sources (16 units each) and switch pairs
    for t, c, x, dk, sg, so in (("M83", "M84", "XD3", "D3", "M85", "M86"), ("M87", "M88", "XD2", "D2", "M89", "M90"),
                                ("M91", "M92", "XD1", "D1", "M93", "M94")):
        L += [P(t, f"N{t}", "VBP2", vdd, q["WPS"], q["MSRC"]), P(c, x, "VCP2", f"N{t}", q["WPS"], q["MSRC"]),
              P(sg, "0", clk(dk), x, q["WSW"]), P(so, iout, clkb(dk), x, q["WSW"])]
    L.append(f"RDAC {iout} 0 {q['RDAC']:g} {rt}")
    return "\n".join(L) + "\n"


def code_bits(code):
    """Thermometer D1..D3 (D3 for code >= 16, D2 >= 32, D1 >= 48) + binary B3 (8) .. B6 (1)."""
    m = code >> 4
    return dict(D3=int(m >= 1), D2=int(m >= 2), D1=int(m >= 3), B3=(code >> 3) & 1, B4=(code >> 2) & 1, B5=(code >> 1) & 1, B6=code & 1)
