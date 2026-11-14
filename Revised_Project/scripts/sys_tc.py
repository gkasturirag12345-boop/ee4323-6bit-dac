import sim, sys_tran, numpy as np, json, sys
from concurrent.futures import ThreadPoolExecutor
temps=[0,20,40,60,80]
def one(T):
    d,g,sched,log=sys_tran.run(T=20e-6, t0=300e-6, temp=T, codes=[0,31,63], name=f'sys_tc_{T}')
    vo=sys_tran.sample(g,sched,20e-6); vr=sys_tran.sample(g,sched,20e-6,node='v(vref)')
    return T, vo, vr
with ThreadPoolExecutor(5) as ex: res=sorted(ex.map(one,temps))
V=np.array([r[1] for r in res]); VR=np.array([r[2][0] for r in res])
for T,vo,vr in res: print(T, 'code0 %.4f mV code31 %.4f mV code63 %.4f mV  VREF %.5f'%(vo[0]*1e3,vo[1]*1e3,vo[2]*1e3,vr[0]))
i27=1
for k,c in [(1,'011111'),(2,'111111')]:
    v=V[:,k]; print(c, 'TC = %.2f ppm/C'%((v.max()-v.min())/np.interp(27,temps,v)/80*1e6))
print('VREF TC = %.2f ppm/C'%((VR.max()-VR.min())/np.interp(27,temps,VR)/80*1e6))
np.save('../results/tc_raw.npy', dict(temps=temps, V=V, VR=VR), allow_pickle=True)
