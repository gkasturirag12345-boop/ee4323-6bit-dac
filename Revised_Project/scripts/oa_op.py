import sim, opamp_net, json, sys, re
p=json.loads(sys.argv[1]) if len(sys.argv)>1 else {}
vcm=float(sys.argv[2]) if len(sys.argv)>2 else 0.4
load=sys.argv[3] if len(sys.argv)>3 else ""
ex=f"VDD VDD 0 3\nVBN VBN 0 0.880\nVCN VCN 0 1.275\nVIP VINP 0 {vcm}\nRfb VOUT VINN 1\n{load}\n.op\n"+sim.INCLUDES+".end"
log,raw=sim.run('oa_op', opamp_net.netlist(p, extra=ex))
d=sim.raw(raw); V={v.name:d.values[i][0].real for i,v in enumerate(d.variables)}
print({k[2:-1]:round(v,3) for k,v in V.items() if k.startswith('V(')})
print({k:'%.3g'%v for k,v in V.items() if k.startswith('Id(')})
print(sim.errors(log)[:1])
