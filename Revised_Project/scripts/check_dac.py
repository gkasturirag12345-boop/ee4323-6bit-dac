import dac_asc, dac_net, asccheck, sys
asc='../blocks/DAC_Core.asc'
dac_asc.draw(asc)
net=asccheck.ltspice_netlist(asc)
intended=dac_net.netlist()
print('\n'.join(asccheck.compare(intended, net, keep=("0","VDD","VBN","VCN","IOUT"))) or 'CONNECTIVITY OK')
print('\n'.join(asccheck.value_check(intended, net)) or 'VALUES OK')
open('../work/DAC_Core_ltspice.net','w').write(net)
