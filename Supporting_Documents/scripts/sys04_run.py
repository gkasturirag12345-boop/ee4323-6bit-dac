"""Characterise 04_Complete_6Bit_DAC.asc. Every run starts from the schematic (LTspice netlists it, then simulates).

INL/DNL convention (end-point): LSB_avg = (V63 - V0)/63, DNL_k = (V_k+1 - V_k)/LSB_avg - 1, INL_k = (V_k - V0)/LSB_avg - k.
Absolute: offset = V0 (ideal 0 V), gain error = (V63 - V0) - 63 x 12.5 mV, both in LSB of 12.5 mV.
TC (handout p.5) = (Vmax - Vmin) / Vnominal / (80 - 0) with Vnominal = V at 27 C.
"""
import json, sys, numpy as np
import sim, sys04_asc, sys_design

OUT = sim.ROOT / "Simulation_Results" / "Complete_DAC"
LSB = 12.5e-3
VHI = 3.62
RES = {}


def run(key, *, codes=None, T=20e-6, t0=200e-6, tr=5e-9, rload="50", directives=None, vun="PWL(0 0 20u 5)", stim=None):
    codes = list(range(64)) if codes is None else codes
    stim = stim if stim is not None else sys_design.pwl_sources(codes, t0, T, VHI, tr)
    s = sys04_asc.draw(codes=codes, T=T, t0=t0, vhi=VHI, tr=tr, vun=vun, rload=rload, directives=directives, stim_text=stim)
    log, net, rawp = sim.run_asc(s.text_asc(), f"s04_{key}", timeout=3000)
    (OUT / f"{key}.log").write_text(log)
    if sim.errors(log):
        print(key, "solver notes:", sim.errors(log)[:2])
    return sim.raw(rawp), net


def lin(v):
    v = np.asarray(v); lsb = (v[-1] - v[0]) / 63
    dnl = np.diff(v) / lsb - 1; inl = (v - v[0]) / lsb - np.arange(64)
    k = np.arange(64); a, b = np.polyfit(k, v, 1); inl_bf = (v - (a * k + b)) / a
    return dict(V0_mV=float(v[0] * 1e3), VFS_mV=float(v[-1] * 1e3), LSB_mV=float(lsb * 1e3),
                DNL_min=float(dnl.min()), DNL_max=float(dnl.max()), INL_min=float(inl.min()), INL_max=float(inl.max()),
                INL_bestfit_absmax=float(np.abs(inl_bf).max()),
                offset_LSB=float(v[0] / LSB), gain_error_LSB=float(((v[-1] - v[0]) - 63 * LSB) / LSB),
                monotonic=bool(np.all(np.diff(v) > 0))), dnl, inl


def sampler(g, t0, T, n, frac=0.95):
    t = g("time")
    return lambda node: np.array([np.interp(t0 + (k + frac) * T, t, g(node)) for k in range(n)])


def save(key, cols):
    np.savetxt(OUT / f"{key}.csv", np.column_stack([np.asarray(v, float) for v in cols.values()]), delimiter=",",
               header=",".join(cols), comments="")


def static():
    RES["static"] = {}
    for tag, rl in (("50R", "50"), ("noload", None)):
        d, net = run(f"static_{tag}", rload=rl)
        g, n = sim.getter(d); sm = sampler(g, 200e-6, 20e-6, 64)
        cols = {"code": np.arange(64)}
        r = {}
        for node in ("v(vout)", "v(vout_ideal)", "v(iout)", "v(vdd)"):
            cols[node] = sm(node)
        for node in ("v(vout)", "v(vout_ideal)"):
            r[node], dnl, inl = lin(cols[node]); cols[node + "_DNL"] = np.append(dnl, np.nan); cols[node + "_INL"] = inl
        r["VDD_min"], r["VDD_max"] = float(cols["v(vdd)"].min()), float(cols["v(vdd)"].max())
        save(f"static_{tag}", cols); RES["static"][tag] = r
        if tag == "noload":
            (OUT / "static_noload_netlist_from_schematic.net").write_text(net)
            # waveform for the report (decimated)
            t = g("time"); m = slice(None, None, max(1, len(t) // 20000))
            save("static_noload_wave", {"time": t[m], "VOUT": g("v(vout)")[m], "VOUT_IDEAL": g("v(vout_ideal)")[m], "VDD": g("v(vdd)")[m]})


def vcvs_isolation():
    """Re-run the LTspice netlist of the schematic without E_IDEAL and compare IOUT / VOUT."""
    net = (OUT / "static_noload_netlist_from_schematic.net").read_text()
    without = "\n".join(l for l in net.splitlines() if not l.split() or l.split()[0] != "E_IDEAL")
    log, rp = sim.run_net(without, "s04_noE", timeout=3000)
    d = sim.raw(rp); g, n = sim.getter(d); sm = sampler(g, 200e-6, 20e-6, 64)
    base = np.loadtxt(OUT / "static_noload.csv", delimiter=",", skiprows=1)
    hdr = open(OUT / "static_noload.csv").readline().strip().split(",")
    io0, vo0 = base[:, hdr.index("v(iout)")], base[:, hdr.index("v(vout)")]
    RES["vcvs_isolation"] = dict(max_dV_IOUT_uV=float(np.abs(sm("v(iout)") - io0).max() * 1e6),
                                 max_dV_VOUT_uV=float(np.abs(sm("v(vout)") - vo0).max() * 1e6),
                                 E_input_current="ideal VCVS: control inputs draw no current")


def tc():
    RES["tc"] = {}
    temps = [0, 10, 20, 27, 30, 40, 50, 60, 70, 80]
    for code in (31, 63):
        codes = [code]
        d, _ = run(f"tc_code{code}", codes=codes, T=100e-6, t0=300e-6, rload=None,
                   directives=[".tran 0 400u 0 200n", ".step temp list " + " ".join(map(str, temps))])
        out = {}
        for node in ("v(vout)", "v(vout_ideal)", "v(vdd)"):
            vals = []
            for st in range(d.step_count):
                g, n = sim.getter(d, st); vals.append(float(np.interp(395e-6, g("time"), g(node))))
            out[node] = vals
        save(f"tc_code{code}", {"temp": temps, **out})
        r = {}
        for node in ("v(vout)", "v(vout_ideal)", "v(vdd)"):
            v = np.array(out[node]); vn = v[temps.index(27)]
            r[node] = dict(Vmin=float(v.min()), Vmax=float(v.max()), Vnominal_27C=float(vn),
                           TC_ppm_per_C=float((v.max() - v.min()) / vn / 80 * 1e6))
        RES["tc"][f"{code:06b}"] = r


def power():
    RES["power"] = {}
    dac_src = ["m53", "m54", "m82", "m83", "m87", "m91"]
    oa_src = ["m49", "m30", "m37", "m38", "m44"]
    for code in (0, 31, 63):
        for tag, rl in (("noload", None), ("50R", "50")):
            d, _ = run(f"power_code{code}_{tag}", codes=[code], T=100e-6, t0=300e-6, rload=rl, directives=[".tran 0 400u 0 200n"])
            g, n = sim.getter(d); at = lambda k: float(np.interp(395e-6, g("time"), g(k)))
            vun, vdd = at("v(vunregulated)"), at("v(vdd)")
            i_tot = -at("i(vunreg)")
            i_dac = -sum(at(f"id({m})") for m in dac_src)
            i_oa = -sum(at(f"id({m})") for m in oa_src) + at("id(m45)")
            i_m29 = -at("id(m29)"); i_bleed = at("i(r7)")
            i_load = at("v(vout)") / 50.0 if rl else 0.0
            r = dict(Vun=vun, VDD=vdd, I_total_mA=i_tot * 1e3, I_M29_mA=i_m29 * 1e3, I_DAC_mA=i_dac * 1e3,
                     I_OPAMP_mA=i_oa * 1e3, I_bleeder_R7R6_mA=i_bleed * 1e3, I_load_mA=i_load * 1e3,
                     I_reg_internal_mA=(i_tot - i_m29) * 1e3,
                     kcl_check_M29_minus_parts_uA=(i_m29 - i_dac - i_oa - i_bleed) * 1e6,
                     P_total_mW=vun * i_tot * 1e3, P_DAC_mW=vdd * i_dac * 1e3, P_OPAMP_mW=vdd * (i_oa - i_load) * 1e3,
                     P_load_mW=at("v(vout)") * i_load * 1e3)
            r["P_regulator_mW"] = r["P_total_mW"] - vdd * (i_dac + i_oa) * 1e3
            RES["power"][f"code{code}_{tag}"] = r


def minsupply():
    RES["minsupply"] = {}
    for code in (63, 0):
        for tag, rl in (("noload", None), ("50R", "50")):
            # quasi-static supply ramp: settle at 5.5 V, then ramp 5.5 V -> 2.5 V in 3 ms (1 V/ms)
            d, _ = run(f"minsup_code{code}_{tag}", codes=[code], T=4e-3, t0=100e-6, rload=rl,
                       vun="PWL(0 0 20u 5.5 300u 5.5 3300u 2.5)", directives=[".tran 0 3300u 0 200n"])
            g, n = sim.getter(d); t = g("time"); m = t >= 300e-6
            vu, vo, vi, vdd = [g(k)[m][::-1] for k in ("v(vunregulated)", "v(vout)", "v(vout_ideal)", "v(vdd)")]
            save(f"minsup_code{code}_{tag}", {"Vun": vu, "VOUT": vo, "VOUT_IDEAL": vi, "VDD": vdd})
            v5, d5 = np.interp(5.0, vu, vo), np.interp(5.0, vu, vdd)
            ok_out = np.abs(vo - v5) <= LSB / 2; ok_vdd = np.abs(vdd - d5) <= 0.01 * d5
            # lowest Vun from which the output stays within 1/2 LSB all the way up to 5 V
            def lowest(ok):
                idx = np.where(vu <= 5.0)[0][::-1]
                last = None
                for i in idx:
                    if ok[i]:
                        last = vu[i]
                    else:
                        break
                return float(last) if last is not None else None
            RES["minsupply"][f"code{code}_{tag}"] = dict(VOUT_at_5V_mV=float(v5 * 1e3), VDD_at_5V=float(d5),
                                                        Vun_min_VOUT_halfLSB=lowest(ok_out), Vun_min_VDD_1pct=lowest(ok_vdd),
                                                        dVOUT_dVun_mV_per_V_4p8_to_5p2=float((np.interp(5.2, vu, vo) - np.interp(4.8, vu, vo)) / 0.4 * 1e3))


def speed():
    RES["speed"] = {}
    ref = np.loadtxt(OUT / "static_50R.csv", delimiter=",", skiprows=1)
    hdr = open(OUT / "static_50R.csv").readline().strip().split(",")
    vref_static = ref[:, hdr.index("v(vout)")]
    for T in (2e-6, 1e-6, 500e-9, 250e-9, 125e-9):
        d, _ = run(f"speed_{int(T * 1e9)}ns", T=T, t0=200e-6, tr=5e-9, rload="50",
                   directives=[f".tran 0 {200e-6 + 64 * T:.6g} 0 {min(T / 100, 2e-9):.4g}"])
        g, n = sim.getter(d); sm = sampler(g, 200e-6, T, 64, frac=0.98)
        vo = sm("v(vout)"); r, dnl, inl = lin(vo)
        r["max_err_vs_static_LSB"] = float(np.abs(vo - vref_static).max() / LSB)
        r["update_rate_MSps"] = 1e-6 / T
        RES["speed"][f"{int(T * 1e9)}ns"] = r


def settling():
    codes, T = [0, 63, 0, 31, 32, 31, 0], 10e-6
    d, _ = run("settling", codes=codes, T=T, t0=200e-6, tr=5e-9, rload="50", directives=[f".tran 0 {200e-6 + 7 * T:.6g} 0 1n"])
    g, n = sim.getter(d); t = g("time")
    m = t > 195e-6
    save("settling_wave", {"time": t[m], "VOUT": g("v(vout)")[m], "VOUT_IDEAL": g("v(vout_ideal)")[m], "IOUT": g("v(iout)")[m],
                           "VDD": g("v(vdd)")[m], "clk_D1": g("v(clk_d1)")[m], "clk_bar_D1": g("v(clk_bar_d1)")[m],
                           "clk_B6": g("v(clk_b6)")[m], "clk_bar_B6": g("v(clk_bar_b6)")[m]})
    out = []
    for k in range(1, len(codes)):
        ts = 200e-6 + k * T; mm = (t >= ts) & (t < ts + T)
        for node in ("v(vout)", "v(vout_ideal)"):
            y = g(node)[mm]; tt = t[mm]; fin = y[-1]; prev = codes[k - 1] * LSB
            bad = np.where(np.abs(y - fin) > LSB / 2)[0]
            glitch = float(np.max(np.abs(y - np.clip(y, min(prev, fin), max(prev, fin)))))
            out.append(dict(transition=f"{codes[k-1]}->{codes[k]}", node=node, settle_halfLSB_ns=float((tt[bad[-1]] - ts) * 1e9) if len(bad) else 0.0,
                            glitch_outside_range_mV=glitch * 1e3, final_mV=float(fin * 1e3)))
    vdd = g("v(vdd)")[t > 200e-6]
    RES["settling"] = dict(steps=out, VDD_min=float(vdd.min()), VDD_max=float(vdd.max()))
    # clock verification: complementarity and edge timing at the 31->32 transition (all bits switch)
    ts = 200e-6 + 4 * T; mm = (t > ts - 20e-9) & (t < ts + 20e-9)
    comp = {}
    for b in sys_design.BITS:
        a, bb = g(f"v(clk_{b.lower()})"), g(f"v(clk_bar_{b.lower()})")
        comp[b] = dict(max_abs_sum_minus_VHI_mV=float(np.abs(a + bb - VHI).max() * 1e3))
    RES["clocks"] = dict(levels=f"0 / {VHI} V", edge_s=5e-9, complementarity=comp)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    which = sys.argv[1:] or ["static", "vcvs", "tc", "power", "minsupply", "speed", "settling"]
    prev = json.loads((OUT / "summary.json").read_text()) if (OUT / "summary.json").exists() else {}
    for w in which:
        {"static": static, "vcvs": vcvs_isolation, "tc": tc, "power": power, "minsupply": minsupply, "speed": speed, "settling": settling}[w]()
        prev.update(RES); (OUT / "summary.json").write_text(json.dumps(prev, indent=1))
        print(w, "done", flush=True)
    print(json.dumps(RES, indent=1))
