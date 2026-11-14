import tb, asccheck, sys_asc
asc,_=tb.system_tb('TB_Power',[0,63],50e-6,ammeters=True)
net=asccheck.ltspice_netlist(asc, extra_files=[str(p) for p in sys_asc.LT.glob('*.as[cy]')])
for l in net.splitlines():
    if l[:2] in ('X§','VI') or l.startswith('VI'): print(l[:120])
print('NC', [l for l in net.splitlines() if 'NC_' in l])
