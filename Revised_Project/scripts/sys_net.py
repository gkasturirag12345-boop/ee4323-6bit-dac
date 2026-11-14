"""Complete system netlist: one Vunregulated source, one ground; regulator output VREF is VDD for DAC + op-amp."""
import reg_net, opamp_net, dac_net

def netlist(preg=None, poa=None, pdac=None, extra=""):
    r = reg_net.netlist(preg)                       # uses VUN, VREF, VBN, VCN
    o = opamp_net.netlist(poa, vinp="IOUT", vinn="VOUT", vout="VOUT", vdd="VREF")
    d = dac_net.netlist(pdac, vdd="VREF", out="IOUT")
    return "* Complete 6-bit segmented DAC system\n" + r + o + d + extra
