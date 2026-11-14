"""Logic stimuli: counter sweep 000000 -> 111111 as PWL sources (thermometer D1-D3, binary B3-B6) + complements."""
BITS = ["D1", "D2", "D3", "B3", "B4", "B5", "B6"]

def bitval(code, b):
    return {"D1": code >= 16, "D2": code >= 32, "D3": code >= 48,
            "B3": (code >> 3) & 1, "B4": (code >> 2) & 1, "B5": (code >> 1) & 1, "B6": code & 1}[b]

def pwl_sources(t0, T, codes=range(64), vhi=3.0, tr=1e-9, extra_codes_after=0):
    """Each code is held for T seconds starting at t0. Returns (netlist text, list of (code, t_start))."""
    seq = list(codes)
    out, sched = [], [(c, t0 + i * T) for i, c in enumerate(seq)]
    for b in BITS:
        for name, inv in ((f"clk_{b}", False), (f"clk_bar_{b}", True)):
            pts = [(0.0, (1 - bitval(seq[0], b)) * vhi if inv else bitval(seq[0], b) * vhi)]
            prev = pts[0][1]
            for c, ts in sched[1:]:
                v = (1 - bitval(c, b)) * vhi if inv else bitval(c, b) * vhi
                if v != prev:
                    pts += [(ts, prev), (ts + tr, v)]
                    prev = v
            body = " ".join(f"{t:.10g} {v:g}" for t, v in pts)
            out.append(f"V_{name} {name} 0 PWL({body})")
    return "\n".join(out), sched
