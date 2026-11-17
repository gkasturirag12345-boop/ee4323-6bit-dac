"""Parameter extraction and figures for the characterisation runs (reads Simulation_Results/Characterisation/*.csv).

NMOS saturation: ID = (Kn'/2)(W/L)(VGS - Vtn)^2  ->  sqrt(ID) = sqrt(Kn' W / 2L) * (VGS - Vtn)
Best-fit line sqrt(ID) = a*VGS + b in the saturation region: slope a = sqrt(Kn' W / 2L), Vtn = -b/a.
Body effect: Vtn(VSB) = Vtn0 + gamma (sqrt(2phiF + VSB) - sqrt(2phiF)).
"""
import json, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sim

D = sim.ROOT / "Simulation_Results" / "Characterisation"
WL = 2e-6 / 2e-6
FIT = (1.2, 2.0)             # VGS fit window (V): strong inversion, before mobility degradation bends the line
SER = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]   # categorical slots 1-6, fixed order
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
K_B, Q = 1.380649e-23, 1.602176634e-19


def style(ax, xl, yl, title):
    ax.set_xlabel(xl, color=INK2); ax.set_ylabel(yl, color=INK2); ax.set_title(title, color=INK, fontsize=11, loc="left")
    ax.grid(True, color=GRID, lw=0.8); ax.tick_params(colors=INK2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def fit_sqrt(vgs, idd, win=FIT):
    m = (vgs >= win[0] - 1e-9) & (vgs <= win[1] + 1e-9)
    y = np.sqrt(np.clip(idd[m], 0, None))
    a, b = np.polyfit(vgs[m], y, 1)
    r2 = 1 - np.sum((y - (a * vgs[m] + b)) ** 2) / np.sum((y - y.mean()) ** 2)
    return a, b, -b / a, r2


def main():
    out = {}
    # ---------- A: output characteristic
    a = pd.read_csv(D / "A_output.csv")
    fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=160)
    bc = pd.read_csv(D / "BC_transfer_body.csv")
    s0 = bc[bc.step == 0]
    sl, ic, vt0, r2 = fit_sqrt(s0.VGS2.values, s0["Id(M2)"].values)
    for st in range(6):
        s = a[a.step == st]; vgs = s["V(vg1)"].iloc[0]
        ax.plot(s.VDS1, s["Id(M1)"] * 1e6, color=SER[st], lw=2)
        if vgs >= 2:
            ax.text(5.05, s["Id(M1)"].iloc[-1] * 1e6, f"VGS = {vgs:.0f} V", color=INK2, fontsize=8, va="center")
        elif vgs == 1:
            ax.text(5.05, 14, f"VGS = 0, 1 V\n(ID = {s['Id(M1)'].iloc[-1] * 1e6:.1f} µA at 1 V)", color=INK2, fontsize=8, va="center")
    vov = np.linspace(0, 5, 51)
    ax.plot(vov, (sl ** 2) * vov ** 2 * 1e6, color=INK2, lw=1, ls="--")
    ax.text(3.35, 345, "VDS = VGS − Vtn0\n← triode | saturation →", color=INK2, fontsize=8, ha="left")
    ax.set_xlim(0, 6.2); ax.set_ylim(0, a["Id(M1)"].max() * 1.1e6)
    style(ax, "VDS (V)", "ID (µA)", "NMOS output characteristic, nmos_NWS W/L = 2 µm / 2 µm")
    fig.tight_layout(); fig.savefig(D / "fig_A_ID_VDS.png"); plt.close(fig)
    out["A"] = {f"ID_uA_at_VDS5_VGS{int(a[a.step == st]['V(vg1)'].iloc[0])}": float(a[a.step == st]["Id(M1)"].iloc[-1] * 1e6) for st in range(6)}

    # ---------- B/C: transfer + body effect
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.0), dpi=160)
    bres = []
    for st in range(3):
        s = bc[bc.step == st]; vsb = -s["V(vb2)"].iloc[0]
        a_, b_, vt, r2_ = fit_sqrt(s.VGS2.values, s["Id(M2)"].values)
        kn_p = 2 * a_ ** 2 / WL
        bres.append(dict(VSB=round(abs(vsb), 3), slope_sqrtA_per_V=a_, intercept_sqrtA=b_, Vtn=vt, Kn_prime_uA_per_V2=kn_p * 1e6,
                         Kn_uA_per_V2=kn_p * WL * 1e6, r2=r2_))
        ax1.plot(s.VGS2, s["Id(M2)"] * 1e6, color=SER[st], lw=2, label=f"VSB = {abs(vsb):.1f} V")
        ax2.plot(s.VGS2, np.sqrt(np.clip(s["Id(M2)"], 0, None)) * 1e3, color=SER[st], lw=2, label=f"VSB = {abs(vsb):.1f} V")
        xx = np.linspace(vt, 3, 20)
        ax2.plot(xx, (a_ * xx + b_) * 1e3, color=SER[st], lw=1, ls="--")
    ax2.axvspan(*FIT, color=GRID, alpha=0.6, lw=0)
    ax2.text(FIT[0] + 0.02, 11.2, "fit window", color=INK2, fontsize=8)
    style(ax1, "VGS (V)", "ID (µA)", "ID vs VGS, VDS = 3 V")
    style(ax2, "VGS (V)", "√ID (√mA)", "√ID vs VGS with best-fit lines (dashed)")
    for x in (ax1, ax2):
        x.legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(D / "fig_BC_transfer_body.png"); plt.close(fig)
    # gamma: 2phiF from the model doping NCH = 1.7e17 cm^-3 (EE4323_cmos.mos), ni = 1.45e10 cm^-3 at 300 K
    phi2 = 2 * (K_B * 300.15 / Q) * np.log(1.7e17 / 1.45e10)
    g = [(r["Vtn"] - bres[0]["Vtn"]) / (np.sqrt(phi2 + r["VSB"]) - np.sqrt(phi2)) for r in bres[1:]]
    out["B"] = bres[0]
    out["C"] = dict(rows=bres, two_phiF_V=phi2, gamma_sqrtV=g, dVt_mV=[(r["Vtn"] - bres[0]["Vtn"]) * 1e3 for r in bres])
    # sensitivity of the fit window (reported, not used)
    out["B_fit_window_sensitivity"] = {f"{w[0]}-{w[1]}V": dict(zip(("slope", "intercept", "Vtn", "r2"), fit_sqrt(s0.VGS2.values, s0["Id(M2)"].values, w)))
                                       for w in ((1.0, 1.6), (1.2, 2.0), (1.4, 3.0))}

    # ---------- D: NPN
    dT = pd.read_csv(D / "D_npn_dc_temp.csv"); sT = pd.read_csv(D / "D_npn_step_temp.csv")
    T = dT.temperature.values; v1, v8 = dT["V(vbe1)"].values, dT["V(vbe8)"].values; dv = v1 - v8
    s1, c1 = np.polyfit(T, v1, 1); s8, c8 = np.polyfit(T, v8, 1); sd, cd = np.polyfit(T, dv, 1)
    i27 = int(np.argmin(abs(T - 27)))
    chk = max(float(np.max(abs(np.interp(sT.temperature, T, v1) - sT["V(vbe1)"]))),
              float(np.max(abs(np.interp(sT.temperature, T, v8) - sT["V(vbe8)"]))))
    out["D"] = dict(VBE1_27C=v1[i27], VBE8_27C=v8[i27], dVBE_27C_mV=dv[i27] * 1e3,
                    dVBE_theory_27C_mV=K_B * 300.15 / Q * np.log(8) * 1e3,
                    TC_VBE1_mV_per_C=s1 * 1e3, TC_VBE8_mV_per_C=s8 * 1e3, TC_dVBE_mV_per_C=sd * 1e3,
                    TC_dVBE_theory_mV_per_C=K_B / Q * np.log(8) * 1e3,
                    Ic_Q1_uA_27C=float(dT["Ic(Q1)"].values[i27] * 1e6),
                    dc_temp_vs_step_temp_max_diff_V=chk)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.8), dpi=160)
    ax1.plot(T, v1 * 1e3, color=SER[0], lw=2, label="VBE, area 1")
    ax1.plot(T, v8 * 1e3, color=SER[1], lw=2, label="VBE, area 8")
    ax1.plot(sT.temperature, sT["V(vbe1)"] * 1e3, "o", ms=6, mfc="none", color=SER[0], label=".step temp check")
    ax1.plot(sT.temperature, sT["V(vbe8)"] * 1e3, "o", ms=6, mfc="none", color=SER[1])
    ax2.plot(T, dv * 1e3, color=SER[2], lw=2, label="ΔVBE = VBE1 − VBE8 (simulated)")
    ax2.plot(T, K_B * (T + 273.15) / Q * np.log(8) * 1e3, color=INK2, lw=1, ls="--", label="(kT/q)·ln 8")
    style(ax1, "Temperature (°C)", "VBE (mV)", f"VBE vs T (CTAT): {s1 * 1e3:.2f} mV/°C (area 1)")
    style(ax2, "Temperature (°C)", "ΔVBE (mV)", f"ΔVBE vs T (PTAT): +{sd * 1e3:.3f} mV/°C")
    for x in (ax1, ax2):
        x.legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(D / "fig_D_npn_temp.png"); plt.close(fig)

    # ---------- E: PMOS (for M1 / VREF calculations only)
    e = pd.read_csv(D / "E_pmos_transfer.csv")
    vsg = -e.VGP.values; idp = np.abs(e["Id(M3)"].values)
    ap, bp, vtp, r2p = fit_sqrt(vsg, idp)
    out["E"] = dict(slope=ap, Vtp_abs=vtp, Kp_prime_uA_per_V2=2 * ap ** 2 / WL * 1e6, r2=r2p)
    (D / "extracted_parameters.json").write_text(json.dumps(out, indent=1, default=float))
    return out


if __name__ == "__main__":
    print(json.dumps(main(), indent=1, default=float))
