import sys_asc, asccheck, sim, stim, ascrender
from pathlib import Path
LT=sys_asc.LT
src,_=stim.pwl_sources(300e-6, 20e-6)
clocks={l.split()[1]: l.split(' ',3)[3] for l in src.splitlines()}
sys_asc.system(LT/'DAC_System.asc', clocks=clocks, directives=[".tran 0 1.58m 0 100n"])
extra=[str(p) for p in LT.glob('*.as[cy]')]
net=asccheck.ltspice_netlist(LT/'DAC_System.asc', extra_files=extra)
open('../work/DAC_System_ltspice.net','w').write(net)
top=[l for l in net.splitlines() if l[:1] in 'XV' ]
for l in top[:6]: print(l[:160])
print('subckts:', [l.split()[1:] for l in net.splitlines() if l.lower().startswith('.subckt')])
print('NC nodes:', [l for l in net.splitlines() if 'NC_' in l][:5])
ascrender.render(LT/'DAC_System.asc','../work/DAC_System.png', dpi=110, extra_dirs=[LT])
