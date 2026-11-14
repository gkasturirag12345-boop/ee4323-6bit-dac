"""Full characterisation, run from the .asc test benches in Revised_Project/LTspice. Results -> results/<test>/."""
import json, shutil, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
import tb, run_asc, sim, dac_static, sys_tran, stim

RES = Path(__file__).resolve().parents[1] / "results"
RES.mkdir(exist_ok=True)
LSB = 12.5e-3


def keep(name, log, cols):
    d = RES / name
    d.mkdir(exist_ok=True)
    (d / f"{name}.log").write_text(log)
    if cols:
        keys = list(cols)
        n = min(len(np.atleast_1d(cols[k])) for k in keys)
        arr = np.column_stack([np.atleast_1d(cols[k])[:n] for k in keys])
        np.savetxt(d / f"{name}.csv", arr, delimiter=",", header=",".join(keys), comments="")
    for ext in (".asc",):
        src = tb.LT / f"{name}{ext}"
        if src.exists():
            shutil.copy(src, d / src.name)
    return d


def sysrun(name, codes, T, **kw):
    asc, sched = tb.system_tb(name, codes, T, **kw)
    log, d, g = run_asc.run(asc, name)
    return log, g, sched


# ------------------------------------------------------------------ system tests
def static(name="TB_Static", load=None):
    log, g, sched = sysrun(name, list(range(64)), 20e-6, load=load)
    vo = sys_tran.sample(g, sched, 20e-6)
    r = dac_static.lin(vo)
    ideal = np.arange(64) * LSB
    keep(name, log, {"code": np.arange(64), "vout_V": vo, "ideal_V": ideal, "error_LSB": (vo - ideal) / LSB,
                     "inl_LSB": r["inl"], "dnl_LSB": np.r_[np.nan, r["dnl"]]})
    t = g("time"); m = t > 290e-6
    keep(name + "_wave", "", {"time_s": t[m][::4], "vout_V": g("v(vout)")[m][::4], "iout_V": g("v(iout)")[m][::4],
                              "vdd_V": g("v(vdd)")[m][::4]})
    return dict(v0=vo[0], vfs=vo[-1], lsb=r["lsb"], dnl_max=float(np.nanmax(np.abs(r["dnl"]))),
                inl_max=float(np.max(np.abs(r["inl"]))), offset_lsb=r["offset_lsb"], gain_err_lsb=r["gain_err_lsb"],
                mono=r["mono"], max_abs_err_lsb=float(np.max(np.abs((vo - ideal) / LSB))))


def speed(T):
    name = f"TB_Speed_{int(round(T * 1e9))}ns"
    log, g, sched = sysrun(name, list(range(64)), T, t0=200e-6, maxstep=T / 100)
    vo = sys_tran.sample(g, sched, T, frac=0.98)
    r = dac_static.lin(vo)
    keep(name, log, {"code": np.arange(64), "vout_V": vo})
    return dict(T=T, inl=float(np.max(np.abs(r["inl"]))), dnl=float(np.max(np.abs(r["dnl"]))), lsb=r["lsb"],
                fs=vo[-1], err=float(np.max(np.abs(vo - np.arange(64) * LSB)) / LSB))


def steps():
    name = "TB_Settling"
    codes, T = [0, 63, 0, 31, 32, 31, 0], 10e-6
    log, g, sched = sysrun(name, codes, T, t0=200e-6, maxstep=2e-9)
    t, vo, io = g("time"), g("v(vout)"), g("v(iout)")
    out = []
    for i in range(1, len(codes)):
        c0, ts = codes[i], sched[i][1]
        m = (t >= ts) & (t < ts + T)
        final = vo[m][-1]
        bad = np.where(np.abs(vo[m] - final) > LSB / 2)[0]
        tset = (t[m][bad[-1]] - ts) if len(bad) else 0.0
        prev = codes[i - 1] * LSB
        glitch_pk = float(np.max(np.abs(vo[m] - np.clip(vo[m], min(prev, final), max(prev, final)))))
        out.append(dict(transition=f"{codes[i-1]}->{c0}", settle_ns=tset * 1e9, final_mV=final * 1e3,
                        overshoot_or_glitch_mV=glitch_pk * 1e3))
    mm = t > 190e-6
    keep(name, log, {"time_s": t[mm], "vout_V": vo[mm], "iout_V": io[mm], "clk_D1": g("v(clk_d1)")[mm],
                     "clk_bar_D1": g("v(clk_bar_d1)")[mm], "clk_B3": g("v(clk_b3)")[mm], "clk_bar_B3": g("v(clk_bar_b3)")[mm],
                     "clk_B6": g("v(clk_b6)")[mm], "clk_bar_B6": g("v(clk_bar_b6)")[mm]})
    # clock complementarity / overlap at the 31->32 transition (all bits switch)
    ts = sched[4][1]; m = (t > ts - 5e-9) & (t < ts + 5e-9)
    comp = {b: float(np.max(np.abs(g(f"v(clk_{b.lower()})")[m] + g(f"v(clk_bar_{b.lower()})")[m] - 3.0))) for b in stim.BITS}
    return out, comp


def tc(T):
    name = f"TB_TC_{T}C"
    log, g, sched = sysrun(name, [0, 31, 63], 20e-6, temp=T)
    vo = sys_tran.sample(g, sched, 20e-6); vdd = sys_tran.sample(g, sched, 20e-6, node="v(vdd)")
    keep(name, log, {"code": [0, 31, 63], "vout_V": vo, "vdd_V": vdd})
    return T, vo, vdd[0]


def psrr(f):
    name = f"TB_PSRR_{int(f)}Hz"
    vun, tend = tb.ripple_pwl(f, amp=0.05)
    T = tend - 300e-6
    log, g, sched = sysrun(name, [63], T, vun=vun, maxstep=min(T / 400, 1 / (f * 48)))
    t = g("time"); m = t > 300e-6 + 1 / f        # skip the first ripple period
    amp = lambda y: (y[m].max() - y[m].min()) / 2
    a_vun, a_vdd, a_out = amp(g("v(vunregulated)")), amp(g("v(vdd)")), amp(g("v(vout)"))
    keep(name, log, {"time_s": t[m], "vun_V": g("v(vunregulated)")[m], "vdd_V": g("v(vdd)")[m], "vout_V": g("v(vout)")[m]})
    return dict(f=f, vdd_ripple_uV=a_vdd * 1e6, vout_ripple_uV=a_out * 1e6,
                psrr_vdd_dB=20 * np.log10(a_vun / max(a_vdd, 1e-12)), psrr_out_dB=20 * np.log10(a_vun / max(a_out, 1e-12)))


def power():
    name = "TB_Power"
    log, g, sched = sysrun(name, [0, 63], 50e-6, ammeters=True)
    t = g("time")
    out = {}
    for c, ts in sched:
        m = (t > ts + 40e-6) & (t < ts + 50e-6)
        iun = -np.mean(g("i(vunregulated)")[m]); idac = np.mean(g("i(vi_dac)")[m]); iopa = np.mean(g("i(vi_opamp)")[m])
        vdd = np.mean(g("v(vdd)")[m]); vun = np.mean(g("v(vunregulated)")[m])
        out[c] = dict(I_total_uA=iun * 1e6, I_dac_uA=idac * 1e6, I_opamp_uA=iopa * 1e6,
                      I_reg_uA=(iun - idac - iopa) * 1e6, VDD=vdd, Vun=vun, P_total_mW=vun * iun * 1e3)
    keep(name, log, {"code": [0, 63], "I_total_uA": [out[c]["I_total_uA"] for c in (0, 63)],
                     "I_dac_uA": [out[c]["I_dac_uA"] for c in (0, 63)], "I_opamp_uA": [out[c]["I_opamp_uA"] for c in (0, 63)],
                     "I_reg_uA": [out[c]["I_reg_uA"] for c in (0, 63)]})
    return out


def minsupply(code=63):
    name = f"TB_MinSupply_code{code}"
    vun = "PWL(0 0 20u 5 300u 5 400u 5.5 500u 5.5 2500u 2)"
    log, g, sched = sysrun(name, [code], 2.2e-3, vun=vun, maxstep=200e-9)
    t = g("time"); m = t > 500e-6
    vu, vdd, vo = g("v(vunregulated)")[m], g("v(vdd)")[m], g("v(vout)")[m]
    nom = np.interp(5.0, vu[::-1], vo[::-1]); vddn = np.interp(5.0, vu[::-1], vdd[::-1])
    ok = np.abs(vo - nom) <= LSB / 2
    vmin_out = float(vu[np.where(~ok)[0][0]]) if (~ok).any() else float(vu.min())
    okd = np.abs(vdd - vddn) <= 0.01 * vddn
    vmin_vdd = float(vu[np.where(~okd)[0][0]]) if (~okd).any() else float(vu.min())
    line = (np.interp(5.5, vu[::-1], vdd[::-1]) - np.interp(4.5, vu[::-1], vdd[::-1]))
    keep(name, log, {"vun_V": vu[::5], "vdd_V": vdd[::5], "vout_V": vo[::5]})
    return dict(code=code, vout_nom=nom, vdd_nom=vddn, vmin_halfLSB=vmin_out, vmin_vdd1pct=vmin_vdd,
                line_reg_mV_per_V=line * 1e3, psr_dc_out_dB=20 * np.log10(1.0 / max(abs(
                    np.interp(5.5, vu[::-1], vo[::-1]) - np.interp(4.5, vu[::-1], vo[::-1])), 1e-12)))


# ------------------------------------------------------------------ block tests
def opamp_ac(vbn, vcn, tag, load=None, vcm=0.4):
    name = f"TB_OpAmp_AC_{tag}"
    asc = tb.opamp_tb(name, "ac", vbn, vcn, load=load, vcm=vcm)
    log, d, g = run_asc.run(asc, name)
    f = g("frequency")
    n = [v.name.lower() for v in d.variables]
    h = np.array(d.values[n.index("v(vout)")])
    gdb = 20 * np.log10(np.abs(h)); ph = np.unwrap(np.angle(h)) * 180 / np.pi
    i = np.where(gdb < 0)[0][0]
    keep(name, log, {"freq_Hz": f, "gain_dB": gdb, "phase_deg": ph})
    return dict(tag=tag, A0_dB=float(gdb[0]), UGB_MHz=float(f[i] / 1e6), PM_deg=float(180 + ph[i]))


def opamp_dc(vbn, vcn, tag, load=None):
    name = f"TB_OpAmp_DC_{tag}"
    asc = tb.opamp_tb(name, "dc", vbn, vcn, load=load)
    log, d, g = run_asc.run(asc, name)
    vi, vo, idd = g("v(vinp)") if False else None, g("v(vout)"), g("i(vdd)")
    n = [v.name.lower() for v in d.variables]; vi = np.array([x.real for x in d.values[0]])
    err = vo - vi; ok = np.abs(err) < 1e-3
    keep(name, log, {"vin_V": vi, "vout_V": vo, "err_mV": err * 1e3, "idd_mA": -idd * 1e3})
    rl = float(load) if load else None
    return dict(tag=tag, max_err_mV_0_to_FS=float(np.max(np.abs(err[vi <= 0.7875 + 1e-9])) * 1e3),
                vin_max_tracking=float(vi[ok][-1]), vin_min_tracking=float(vi[ok][0]),
                iout_at_FS_mA=(float(np.interp(0.7875, vi, vo)) / rl * 1e3) if rl else None)


def opamp_step(vbn, vcn):
    name = "TB_OpAmp_Step"
    asc = tb.opamp_tb(name, "step", vbn, vcn, load="50")
    log, d, g = run_asc.run(asc, name)
    t, vo = g("time"), g("v(vout)")
    keep(name, log, {"time_s": t, "vout_V": vo})
    m = (t > 5e-6) & (t < 15e-6); tt, y = t[m], vo[m]
    final = y[-1]; bad = np.where(np.abs(y - final) > LSB / 2)[0]
    i10, i90 = np.argmax(y > 0.1 + 0.06), np.argmax(y > 0.1 + 0.54)
    return dict(slew_V_per_us=0.48 / ((tt[i90] - tt[i10]) * 1e6), settle_ns=(tt[bad[-1]] - 5e-6) * 1e9 if len(bad) else 0,
                overshoot_mV=(y.max() - final) * 1e3)


def reg_tc():
    name = "TB_Regulator_TC"
    asc = tb.reg_tb(name, "5", [".dc temp 0 80 5"])
    log, d, g = run_asc.run(asc, name)
    T = np.array([x.real for x in d.values[0]]); vref = g("v(vref)")
    n = [v.name.lower() for v in d.variables]
    vx = g("v(xreg:vx)") if "v(xreg:vx)" in n else None
    keep(name, log, {"temp_C": T, "vref_V": vref, **({"vx_V": vx} if vx is not None else {})})
    i = np.argmin(abs(T - 25))
    return dict(vref27=float(vref[i]), tc_ppm=float((vref.max() - vref.min()) / vref[i] / 80 * 1e6),
                vx_tc_ppm=float((vx.max() - vx.min()) / vx[i] / 80 * 1e6) if vx is not None else None)


def reg_load():
    name = "TB_Regulator_Load"
    asc = tb.reg_tb(name, "PWL(0 0 20u 5)", [".tran 0 500u 0 20n startup"], load_r="3k",
                    load_i="PWL(0 0 300u 0 300.1u 50m 400u 50m 400.1u 0)")
    log, d, g = run_asc.run(asc, name)
    t, v = g("time"), g("v(vref)")
    keep(name, log, {"time_s": t[t > 250e-6], "vref_V": v[t > 250e-6]})
    seg = lambda a, b: v[(t >= a) & (t < b)]
    v1, v51 = seg(290e-6, 300e-6).mean(), seg(390e-6, 400e-6).mean()
    rec = t[(t > 300e-6) & (t < 400e-6)][np.where(np.abs(seg(300e-6, 400e-6) - v51) > 1e-3)[0][-1]] - 300e-6
    return dict(vref_1mA=v1, vref_51mA=v51, load_reg_mV=(v1 - v51) * 1e3, dip_mV=(v1 - seg(300e-6, 320e-6).min()) * 1e3,
                overshoot_mV=(seg(400e-6, 420e-6).max() - v1) * 1e3, recovery_us=rec * 1e6)


def reg_startup(T):
    name = f"TB_Regulator_Startup_{T}C"
    asc = tb.reg_tb(name, "PWL(0 0 20u 5)", [".tran 0 200u 0 50n startup", ".save V(vref) V(xreg:su) I(Vunregulated)"], temp=T)
    log, d, g = run_asc.run(asc, name)
    t, v = g("time"), g("v(vref)")
    keep(name, log, {"time_s": t, "vref_V": v, "su_V": g("v(xreg:su)")})
    i = np.where(np.abs(v - v[-1]) > 0.003)[0][-1]
    return dict(T=T, vref_final=float(v[-1]), su_final=float(g("v(xreg:su)")[-1]), t_settle_us=float(t[i] * 1e6))


def _store(res):
    """Merge results into summary.json; a FAILED entry never overwrites an earlier good result."""
    prev = json.loads((RES / "summary.json").read_text()) if (RES / "summary.json").exists() else {}
    prev.update({k: v for k, v in res.items() if not (isinstance(v, str) and v.startswith("FAILED") and k in prev)})
    (RES / "summary.json").write_text(json.dumps(prev, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o)))


if __name__ == "__main__":
    which = sys.argv[1:] or ["all"]
    out = {}
    t0 = time.time()
    with ThreadPoolExecutor(2) as ex:
        jobs = {}
        if "all" in which or "static" in which:
            jobs["static"] = ex.submit(static); jobs["static_50R"] = ex.submit(static, "TB_Static_50R", "50")
        if "all" in which or "speed" in which or "speed125" in which:
            for T in ((2e-6, 1e-6, 500e-9, 250e-9, 125e-9) if "speed" in which or "all" in which else (125e-9,)):
                jobs[f"speed_{T}"] = ex.submit(speed, T)
        if "all" in which or "steps" in which:
            jobs["steps"] = ex.submit(steps)
        if "all" in which or "tc" in which:
            for T in (0, 20, 40, 60, 80):
                jobs[f"tc_{T}"] = ex.submit(tc, T)
        if "all" in which or "psrr" in which:
            for f in (1e3, 10e3, 100e3, 1e6):
                jobs[f"psrr_{f}"] = ex.submit(psrr, f)
        if "all" in which or "power" in which:
            jobs["power"] = ex.submit(power)
        if "all" in which or "minsupply" in which:
            jobs["minsupply63"] = ex.submit(minsupply, 63); jobs["minsupply0"] = ex.submit(minsupply, 0)
        if "all" in which or "reg" in which:
            jobs["reg_tc"] = ex.submit(reg_tc); jobs["reg_load"] = ex.submit(reg_load)
            for T in (0, 27, 80):
                jobs[f"reg_startup_{T}"] = ex.submit(reg_startup, T)
        for k, j in jobs.items():
            try:
                out[k] = j.result()
            except Exception as e:  # report, do not hide
                out[k] = f"FAILED: {type(e).__name__}: {e}"
            print(k, out[k], flush=True)
            _store({k: out[k]})
    if "all" in which or "opamp" in which:
        vbn, vcn = json.loads((RES / "bias.json").read_text()) if (RES / "bias.json").exists() else (0.9387, 1.2701)
        for tag, load, vcm in (("noload", None, 0.4), ("50R", "50", 0.4), ("50mA", "15.75", 0.7875)):
            out[f"opamp_ac_{tag}"] = opamp_ac(vbn, vcn, tag, load, vcm); print(tag, out[f"opamp_ac_{tag}"], flush=True)
        for tag, load in (("noload", None), ("50R", "50"), ("50mA", "15.75")):
            out[f"opamp_dc_{tag}"] = opamp_dc(vbn, vcn, tag, load); print(tag, out[f"opamp_dc_{tag}"], flush=True)
        out["opamp_step"] = opamp_step(vbn, vcn); print(out["opamp_step"])
    _store(out)
    print("elapsed %.0f s" % (time.time() - t0))
