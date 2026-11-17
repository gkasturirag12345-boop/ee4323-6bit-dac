import json, sim, reg02_run, reg02_asc, reg_design
p = sim.ROOT / "Simulation_Results/VREF/loop_vs_temp_and_M1_study.json"; out = {"loop_vs_temp": {}, "m1_study": {}}
for T in (0, 27, 80):
    for vun in ("5", "4.5"):
        net = sim.netlist(reg02_asc.draw_file("op", vun=vun, temp=T).text_asc(), "lt_t")
        _, _, _, rc = reg02_run.tian(net, "Mc", "G", "lt_c"); _, _, _, rl = reg02_run.tian(net, "M25", "FB", "lt_l")
        out["loop_vs_temp"][f"{T}C_{vun}V"] = dict(core_PM=rc["PM_deg"], core_T0_dB=rc["T0_dB"], LDO_PM=rl["PM_deg"], LDO_T0_dB=rl["T0_dB"])
old = dict(reg_design.DEF)
for L1 in (30e-6, 60e-6, 120e-6, 180e-6, 220e-6, 260e-6, 300e-6, 500e-6):
    reg_design.DEF["L1"] = L1; row = {}
    for T in (0, 27, 80):
        s = reg02_asc.draw_file("startup", vun="PWL(0 0 20u 4.5)", temp=T)
        log, net, rp = sim.run_asc(s.text_asc(), "m1s"); d = sim.raw(rp); g, n = sim.getter(d); igm = float(g("id(m7)")[-1])
        row[f"{T}C"] = dict(VREF=float(g("v(vref)")[-1]), IPTAT_uA=float(g("ic(ma)")[-1] * 1e6), I_M1_uA=float(-g("id(m1)")[-1] * 1e6),
                            I_Gm_uA=igm * 1e6, IGm_x_R2_V=igm * reg_design.DEF["R2"], V_G=float(g("v(g)")[-1]))
    out["m1_study"][f"L1={L1*1e6:.0f}u"] = row
    print(L1, {k: (round(v['VREF'], 3), round(v['IGm_x_R2_V'] / v['V_G'], 2)) for k, v in row.items()}, flush=True)
reg_design.DEF.clear(); reg_design.DEF.update(old)
p.write_text(json.dumps(out, indent=1)); print("study saved")
