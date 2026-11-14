import sim, numpy as np
r={}
for T in (0,80):
    d=sim.raw(f'~/dac_sim/sys_tc_{T}.raw'); n=[v.name for v in d.variables]
    t=np.array([x.real for x in d.values[0]])
    at=lambda name, tt=355e-6: float(np.interp(tt,t,[x.real for x in d.values[n.index(name)]]))
    r[T]={k:at(k) for k in ['Id(M11)','Id(M14)','Id(M50)','Id(M53)','Id(M83)','I(R5)','V(n14)','V(n51)','V(s_d1)','V(n53)','V(vbp2)','V(vcp2)','V(iout)']}
for k in r[0]:
    print(k, '%.5g -> %.5g'%(r[0][k],r[80][k]))
print('M50/M14', r[0]['Id(M50)']/r[0]['Id(M14)'], r[80]['Id(M50)']/r[80]['Id(M14)'])
print('M83/M53', r[0]['Id(M83)']/r[0]['Id(M53)'], r[80]['Id(M83)']/r[80]['Id(M53)'])
print('M14/R5', r[0]['Id(M14)']/r[0]['I(R5)'], r[80]['Id(M14)']/r[80]['I(R5)'])
