import sim, reg_net, sys
def op(p=None, load="RL VREF 0 3k", vun=5, temp=27):
    net=reg_net.netlist(p, f"VUN VUN 0 {vun}\n{load}\n.temp {temp}\n.op\n"+sim.INCLUDES+".end")
    log,raw=sim.run('reg_op',net)
    e=sim.errors(log)
    d=sim.raw(raw) if raw else None
    return log,d,e
if __name__=='__main__':
    log,d,e=op()
    print('ERR',e[:5])
    if d:
        for v in d.variables:
            if v.name.startswith('V('): print(v.name, round(d.values[d.variables.index(v)][0].real,4))
        for nm in ['I(Vun)','Id(M11)','Id(M13)','Ic(Qb)','Ic(Qa)','Id(M29)','Id(M9)','Id(M1)','Id(M2)']:
            names=[v.name for v in d.variables]
            if nm in names: print(nm, d.values[names.index(nm)][0].real)
