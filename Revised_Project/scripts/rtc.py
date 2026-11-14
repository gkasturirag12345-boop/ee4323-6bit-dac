import sys, json, sim, reg_net, numpy as np
def tc(p=None, load="RL VREF 0 3k", nodes=('V(vx)','V(vref)','Id(M11)','Ic(Qb)')):
    net=reg_net.netlist(p, f"VUN VUN 0 5\n{load}\n.dc temp 0 80 5\n"+sim.INCLUDES+".end")
    log,raw=sim.run('reg_tc',net); d=sim.raw(raw)
    names=[v.name.lower() for v in d.variables]; g=lambda n: np.array([x.real for x in d.values[names.index(n.lower())]])
    T=g(names[0]); out={}
    for n in nodes:
        y=g(n); i27=np.argmin(abs(T-25)); out[n]=(y[i27], (y.max()-y.min())/abs(y[i27])/80*1e6)
    return T,out,log
if __name__=='__main__':
    for r2 in [float(x) for x in sys.argv[1:]] or [43.4e3]:
        T,o,log=tc({'R2':r2,'R4':r2,'WEP':66e-6})
        print(int(r2), {k:(round(v[0],5) if 'V' in k else '%.3g'%v[0], round(v[1],1)) for k,v in o.items()}, sim.errors(log)[:1])
