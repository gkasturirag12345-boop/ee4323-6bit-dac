import sim, reg_net, sys, numpy as np
def tran(p=None, tstop=200e-6, load="RL VREF 0 3k"):
    net=reg_net.netlist(p, f"VUN VUN 0 PWL(0 0 20u 5)\n{load}\n.tran 0 {tstop} 0 50n startup\n"+sim.INCLUDES+".end")
    log,raw=sim.run('reg_tr',net)
    return log, sim.raw(raw) if raw else None
def last(d, name):
    names=[v.name.lower() for v in d.variables]; return np.array([x.real for x in d.values[names.index(name.lower())]])
if __name__=='__main__':
    log,d=tran()
    print(sim.errors(log)[:3])
    t=last(d,'time')
    for n in ['V(a)','V(b)','V(pg)','V(vref)','V(vx)','V(vbn)','V(su)','Ic(Qb)','Ic(Qa)']:
        y=last(d,n); print(n, [round(float(np.interp(tt,t,y)),6) for tt in (25e-6,50e-6,100e-6,199e-6)])
