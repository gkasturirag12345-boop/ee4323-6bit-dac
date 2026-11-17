"""Characterise 03_Folded_Cascode_OpAmp.asc (runs start from the schematic; probes are added to LTspice's netlist of it)."""
import json, numpy as np
import sim, opamp03_asc as o

OUT = sim.ROOT / "Simulation_Results" / "OpAmp"
LSB = 12.5e-3
RES = {}


def run(key, active, **kw):
    log, net, rawp = sim.run_asc(o.draw_file(active, **kw).text_asc(), f"oa03_{key}")
    (OUT / f"{key}.log").write_text(log)
    if sim.errors(log):
        print(key, "ERRORS:", sim.errors(log)[:3])
    return sim.raw(rawp), net


def save(key, cols):
    np.savetxt(OUT / f"{key}.csv", np.column_stack([np.asarray(v, float) for v in cols.values()]), delimiter=",",
               header=",".join(cols), comments="")


def tian(net_text, name):
    """Loop gain of the follower: break the M33 gate (node VOUT) with Vi (series) + Ii (shunt)."""
    lines = []
    for l in net_text.splitlines():
        t = l.split()
        if t and t[0] == "M33":
            t[2] = "XBRK"; l = " ".join(t)
        if l.strip().lower().startswith((".tran", ".dc", ".op", ".ac", ".backanno", ".end")):
            continue
        lines.append(l)
    out = []
    for vi, ii in ((1, 0), (0, 1)):
        log, rp = sim.run_net("\n".join(lines) + f"\nVi XBRK VOUT 0 AC {vi}\nIi 0 XBRK 0 AC {ii}\n.ac dec 40 1 1G\n.end\n", name)
        d = sim.raw(rp); g, n = sim.getter(d, cplx=True)
        out.append((g("frequency").real, g("v(xbrk)"), g("i(vi)")))
    f, V1, I1 = out[0]; _, V2, I2 = out[1]
    T = -1 / (1 - 1 / (2 * (I1 * V2 - V1 * I2) + V1 + I2))
    mag, ang = 20 * np.log10(abs(T)), np.angle(T, deg=True)
    k = np.where(mag < 0)[0][0]
    pm = (180 + ang[k]) if ang[k] < 0 else (ang[k] - 180)
    return f, mag, ang, dict(A0_dB=float(mag[0]), UGF_MHz=float(f[k] / 1e6), PM_deg=float(pm), phase_at_1Hz=float(ang[0]))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # operating point / quiescent current (no external load), VIN = 0.4 V
    d, net = run("op", "op")
    g, n = sim.getter(d); v = lambda k: float(g(k)[0])
    RES["op"] = dict(VIN=0.4, VOUT=v("v(vout)"), offset_mV=(v("v(vout)") - 0.4) * 1e3, TAIL=v("v(tail)"), F1=v("v(f1)"), F2=v("v(f2)"),
                     LFT=v("v(lft)"), O1=v("v(o1)"), G45=v("v(g45)"), VBP1=v("v(vbp1)"), VCP1=v("v(vcp1)"),
                     I_VDD_uA=-v("i(vdd)") * 1e6, I_tail_uA=-v("id(m30)") * 1e6, I_M34_uA=v("id(m34)") * 1e6,
                     I_M42_uA=v("id(m42)") * 1e6, I_M45_uA=v("id(m45)") * 1e6, I_ROUT_uA=v("i(rout)") * 1e6)
    (OUT / "op_netlist_from_schematic.net").write_text(net)
    # polarity check: negative feedback -> VOUT follows VIN at several levels (op points from the schematic)
    RES["polarity"] = {}
    for vin in ("0.05", "0.4", "0.79"):
        d, _ = run(f"op_vin{vin}", "op", vin=vin); g, n = sim.getter(d)
        RES["polarity"][vin] = float(g("v(vout)")[0])
    # counter-check: feedback deliberately to M32 and input on M33 (swapped) -> expected to latch (positive feedback)
    sw = []
    for l in net.splitlines():
        t = l.split()
        if t and t[0] == "M32":
            t[2] = "VOUT"; l = " ".join(t)
        elif t and t[0] == "M33":
            t[2] = "VINP"; l = " ".join(t)
        if l.strip().lower().startswith((".backanno", ".end")):
            continue
        sw.append(l)
    log, rp = sim.run_net("\n".join(sw) + "\n.end\n", "oa03_swapped")
    d = sim.raw(rp); g, n = sim.getter(d)
    RES["polarity"]["swapped_inputs_VOUT_at_VIN_0.4"] = float(g("v(vout)")[0])
    # DC transfer (unity follower)
    RES["dc"] = {}
    for tag, load, il in (("noload", None, None), ("50R", "50", None), ("15R75_50mA", "15.75", None), ("sink50mA", None, "50m")):
        d, _ = run(f"dc_{tag}", "dc", load=load, il=il); g, n = sim.getter(d)
        vi, vo, ivdd = g("v(vinp)"), g("v(vout)"), -g("i(vdd)")
        save(f"dc_{tag}", {"VIN": vi, "VOUT": vo, "I_VDD": ivdd})
        e = vo - vi; fs = vi <= 0.7875 + 1e-9; ok = np.abs(e) < LSB / 2          # tracking: |VOUT - VIN| < 1/2 LSB
        RES["dc"][tag] = dict(max_err_0_to_FS_mV=float(np.abs(e[fs]).max() * 1e3), track_range_V=[float(vi[ok].min()), float(vi[ok].max())],
                              VOUT_at_VIN0_mV=float(vo[0] * 1e3), I_VDD_at_FS_mA=float(np.interp(0.7875, vi, ivdd) * 1e3),
                              I_load_at_FS_mA=float(0.7875 / float(load) * 1e3) if load else (50.0 if il else 0.0))
    # step response 0.1 -> 0.7 V (10 ns edges)
    RES["step"] = {}
    for tag, load in (("noload", None), ("50R", "50")):
        d, _ = run(f"step_{tag}", "step", vin="PULSE(0.1 0.7 5u 10n 10n 10u 20u)", load=load); g, n = sim.getter(d)
        t, vo = g("time"), g("v(vout)"); save(f"step_{tag}", {"time": t, "VOUT": vo})
        r = {}
        for lab, t0, a, b in (("rise", 5e-6, 0.1, 0.7), ("fall", 15e-6, 0.7, 0.1)):
            m = (t > t0) & (t < t0 + 10e-6); tt, y = t[m], vo[m]; fin = y[-1]
            bad = np.where(np.abs(y - fin) > LSB / 2)[0]
            lo, hi = a + 0.1 * (b - a), a + 0.9 * (b - a)
            i10 = np.argmax((y - lo) * np.sign(b - a) > 0); i90 = np.argmax((y - hi) * np.sign(b - a) > 0)
            r[lab] = dict(final=float(fin), settle_halfLSB_ns=float((tt[bad[-1]] - t0) * 1e9) if len(bad) else 0.0,
                          slew_V_per_us=float(0.48 / max(tt[i90] - tt[i10], 1e-12) / 1e6),
                          overshoot_mV=float((y.max() - fin) * 1e3 if b > a else (fin - y.min()) * 1e3),
                          pp_last_2us_mV=float(np.ptp(y[tt > tt[-1] - 2e-6]) * 1e3))
        RES["step"][tag] = r
    # loop gain (= open-loop gain for the follower, beta = 1)
    RES["loop"] = {}
    for vin in ("0.05", "0.4", "0.79"):
        for tag, load in (("noload", None), ("50R", "50")):
            d, net_l = run(f"loopop_{vin}_{tag}", "op", vin=vin, load=load)
            f, mag, ang, r = tian(net_l, "oa03_tian")
            save(f"loop_{vin}_{tag}", {"f": f, "mag_dB": mag, "phase_deg": ang}); RES["loop"][f"{vin}_{tag}"] = r
    (OUT / "summary.json").write_text(json.dumps(RES, indent=1))
    print(json.dumps(RES, indent=1))


if __name__ == "__main__":
    main()
