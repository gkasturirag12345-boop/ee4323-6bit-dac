import sys, json, sim, reg_net, numpy as np
p=json.loads(sys.argv[1]) if len(sys.argv)>1 else {}
load="RL VREF 0 3k\nIL VREF 0 PWL(0 0 300u 0 300.1u 50m 400u 50m 400.1u 0)"
net=reg_net.netlist(p, f"VUN VUN 0 PWL(0 0 20u 5)\n{load}\n.tran 0 500u 0 20n startup\n"+sim.INCLUDES+".end")
log,raw=sim.run('reg_step',net); d=sim.raw(raw)
names=[v.name.lower() for v in d.variables]; g=lambda n: np.array([x.real for x in d.values[names.index(n.lower())]])
t=g('time'); v=g('V(vref)'); e=g('V(eout)')
for a,b in [(250e-6,300e-6),(300e-6,320e-6),(380e-6,400e-6),(400e-6,420e-6),(480e-6,500e-6)]:
    m=(t>=a)&(t<b); print(f'{a*1e6:.0f}-{b*1e6:.0f}us VREF min {v[m].min():.4f} max {v[m].max():.4f} end {v[m][-1]:.4f}  EOUT end {e[m][-1]:.3f}')
print(sim.errors(log)[:2])
