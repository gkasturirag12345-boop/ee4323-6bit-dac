"""Report figures from the saved simulation CSVs (Simulation_Results/*). Nothing here simulates; it only plots data."""
import json, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sim

R = sim.ROOT / "Simulation_Results"
SER = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def style(ax, xl, yl, title):
    ax.set_xlabel(xl, color=INK2); ax.set_ylabel(yl, color=INK2); ax.set_title(title, color=INK, fontsize=10, loc="left")
    ax.grid(True, color=GRID, lw=0.8); ax.tick_params(colors=INK2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def csv(path):
    hdr = open(path).readline().strip().split(",")
    d = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
    return {h: d[:, i] for i, h in enumerate(hdr)}


def save(fig, path):
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


def vref_figs():
    D = R / "VREF"
    t = csv(D / "tc.csv")
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.6))
    a.plot(t["temperature"], t["v(vref)"], color=SER[0], lw=2); style(a, "Temperature (°C)", "VREF (V)", "VREF vs temperature (Vunreg = 5 V, RL = 3 kΩ)")
    b.plot(t["temperature"], t["ic(ma)"] * 1e6, color=SER[1], lw=2, label="IPTAT (Ma, R3)")
    b.plot(t["temperature"], t["i(r4)"] * 1e6, color=SER[2], lw=2, label="ICTAT (R4)")
    b.plot(t["temperature"], t["i(r5)"] * 1e6, color=SER[0], lw=2, label="ICONST (R5)")
    style(b, "Temperature (°C)", "Current (µA)", "Core currents vs temperature"); b.legend(frameon=False, fontsize=8)
    save(fig, D / "fig_vref_tc.png")
    ln, ld = csv(D / "line.csv"), csv(D / "load.csv")
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.6))
    a.plot(ln["Vun"], ln["VREF"], color=SER[0], lw=2); style(a, "Vunregulated (V)", "VREF (V)", "Line regulation (RL = 3 kΩ)")
    b.plot(ld["IL"] * 1e3, ld["VREF"], color=SER[0], lw=2); style(b, "Extra load current IL (mA)", "VREF (V)", "Load regulation (Vunreg = 5 V)")
    save(fig, D / "fig_vref_line_load.png")
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.6))
    for k, T in enumerate((0, 27, 80)):
        s = csv(D / f"startup_{T}C_5V.csv"); a.plot(s["time"] * 1e6, s["VREF"], color=SER[k], lw=1.6, label=f"{T} °C")
    s = csv(D / "startup_27C_5V.csv"); a.plot(s["time"] * 1e6, s["Vun"], color=INK2, lw=1, ls="--", label="Vunregulated")
    style(a, "Time (µs)", "Voltage (V)", "Start-up from a 20 µs supply ramp"); a.legend(frameon=False, fontsize=8); a.set_xlim(0, 60)
    s = csv(D / "loadstep.csv")
    b.plot(s["time"] * 1e6, s["VREF"], color=SER[0], lw=1.6); style(b, "Time (µs)", "VREF (V)", "Load step 0 → 50 mA → 0 (0.1 µs edges)")
    b.set_xlim(290, 420)
    save(fig, D / "fig_vref_startup_loadstep.png")
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
    for a, key, ttl in ((axs[0], "core_Mc_gate", "Core loop (break at Mc gate)"), (axs[1], "LDO_M25_gate", "LDO loop (break at M25 gate)")):
        l = csv(D / f"loop_{key}.csv"); a.semilogx(l["f"], l["mag_dB"], color=SER[0], lw=2, label="|T| (dB)")
        a2 = a.twinx(); a2.semilogx(l["f"], l["phase_deg"], color=SER[1], lw=1.4, label="phase (°)"); a2.set_ylabel("Phase (°)", color=INK2)
        style(a, "Frequency (Hz)", "|T| (dB)", ttl); a.axhline(0, color=INK2, lw=0.8)
    save(fig, D / "fig_vref_loops.png")


def opamp_figs():
    D = R / "OpAmp"
    fig, a = plt.subplots(figsize=(6.4, 3.8))
    l = csv(D / "loop_0.4_50R.csv"); a.semilogx(l["f"], l["mag_dB"], color=SER[0], lw=2)
    a2 = a.twinx(); a2.semilogx(l["f"], l["phase_deg"], color=SER[1], lw=1.4); a2.set_ylabel("Phase of T (°)", color=INK2)
    style(a, "Frequency (Hz)", "Loop gain |T| (dB)", "Op-amp loop gain, unity follower, VIN = 0.4 V, 50 Ω"); a.axhline(0, color=INK2, lw=0.8)
    save(fig, D / "fig_opamp_loop.png")
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.6))
    for k, (tag, lab) in enumerate((("noload", "no load"), ("50R", "50 Ω"), ("15R75_50mA", "15.75 Ω (50 mA at FS)"), ("sink50mA", "50 mA sink"))):
        d = csv(D / f"dc_{tag}.csv"); a.plot(d["VIN"], d["VOUT"], color=SER[k], lw=1.6, label=lab)
        b.plot(d["VIN"], (d["VOUT"] - d["VIN"]) * 1e3, color=SER[k], lw=1.6, label=lab)
    style(a, "VIN (V)", "VOUT (V)", "Follower DC transfer"); a.legend(frameon=False, fontsize=8)
    style(b, "VIN (V)", "VOUT − VIN (mV)", "Follower error"); b.set_ylim(-10, 5); b.axvspan(0, 0.7875, color=GRID, alpha=0.6, lw=0)
    save(fig, D / "fig_opamp_dc.png")
    fig, a = plt.subplots(figsize=(6.4, 3.6))
    for k, tag in enumerate(("noload", "50R")):
        d = csv(D / f"step_{tag}.csv"); a.plot(d["time"] * 1e6, d["VOUT"], color=SER[k], lw=1.6, label=tag)
    style(a, "Time (µs)", "VOUT (V)", "Step response 0.1 ↔ 0.7 V (10 ns edges)"); a.legend(frameon=False, fontsize=8); a.set_xlim(4, 17)
    save(fig, D / "fig_opamp_step.png")


def dac_figs():
    D = R / "Complete_DAC"
    s = csv(D / "static_noload.csv")
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.8))
    a.step(s["code"], s["v(vout_ideal)"] * 1e3, where="mid", color=SER[0], lw=1.6, label="VOUT_IDEAL (VCVS)")
    a.step(s["code"], s["v(vout)"] * 1e3, where="mid", color=SER[1], lw=1.2, label="VOUT (op-amp)")
    a.plot(s["code"], s["code"] * 12.5, color=INK2, lw=0.8, ls="--", label="ideal 12.5 mV/code")
    style(a, "Input code", "Output (mV)", "Transfer characteristic, 000000-111111"); a.legend(frameon=False, fontsize=8)
    b.plot(s["code"][:-1], s["v(vout_ideal)_DNL"][:-1], "o-", ms=3, color=SER[0], lw=1, label="DNL (VCVS)")
    b.plot(s["code"], s["v(vout_ideal)_INL"], "s-", ms=3, color=SER[2], lw=1, label="INL (VCVS)")
    b.plot(s["code"], s["v(vout)_INL"], "^-", ms=3, color=SER[1], lw=1, label="INL (op-amp)")
    style(b, "Input code", "LSB", "DNL / INL (end-point)"); b.legend(frameon=False, fontsize=8); b.axhline(0, color=INK2, lw=0.8)
    save(fig, D / "fig_dac_static.png")
    w = csv(D / "static_noload_wave.csv")
    fig, a = plt.subplots(figsize=(10, 3.4))
    a.plot(w["time"] * 1e3, w["VOUT"] * 1e3, color=SER[1], lw=1, label="VOUT")
    a.plot(w["time"] * 1e3, w["VOUT_IDEAL"] * 1e3, color=SER[0], lw=1, ls="--", label="VOUT_IDEAL")
    style(a, "Time (ms)", "Output (mV)", "64-code staircase (20 µs per code, 5 ns logic edges)"); a.legend(frameon=False, fontsize=8)
    save(fig, D / "fig_dac_staircase.png")
    fig, a = plt.subplots(figsize=(6.4, 3.6))
    for k, code in enumerate((31, 63)):
        t = csv(D / f"tc_code{code}.csv")
        for node, ls in (("v(vout_ideal)", "-"), ("v(vout)", "--")):
            v = t[node]; a.plot(t["temp"], (v / v[list(t["temp"]).index(27)] - 1) * 1e6, ls, color=SER[k], lw=1.6,
                               label=f"{code:06b} {'VCVS' if 'ideal' in node else 'op-amp'}")
    style(a, "Temperature (°C)", "Deviation from 27 °C (ppm)", "Output vs temperature"); a.legend(frameon=False, fontsize=8)
    save(fig, D / "fig_dac_tc.png")
    st = csv(D / "settling_wave.csv")
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.6))
    a.plot(st["time"] * 1e6, st["VOUT"] * 1e3, color=SER[1], lw=1.2, label="VOUT")
    a.plot(st["time"] * 1e6, st["VOUT_IDEAL"] * 1e3, color=SER[0], lw=1, ls="--", label="VOUT_IDEAL")
    style(a, "Time (µs)", "Output (mV)", "Code steps 0→63→0→31→32→31→0 (50 Ω)"); a.legend(frameon=False, fontsize=8)
    m = (st["time"] > 239.9e-6) & (st["time"] < 240.5e-6)
    b.plot((st["time"][m] - 240e-6) * 1e9, st["VOUT"][m] * 1e3, color=SER[1], lw=1.4, label="VOUT")
    b.plot((st["time"][m] - 240e-6) * 1e9, st["VOUT_IDEAL"][m] * 1e3, color=SER[0], lw=1, ls="--", label="VOUT_IDEAL")
    style(b, "Time after the 31→32 edge (ns)", "Output (mV)", "Major-carry transition 31 → 32"); b.legend(frameon=False, fontsize=8)
    save(fig, D / "fig_dac_settling.png")
    fig, a = plt.subplots(figsize=(6.4, 3.4))
    m = (st["time"] > 239.95e-6) & (st["time"] < 240.05e-6)
    for k, (n1, n2) in enumerate((("clk_D1", "clk_bar_D1"), ("clk_B6", "clk_bar_B6"))):
        a.plot((st["time"][m] - 240e-6) * 1e9, st[n1][m], color=SER[2 * k], lw=1.6, label=n1)
        a.plot((st["time"][m] - 240e-6) * 1e9, st[n2][m], color=SER[2 * k + 1], lw=1.6, ls="--", label=n2)
    style(a, "Time (ns)", "V", "Logic stimuli at the 31 → 32 edge (5 ns edges)"); a.legend(frameon=False, fontsize=8)
    save(fig, D / "fig_clocks.png")
    j = json.loads((D / "summary.json").read_text())
    if "speed" in j:
        Ts = sorted(j["speed"], key=lambda k: -int(k[:-2]))
        x = [j["speed"][k]["update_rate_MSps"] for k in Ts]; y = [j["speed"][k]["max_err_vs_static_LSB"] for k in Ts]
        fig, a = plt.subplots(figsize=(6.4, 3.4))
        a.semilogx(x, y, "o-", color=SER[0], lw=2, ms=6); a.axhline(0.5, color=SER[1], lw=1, ls="--"); a.text(x[0], 0.55, "½ LSB", color=INK2, fontsize=8)
        style(a, "Update rate (MS/s)", "Max error vs static (LSB)", "Speed: error at the end of each code period (50 Ω)")
        save(fig, D / "fig_dac_speed.png")


if __name__ == "__main__":
    vref_figs(); opamp_figs(); dac_figs(); print("figures written")
