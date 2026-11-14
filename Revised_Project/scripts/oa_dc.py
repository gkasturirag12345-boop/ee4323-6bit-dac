import sim, opamp_net, numpy as np, sys
def sweep(load, vmax=2.0):
    ex=f"VDD VDD 0 3\nVBN VBN 0 0.880\nVCN VCN 0 1.275\nVIP VINP 0 0\nRfb VOUT VINN 1\n{load}\n.dc VIP 0 {vmax} 0.01\n"+sim.INCLUDES+".end"
    log,raw=sim.run('oa_dc', opamp_net.netlist(None, extra=ex)); d=sim.raw(raw)
    n=[v.name.lower() for v in d.variables]; g=lambda k: np.array([x.real for x in d.values[n.index(k)]])
    return g(n[0]), g('v(vout)'), g('i(vdd)'), log
for load in ["", "RL VOUT 0 50", "RL VOUT 0 15.75"]:
    vi,vo,idd,log=sweep(load)
    err=vo-vi; ok=np.abs(err)<1e-3
    print(f'load [{load}]  max |err| over 0-0.7875V: {np.abs(err[vi<=0.7875+1e-9]).max()*1e3:.3f} mV;  tracks(<1mV) up to {vi[ok][-1] if ok.any() else None:.2f} V;  min tracked {vi[ok][0]:.2f} V;  Iout at 0.7875V: {np.interp(0.7875,vi,vo)/ (float(load.split()[-1]) if load else 2e3)*1e3:.2f} mA; IDD@0.7875 {-np.interp(0.7875,vi,idd)*1e3:.3f} mA', sim.errors(log)[:1])
