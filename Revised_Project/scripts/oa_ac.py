import sys, json, sim, opamp_net, numpy as np
VBN, VCN = 0.880, 1.275
def ac(p=None, vcm=0.4, load="", cl=0):
    ex=f"""VDD VDD 0 3
VBN VBN 0 {VBN}
VCN VCN 0 {VCN}
VIP VINP 0 {vcm} AC 1
Lfb VOUT VINN 1G
Cfb VINN 0 1
{load}
{"CLD VOUT 0 %g"%cl if cl else ""}
.ac dec 50 1 1G
"""+sim.INCLUDES+".end"
    log,raw=sim.run('oa_ac', opamp_net.netlist(p, extra=ex)); d=sim.raw(raw)
    names=[v.name.lower() for v in d.variables]
    f=np.array([x.real for x in d.values[0]]); h=np.array(d.values[names.index('v(vout)')])
    g=20*np.log10(abs(h)); ph=np.unwrap(np.angle(h))*180/np.pi
    i=np.where(g<0)[0][0]; pm=180+ph[i]
    return dict(A0=g[0], UGB=f[i], PM=pm, ph0=ph[0]), log
if __name__=='__main__':
    p=json.loads(sys.argv[1]) if len(sys.argv)>1 else {}
    r,log=ac(p); print({k:round(float(v),2) for k,v in r.items()}, sim.errors(log)[:2])
