"""Simulate an .asc from the LTspice folder (hierarchy staged alongside)."""
import sim, sys_asc, numpy as np
def run(asc, name=None, timeout=3000):
    LT=sys_asc.LT
    extra=[str(p) for p in LT.glob('*.as[cy]')]
    log,raw=sim.run(name or asc.stem, path=asc, extra=extra, timeout=timeout)
    d=sim.raw(raw) if raw else None
    if d is None: return log, None, None
    n=[v.name.lower() for v in d.variables]
    g=lambda k: np.array([x.real for x in d.values[n.index(k.lower())]])
    return log, d, g
