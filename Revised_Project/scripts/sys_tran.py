import sim, sys_net, stim, dac_static, numpy as np, json, sys
def run(T=20e-6, t0=300e-6, temp=27, vun="PWL(0 0 20u 5)", preg=None, poa=None, pdac=None, load="", name='sys_tran', codes=range(64), maxstep=None, save=None):
    src, sched = stim.pwl_sources(t0, T, codes)
    tstop = t0 + T*len(list(codes))
    ms = maxstep or T/200
    ex=f"VUN VUN 0 {vun}\n{load}\n.temp {temp}\n{src}\n.tran 0 {tstop:g} 0 {ms:g}\n" + (save or "") + sim.INCLUDES + ".end"
    log,raw=sim.run(name, sys_net.netlist(preg,poa,pdac,extra=ex), timeout=3000)
    d=sim.raw(raw); n=[v.name.lower() for v in d.variables]
    g=lambda k: np.array([x.real for x in d.values[n.index(k.lower())]])
    return d, g, sched, log
def sample(g, sched, T, frac=0.95, node='v(vout)'):
    t=g('time'); y=g(node)
    return np.array([np.interp(ts+frac*T, t, y) for c,ts in sched])
if __name__=='__main__':
    d,g,sched,log=run()
    vo=sample(g,sched,20e-6); r=dac_static.lin(vo)
    print('VOUT0 %.4f mV FS %.3f mV LSB %.4f mV | DNL %.4f/%.4f INL %.4f/%.4f off %.3f gainerr %.3f LSB mono %s'%(vo[0]*1e3,vo[-1]*1e3,r['lsb']*1e3,r['dnl'].max(),r['dnl'].min(),r['inl'].max(),r['inl'].min(),r['offset_lsb'],r['gain_err_lsb'],r['mono']))
    vr=sample(g,sched,20e-6,node='v(vref)'); print('VREF %.5f..%.5f'%(vr.min(),vr.max()), sim.errors(log)[:2])
