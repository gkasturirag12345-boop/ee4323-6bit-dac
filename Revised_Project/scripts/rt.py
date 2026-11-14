import sys, json, reg_tr, numpy as np, sim
p=json.loads(sys.argv[1]) if len(sys.argv)>1 else {}
load=sys.argv[2] if len(sys.argv)>2 else "RL VREF 0 3k"
log,d=reg_tr.tran(p, load=load)
print(sim.errors(log)[:3])
t=reg_tr.last(d,'time')
for n in ['V(a)','V(b)','V(pg)','V(vbn)','V(vcn)','V(vcpi)','V(su)','V(n14)','Id(M14)','Id(M17)','Id(M11)','V(ao)','V(tl)']:
    try: y=reg_tr.last(d,n); print(n, [float('%.5g'%np.interp(tt,t,y)) for tt in (25e-6,50e-6,100e-6,199e-6)])
    except ValueError: pass
