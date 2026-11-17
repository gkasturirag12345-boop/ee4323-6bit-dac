"""Voltage regulator of 6-bit DAC.pdf page 3: intended netlist (device names and connections as drawn).

Constant-gm cross-coupled quad M2/M3/M6/M7 + R1 fed by M1 (I_CONST,Gm), M4/M5 -> VCP, M9/M8 -> VBP,
current-mode bandgap core Ma (npn A=8, diode, R3) / Mb (npn A=1) with Mc + Cc1 feedback, mirrors M10-M13,
bias legs M14-M20 (VCN, VBN), M21/M22 + R5 (VX), LDO M23/M25 (PMOS pair, tail M26/M27),
M24a/b-M28a/b NMOS cascode mirror load, pass device M29, R7/R6 feedback, Cc2 + Rnull.
PMOS bodies -> VUN (Vunregulated, most positive); NMOS bodies -> GND.
"""

DEF = dict(
    L1=120e-6, W1=2e-6,                     # M1: W = 2 um; L = 120 um = ~2x margin to the start-up failure boundary (~260 um) at 4.5 V, 0-80 C
    W2=5e-6, W3=5e-6, W7=5e-6, M6=4, W4=5e-6, M4=2, R1=8.5e3,
    W5=8e-6, WPU=8e-6, MP=2, MTAIL=4,      # PMOS unit 8u/3u; I_CONST legs m=2, tail m=4 (top devices on VBP run in triode, cascodes on VCP set the current)
    WC=20e-6, CC1=4e-12,                    # Cc1: core-loop phase margin >= 70 deg over 0-80 C
    R2=112e3, R3=6.45e3, R4=64e3, AREA=8,   # R2/R4 tuned for the DAC output TC (codes 011111, 111111); R3 for IPTAT = 10 uA
    WNU=5e-6, W14=3e-6, M17=4, M18=4,       # NMOS unit 5u/3u; M14 narrower -> VCN = Vt + ~2 Vov
    R5=127.6e3, WPAIR=20e-6, MLD=4,
    W29=600e-6, L29=0.6e-6, CC2=5e-12, RNULL=2e3, R7=0.86e3, R6=3.0e3,
)


def um(v):
    return f"{v * 1e6:g}u"


def netlist(p=None):
    q = dict(DEF, **(p or {}))
    P = lambda w, m=1, l="3u": f"PHL l={l} w={um(w)}" + (f" m={m}" if m > 1 else "")
    N = lambda w, m=1, l="3u": f"NWS l={l} w={um(w)}" + (f" m={m}" if m > 1 else "")
    pu = q["WPU"]
    rt = "tc1=1.56e-3 tc2=6.10e-7"
    return f"""* start-up / constant-gm current I_CONST,Gm
M1 N1 0 VUN VUN PHL l={um(q['L1'])} w={um(q['W1'])}
M2 N1 N1 N2 0 {N(q['W2'])}
M3 N2 N3 0 0 {N(q['W3'])}
M7 VBP N1 N3 0 {N(q['W7'])}
M6 N3 N2 R1T 0 {N(q['W7'], q['M6'])}
R1 R1T 0 {q['R1']:g} {rt}
M4 VCP N2 0 0 {N(q['W4'], q['M4'])}
M5 VCP VCP VUN VUN {P(q['W5'])}
M9 S9 VBP VUN VUN {P(pu, q['MP'])}
M8 VBP VCP S9 VUN {P(pu, q['MP'])}
* bandgap core
Mc VBP G 0 0 {N(q['WC'])}
Cc1 VBP G {q['CC1']:g}
M11 S11 VBP VUN VUN {P(pu, q['MP'])}
M10 G VCP S11 VUN {P(pu, q['MP'])}
M13 S13 VBP VUN VUN {P(pu, q['MP'])}
M12 A VCP S13 VUN {P(pu, q['MP'])}
QMb G A 0 npn_EE4323 1
QMa A A E3 npn_EE4323 {q['AREA']}
R3 E3 0 {q['R3']:g} {rt}
R2 G 0 {q['R2']:g} {rt}
R4 A 0 {q['R4']:g} {rt}
* bias legs
M16 S16 VBP VUN VUN {P(pu, q['MP'])}
M15 VCN VCP S16 VUN {P(pu, q['MP'])}
M14 VCN VCN 0 0 {N(q['W14'])}
M20 S20 VBP VUN VUN {P(pu, q['MP'])}
M19 VBN VCP S20 VUN {P(pu, q['MP'])}
M18 VBN VCN S18 0 {N(q['WNU'], q['M18'])}
M17 S18 VBN 0 0 {N(q['WNU'], q['M17'])}
M22 S22 VBP VUN VUN {P(pu, q['MP'])}
M21 VX VCP S22 VUN {P(pu, q['MP'])}
R5 VX 0 {q['R5']:g} {rt}
* LDO error amplifier and pass device
M26 S26 VBP VUN VUN {P(pu, q['MTAIL'])}
M27 TL VCP S26 VUN {P(pu, q['MTAIL'])}
M23 GP VX TL VUN {P(q['WPAIR'])}
M25 D25 FB TL VUN {P(q['WPAIR'])}
M24b GP VCN S24 0 {N(q['WNU'], q['MLD'])}
M24a S24 D25 0 0 {N(q['WNU'], q['MLD'])}
M28b D25 VCN S28 0 {N(q['WNU'], q['MLD'])}
M28a S28 D25 0 0 {N(q['WNU'], q['MLD'])}
M29 VREF GP VUN VUN PHL l={um(q['L29'])} w={um(q['W29'])}
Cc2 VREF RN {q['CC2']:g}
Rnull RN GP {q['RNULL']:g} {rt}
R7 VREF FB {q['R7']:g} {rt}
R6 FB 0 {q['R6']:g} {rt}
"""
