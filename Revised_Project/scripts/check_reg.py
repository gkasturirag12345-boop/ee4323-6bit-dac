import reg_asc, reg_net, asccheck, ascrender
asc='../blocks/Voltage_Regulator.asc'
reg_asc.draw(asc)
net=asccheck.ltspice_netlist(asc)
intended=reg_net.netlist()
print('\n'.join(asccheck.compare(intended, net, keep=("0","VUN","VREF","VBN","VCN"))) or 'CONNECTIVITY OK')
print('\n'.join(asccheck.value_check(intended, net)) or 'VALUES OK')
print([l for l in net.splitlines() if l.startswith('Q')])
open('../work/Voltage_Regulator_ltspice.net','w').write(net)
ascrender.render(asc,'../work/Voltage_Regulator.png', dpi=110)
