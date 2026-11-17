"""Netlist the committed schematics 02-04 with LTspice and compare them with their intended netlists.

01_Characterisation has no intended netlist (it is a set of device test benches), so it is not checked here.
Needs LTspice and the course models in the repository root (see README). Exit code 1 on any mismatch.
"""
import sys

import opamp03_asc, reg02_asc, reg_design, sim, sys04_asc, verify

CHECKS = [
    ("02_VREF_Regulator", lambda: reg_design.netlist() + reg02_asc.INTENDED_EXTRA),
    ("03_Folded_Cascode_OpAmp", lambda: opamp03_asc.intended()),
    # the committed 04 is sys04_asc.draw() with its defaults: codes 0..63, t0 = 200 us, T = 20 us, 3.62 V, 5 ns edges
    ("04_Complete_6Bit_DAC", lambda: sys04_asc.intended(stim=sys04_asc.sys_design.pwl_sources(
        list(range(64)), 200e-6, 20e-6, 3.62, 5e-9))),
]

if __name__ == "__main__":
    failed = 0
    for name, intended in CHECKS:
        rep, _, bodies = verify.verify((sim.ROOT / f"{name}.asc").read_text(), intended(), f"verify_{name}")
        print(f"{name}: {len(bodies)} transistors, " + ("OK" if not rep else "MISMATCH"))
        for line in rep:
            print("   ", line)
        failed += bool(rep)
    sys.exit(1 if failed else 0)
