import sim, reg_net, numpy as np, sys
from concurrent.futures import ThreadPoolExecutor
def one(T):
    net=reg_net.netlist(None, f"VUN VUN 0 PWL(0 0 20u 5)\nRL VREF 0 3k\n.temp {T}\n.tran 0 200u 0 50n startup\n"+sim.INCLUDES+".end")
    log,raw=sim.run(f'rt_{T}',net); d=sim.raw(raw); n=[v.name.lower() for v in d.variables]
    g=lambda k: np.array([x.real for x in d.values[n.index(k)]]); t=g('time')
    return T, {k: float(np.interp(199e-6,t,g(k))) for k in ['v(vref)','v(su)','v(a)','v(vx)']}, sim.errors(log)[:1]
with ThreadPoolExecutor(3) as ex:
    for r in ex.map(one,[0,27,80]): print(r)
