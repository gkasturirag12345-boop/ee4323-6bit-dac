"""Generate every block schematic into Revised_Project/LTspice (with symbols and models) and verify each one."""
import shutil, sys
from pathlib import Path
import dac_asc, opamp_asc, reg_asc, sys_asc, asccheck, dac_net, opamp_net, reg_net
LT = sys_asc.LT; LT.mkdir(exist_ok=True)
W = Path(__file__).resolve().parents[1] / "work"
for f in ["nmos_NWS.asy", "pmos_PHL.asy", "npn_npn.asy", "pnp_pnp1.asy", "R_ndiff.asy", "EE4323_cmos.mos", "EE4323_bjt.lib"]:
    src = W / f if (W / f).exists() else Path.home() / "Documents/LTspice/EE4323_library" / f
    shutil.copy(src, LT / f)
sys_asc.symbols()
ok = True
for mod, net, name, keep in [(dac_asc, dac_net, "DAC_Core", ("0", "VDD", "VBN", "VCN", "IOUT")),
                             (opamp_asc, opamp_net, "OpAmp", ("0", "VDD", "VBN", "VCN", "VINP", "VINN", "VOUT")),
                             (reg_asc, reg_net, "Voltage_Regulator", ("0", "VUN", "VREF", "VBN", "VCN"))]:
    asc = LT / f"{name}.asc"
    mod.draw(asc)
    n = asccheck.ltspice_netlist(asc)
    rep = asccheck.compare(net.netlist(), n, keep=keep) + asccheck.value_check(net.netlist(), n)
    print(name, "OK" if not rep else rep); ok &= not rep
sys.exit(0 if ok else 1)
