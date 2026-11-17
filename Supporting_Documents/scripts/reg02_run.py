"""Characterise 02_VREF_Regulator.asc (all runs start from the schematic; LTspice netlists it, then simulates)."""
import json, re, numpy as np
import sim, reg02_asc

OUT = sim.ROOT / "Simulation_Results" / "VREF"
RES = {}


def run(key, active, vun="5", il="0", temp=None, extra=()):
    s = reg02_asc.draw_file(active, vun=vun, il=il, temp=temp)
    for k, t in enumerate(extra):
        s.text(0, 1500 + 36 * k, t, 2, directive=True)
    log, net, rawp = sim.run_asc(s.text_asc(), f"reg02_{key}")
    (OUT / f"{key}.log").write_text(log)
    err = sim.errors(log)
    if err:
        print(key, "ERRORS:", err[:3])
    return sim.raw(rawp), log, net


def save(key, cols):
    names = list(cols)
    np.savetxt(OUT / f"{key}.csv", np.column_stack([np.asarray(cols[n], float) for n in names]), delimiter=",",
               header=",".join(names), comments="")


def tc_ppm(T, y, tnom=27.0):
    return (y.max() - y.min()) / np.interp(tnom, T, y) / (T.max() - T.min()) * 1e6


def tian(net_text, brk_dev, brk_pin_old, name):
    """Tian loop gain: break the gate of brk_dev (node brk_pin_old) with Vi (series) + Ii (shunt)."""
    lines = []
    for l in net_text.splitlines():
        t = l.split()
        if t and t[0] == brk_dev:
            t[2] = "XBRK"; l = " ".join(t)
        if l.strip().lower().startswith((".tran", ".dc", ".op", ".ac", ".backanno", ".end")):
            continue
        lines.append(l)
    body = "\n".join(lines)
    out = []
    for vi, ii in ((1, 0), (0, 1)):
        txt = body + f"\nVi XBRK {brk_pin_old} 0 AC {vi}\nIi 0 XBRK 0 AC {ii}\n.ac dec 40 1 1G\n.end\n"
        log, rp = sim.run_net(txt, name)
        d = sim.raw(rp); g, n = sim.getter(d, cplx=True)
        out.append((g("frequency").real, g("v(xbrk)"), g("i(vi)")))
    f, V1, I1 = out[0]; _, V2, I2 = out[1]
    T = -1 / (1 - 1 / (2 * (I1 * V2 - V1 * I2) + V1 + I2))
    mag, ang = 20 * np.log10(abs(T)), np.angle(T, deg=True)
    i = np.where(mag < 0)[0]; k = i[0]
    pm = (180 + ang[k]) if ang[k] < 0 else (ang[k] - 180)
    return f, mag, ang, dict(T0_dB=float(mag[0]), UGF_Hz=float(f[k]), PM_deg=float(pm))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # 1. operating point at Vunregulated = 5 V, 27 C, RL = 3 kohm
    d, log, net = run("op", "op", vun="5")
    g, n = sim.getter(d); v = lambda k: float(g(k)[0])
    RES["op"] = dict(VREF=v("v(vref)"), VX=v("v(vx)"), VBP=v("v(vbp)"), VCP=v("v(vcp)"), VCN=v("v(vcn)"), VBN=v("v(vbn)"),
                     V_G=v("v(g)"), V_A=v("v(a)"),
                     IPTAT_uA=v("ic(ma)") * 1e6, Ic_Mb_uA=v("ic(mb)") * 1e6, ICTAT_R4_uA=v("i(r4)") * 1e6,
                     ICTAT_R2_uA=v("i(r2)") * 1e6, ICONST_uA=v("i(r5)") * 1e6, I_CONST_Gm_uA=v("id(m7)") * 1e6,
                     I_M1_uA=-v("id(m1)") * 1e6, I_Mc_uA=v("id(mc)") * 1e6, I_tail_uA=-v("id(m26)") * 1e6,
                     I_supply_mA=-v("i(vunreg)") * 1e3, I_M29_mA=-v("id(m29)") * 1e3, I_bleeder_mA=v("i(r7)") * 1e3)
    RES["op"]["I_regulator_internal_uA"] = (RES["op"]["I_supply_mA"] - RES["op"]["I_M29_mA"]) * 1e3
    (OUT / "op_netlist_from_schematic.net").write_text(net)
    # 2. temperature 0-80 C
    d, log, _ = run("tc", "tc", vun="5"); g, n = sim.getter(d); T = g("temperature")
    cols = {k: g(k) for k in ("temperature", "v(vref)", "v(vx)", "i(r5)", "ic(ma)", "i(r4)", "v(vbn)", "v(vcn)")}
    save("tc", cols)
    RES["tc"] = {k: dict(at0=float(cols[k][0]), at27=float(np.interp(27, T, cols[k])), at80=float(cols[k][-1]),
                         TC_ppm_per_C=float(tc_ppm(T, cols[k]))) for k in cols if k != "temperature"}
    # 3. line regulation (DC sweep of Vunregulated)
    d, log, _ = run("line", "line", vun="5"); g, n = sim.getter(d); vu, vr = g("v(vunregulated)"), g("v(vref)")
    save("line", {"Vun": vu, "VREF": vr, "VX": g("v(vx)"), "IPTAT": g("ic(ma)")})
    v5 = np.interp(5, vu, vr); ok = np.abs(vr - v5) < 0.02
    RES["line"] = dict(VREF_at_4p5=float(np.interp(4.5, vu, vr)), VREF_at_5=float(v5), VREF_at_5p5=float(np.interp(5.5, vu, vr)),
                       line_reg_mV_per_V_4p5_to_5=float((v5 - np.interp(4.5, vu, vr)) / 0.5 * 1e3),
                       within_20mV_range_V=[float(vu[ok].min()), float(vu[ok].max())])
    # 4. load regulation (IL 0-55 mA on top of RL)
    d, log, _ = run("load", "load", vun="5"); g, n = sim.getter(d); il, vr = g("i(il)"), g("v(vref)")
    save("load", {"IL": il, "VREF": vr, "GP": g("v(gp)")})
    RES["load"] = dict(VREF_IL0=float(vr[0]), VREF_IL50m=float(np.interp(50e-3, il, vr)),
                       load_reg_mV_0_to_50mA=float((vr[0] - np.interp(50e-3, il, vr)) * 1e3))
    # 5. start-up from a 20 us supply ramp at 0/27/80 C (5 V) and 27 C at 4.5 V
    RES["startup"] = {}
    for T, vend in ((0, 5), (27, 5), (80, 5), (0, 4.5), (27, 4.5), (80, 4.5)):
        d, log, _ = run(f"startup_{T}C_{vend}V", "startup", vun=f"PWL(0 0 20u {vend})", temp=T)
        g, n = sim.getter(d); t, vr = g("time"), g("v(vref)")
        bad = np.where(np.abs(vr - vr[-1]) > 1e-3)[0]
        save(f"startup_{T}C_{vend}V", {"time": t, "VREF": vr, "VX": g("v(vx)"), "Vun": g("v(vunregulated)")})
        RES["startup"][f"{T}C_{vend}V"] = dict(VREF_final=float(vr[-1]), IPTAT_final_uA=float(g("ic(ma)")[-1] * 1e6),
                                               settle_1mV_us=float(t[bad[-1]] * 1e6) if len(bad) else 0.0,
                                               pp_last_100us_mV=float(np.ptp(vr[t > t[-1] - 100e-6]) * 1e3))
    # 6. load step 0 -> 50 mA -> 0 (plus 1 mA in RL)
    d, log, _ = run("loadstep", "loadstep", vun="5", il="PWL(0 0 300u 0 300.1u 50m 400u 50m 400.1u 0)")
    g, n = sim.getter(d); t, vr = g("time"), g("v(vref)")
    save("loadstep", {"time": t, "VREF": vr, "IL": g("i(il)")})
    seg = lambda a, b: vr[(t > a) & (t < b)]
    v1, v51 = seg(290e-6, 300e-6).mean(), seg(390e-6, 400e-6).mean()
    after = (t > 300e-6) & (t < 400e-6); bad = np.where(np.abs(vr[after] - v51) > 1e-3)[0]
    RES["loadstep"] = dict(VREF_1mA=float(v1), VREF_51mA=float(v51), dip_mV=float((v1 - seg(300e-6, 330e-6).min()) * 1e3),
                           overshoot_mV=float((seg(400e-6, 430e-6).max() - v1) * 1e3),
                           recovery_1mV_us=float((t[after][bad[-1]] - 300e-6) * 1e6) if len(bad) else 0.0)
    # 7. loop gains (Tian), probes inserted into LTspice's netlist of the schematic
    net = (OUT / "op_netlist_from_schematic.net").read_text()
    RES["loop"] = {}
    for key, dev, node in (("core_Mc_gate", "Mc", "G"), ("LDO_M25_gate", "M25", "FB")):
        f, mag, ang, r = tian(net, dev, node, f"tian_{key}")
        save(f"loop_{key}", {"f": f, "mag_dB": mag, "phase_deg": ang}); RES["loop"][key] = r
    (OUT / "summary.json").write_text(json.dumps(RES, indent=1))
    print(json.dumps(RES, indent=1))


if __name__ == "__main__":
    main()
