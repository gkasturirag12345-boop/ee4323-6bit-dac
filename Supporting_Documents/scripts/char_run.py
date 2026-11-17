"""Run the five characterisation analyses of 01_Characterisation.asc and save the raw curves (CSV)."""
import json, numpy as np
import char_asc, sim

OUT = sim.ROOT / "Simulation_Results" / "Characterisation"


def run(key):
    log, net, rawp = sim.run_asc(char_asc.draw(key).text_asc(), f"char_{key}")
    (OUT / f"{key}.log").write_text(log)
    err = sim.errors(log)
    d = sim.raw(rawp)
    return d, log, err


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for key in char_asc.RUNS:
        d, log, err = run(key)
        names = [v.name for v in d.variables]
        print(key, "steps", d.step_count, "points", d.points, "errors", err[:3])
        print("   vars:", names[:30])
        rows = []
        for st in range(d.step_count):
            g, _ = sim.getter(d, st if d.step_count > 1 else None)
            cols = {n: g(n) for n in names}
            for i in range(len(next(iter(cols.values())))):
                rows.append([st] + [float(cols[n][i]) for n in names])
        np.savetxt(OUT / f"{key}.csv", np.array(rows), delimiter=",", header="step," + ",".join(names), comments="")
        res[key] = dict(steps=d.step_count, points=d.points, errors=err)
    (OUT / "runs.json").write_text(json.dumps(res, indent=1))
