import sim, dac_net, numpy as np, json, sys
def static(p=None, vdd_src="VDD VDD 0 3\nVBN VBN 0 0.880\nVCN VCN 0 1.275", node="v(iout)", net=None, name='dac_static'):
    ex=f"{vdd_src}\n.param code=0\n{dac_net.code_sources()}\n.step param code 0 63 1\n.op\n"+sim.INCLUDES+".end"
    log,raw=sim.run(name, net or dac_net.netlist(p, extra=ex))
    d=sim.raw(raw); n=[v.name.lower() for v in d.variables]
    vo=np.array([x.real for x in d.values[n.index(node)]])
    return vo, d, log
def lin(vo, lsb_ideal=12.5e-3):
    lsb=(vo[-1]-vo[0])/63
    dnl=np.diff(vo)/lsb-1; inl=(vo-vo[0])/lsb-np.arange(64)
    off=vo[0]/lsb_ideal; gain=((vo[-1]-vo[0])-63*lsb_ideal)/lsb_ideal
    return dict(lsb=lsb, dnl=dnl, inl=inl, offset_lsb=off, gain_err_lsb=gain, mono=bool((np.diff(vo)>0).all()))
if __name__=='__main__':
    p=json.loads(sys.argv[1]) if len(sys.argv)>1 else {}
    vo,d,log=static(p); r=lin(vo)
    print('V0 %.4f mV  VFS %.4f mV  LSB %.4f mV'%(vo[0]*1e3,vo[-1]*1e3,r['lsb']*1e3))
    print('DNL %.4f/%.4f  INL %.4f/%.4f  offset %.3f LSB gain err %.3f LSB mono %s'%(r['dnl'].max(),r['dnl'].min(),r['inl'].max(),r['inl'].min(),r['offset_lsb'],r['gain_err_lsb'],r['mono']))
    print('worst DNL codes', np.argsort(-abs(r['dnl']))[:4]+1, sim.errors(log)[:1])
