import sim, sys_net, dac_net, dac_static, numpy as np, json, sys
def run(temp=27, vun=5, preg=None, poa=None, pdac=None, load="", name='sys_static'):
    ex=f"VUN VUN 0 {vun}\n{load}\n.temp {temp}\n.param code=0\n"+dac_net.code_sources(amp="V(VREF)").replace("{V(VREF)*","{3*")+"\n.step param code 0 63 1\n.op\n"+sim.INCLUDES+".end"
    log,raw=sim.run(name, sys_net.netlist(preg,poa,pdac,extra=ex))
    d=sim.raw(raw); n=[v.name.lower() for v in d.variables]; g=lambda k: np.array([x.real for x in d.values[n.index(k)]])
    return g('v(vout)'), g('v(iout)'), g('v(vref)'), g('i(vun)'), log
if __name__=='__main__':
    vo,io,vref,iun,log=run()
    r=dac_static.lin(vo)
    print('VOUT0 %.4f mV FS %.3f mV LSB %.4f mV | DNL %.4f/%.4f INL %.4f/%.4f off %.3f gainerr %.3f LSB mono %s'%(vo[0]*1e3,vo[-1]*1e3,r['lsb']*1e3,r['dnl'].max(),r['dnl'].min(),r['inl'].max(),r['inl'].min(),r['offset_lsb'],r['gain_err_lsb'],r['mono']))
    print('VREF range %.5f-%.5f  I(VUN) %.3f-%.3f mA'%(vref.min(),vref.max(),-iun.max()*1e3,-iun.min()*1e3), sim.errors(log)[:1])
