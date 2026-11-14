"""Transistor sizing tables extracted from LTspice's own netlists of the block schematics."""
import re, json
from pathlib import Path
import asccheck, sys_asc

FUNC = {
 # regulator
 "M1": "Start-up current source (gate at GND, minimum W/L)", "M2": "Start-up turn-off sensor (gate = node A)",
 "M3": "Start-up injector into node A", "M4": "Start-up pull-down of VCPI", "M5": "Start-up pull-down of PG",
 "M9": "Diode load setting PG (mirror input)", "Mc": "Core-amp gain device driving PG",
 "M11": "PTAT/CTAT core mirror (branch A)", "M10": "Cascode, branch A", "M13": "PTAT/CTAT core mirror (branch B)", "M12": "Cascode, branch B",
 "Mt": "Core error-amp tail current", "Ma": "Core error-amp input (node A)", "Mb": "Core error-amp input (node B)",
 "Mn1": "Core error-amp mirror load (diode)", "Mn2": "Core error-amp mirror load (output AO)",
 "M16": "ICONST copy for VBN", "M15": "Cascode for VBN copy", "M14b": "VBN reference cascode (gate VCN)", "M14": "VBN reference device (low-voltage cascode diode)",
 "M20": "ICONST copy for VCN", "M19": "Cascode for VCN copy", "M17": "VCN diode (W/6 of M14)",
 "M8": "VCPI (PMOS cascode bias) diode", "M7": "VCPI sink cascode (VCN)", "M18": "VCPI sink (VBN)",
 "M22": "ICONST copy into R5 (VX)", "M21": "Cascode for VX copy",
 "M24a": "LDO-amp PMOS mirror (diode side)", "M24b": "LDO-amp mirror cascode", "M28a": "LDO-amp PMOS mirror (output side)", "M28b": "LDO-amp output cascode",
 "M25": "LDO-amp input (FB)", "M23": "LDO-amp input (VX)", "M26": "LDO-amp tail cascode (VCN)", "M27": "LDO-amp tail sink (VBN), 2 x ICONST",
 "M29": "LDO pass device (L = 0.6 um)",
 # op-amp
 "M49": "VBP1 bias (diode through M48)", "M48": "VBP1/VCP1 bias cascode", "M47": "Bias sink cascode (VCN)", "M46": "Bias sink (VBN)",
 "M30": "Tail current source (VBP1)", "M31": "Tail cascode (VCP1)", "M32": "Input pair, inverting (-)", "M33": "Input pair, non-inverting (+)",
 "M34": "Folding current sink (VBN)", "M41": "Folding current sink (VBN)", "M35": "NMOS cascode (VCN)", "M40": "NMOS cascode (VCN)",
 "M37": "PMOS mirror load (diode side)", "M38": "PMOS mirror load (output side)", "M36": "PMOS mirror cascode", "M39": "PMOS mirror cascode (output O1)",
 "M42": "Second-stage gain device", "M44": "Second-stage current source (VBP1)", "M43": "Second-stage cascode (VCP1)", "M45": "Source-follower output (L = 0.6 um)",
 # DAC
 "M53": "VBP2 bias (diode through M52), 8 units", "M52": "VCP2 bias cascode", "M51": "Bias sink cascode (VCN)", "M50": "Bias sink (VBN)",
}
CELLROLE = ["Current source (VBP2)", "Cascode (VCP2)", "Switch to IOUT (gate clk_bar)", "Switch to analog GND (gate clk)"]


def table(block):
    asc = sys_asc.LT / f"{block}.asc"
    net = asccheck.ltspice_netlist(asc)
    rows = []
    import dac_net
    cellmap = {n: (bit, CELLROLE[i]) for bit, m, names in dac_net.CELLS for i, n in enumerate(names)}
    for l in net.splitlines():
        t = l.split()
        if not t or t[0][0] not in "MQ":
            continue
        kv = dict(re.findall(r"(\w+)=(\S+)", l.lower()))
        if t[0][0] == "M":
            typ = "PMOS (pmos_PHL)" if " PHL " in f" {l} " else "NMOS (nmos_NWS)"
            def um(s):
                s = s.replace("u", "e-6"); v = float(s); return f"{v * 1e6:g}"
            name = t[0]
            func = FUNC.get(name) or (f"{cellmap[name][1]}, cell {cellmap[name][0]}" if name in cellmap else "")
            rows.append([name, typ, um(kv["w"]), um(kv["l"]), kv.get("m", "1"), func])
        else:
            rows.append([t[0], "NPN (npn_npn)", "-", "-", f"area {t[-1]}", "PTAT/CTAT core diode"])
    return rows


if __name__ == "__main__":
    out = {b: table(b) for b in ("Voltage_Regulator", "OpAmp", "DAC_Core")}
    Path("../results/sizing.json").write_text(json.dumps(out, indent=1))
    for b, r in out.items():
        print(b, len(r)); print(r[:3])
