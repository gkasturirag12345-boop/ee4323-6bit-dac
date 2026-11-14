import opamp_asc, opamp_net, asccheck, ascrender
asc='../blocks/OpAmp.asc'
opamp_asc.draw(asc)
net=asccheck.ltspice_netlist(asc)
intended=opamp_net.netlist()
print('\n'.join(asccheck.compare(intended, net, keep=("0","VDD","VBN","VCN","VINP","VINN","VOUT"))) or 'CONNECTIVITY OK')
print('\n'.join(asccheck.value_check(intended, net)) or 'VALUES OK')
open('../work/OpAmp_ltspice.net','w').write(net)
ascrender.render(asc,'../work/OpAmp.png', dpi=130)
