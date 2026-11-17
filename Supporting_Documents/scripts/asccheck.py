"""Verify a generated .asc against the intended netlist using LTspice's own netlister.

1. LTspice -netlist turns the .asc into a .net (this is exactly what LTspice simulates).
2. Both netlists are reduced to a partition of device pins into nets, and the partitions are compared
   (net names are ignored except ground '0' and the listed port names).
3. Floating pins (LTspice NC_xx nodes) and body ties are reported.
"""
import re, shutil, subprocess
from pathlib import Path
import sim

ORDER = {"M": ["D", "G", "S", "B"], "Q": ["C", "B", "E"], "R": ["A", "B"], "C": ["A", "B"],
         "V": ["P", "N"], "I": ["P", "N"], "E": ["P", "N", "CP", "CN"], "X": None}


def ltspice_netlist(asc, extra_files=()):
    sim._stage(extra_files)
    dst = sim.SIMDIR / Path(asc).name
    shutil.copy(asc, dst)
    net = dst.with_suffix(".net")
    if net.exists():
        net.unlink()
    sim._exec([sim.WINE, "--bottle", "ltspice", "--no-gui", "--wait-children", sim.EXE, "-netlist",
               sim.winpath(dst)], dst, 900)
    return net.read_text(errors="replace")


def parse(text, subckt=None):
    """Return {(inst, pin): node} for the top level (or a named .subckt) of a netlist."""
    out, cur = {}, None
    for line in text.splitlines():
        t = line.split()
        if not t or t[0].startswith("*"):
            continue
        k = t[0].lower()
        if k == ".subckt":
            cur = t[1]
            continue
        if k == ".ends":
            cur = None
            continue
        if k.startswith("."):
            continue
        if (cur or None) != subckt:
            continue
        kind = t[0][0].upper()
        pins = ORDER.get(kind)
        if pins is None:
            # subcircuit instance: nodes until the subckt name (last bare token before params)
            nodes = [x for x in t[1:] if "=" not in x][:-1]
            pins = [f"p{i}" for i in range(len(nodes))]
        else:
            nodes = t[1:1 + len(pins)]
        inst = t[0].replace("§", "")       # LTspice writes an instance "Ma" of a Q symbol as "Q§Ma"
        for p, n in zip(pins, nodes):
            out[(inst, p)] = n
    return out


def partition(conn, keep=("0",)):
    nets = {}
    for key, node in conn.items():
        nets.setdefault(node, set()).add(key)
    named = {n: frozenset(v) for n, v in nets.items() if n in keep}
    return {frozenset(v) for v in nets.values()}, named


def compare(intended_text, asc_net_text, subckt=None, keep=("0",)):
    a, b = parse(intended_text), parse(asc_net_text, subckt)
    report = []
    missing = set(a) - set(b)
    extra = set(b) - set(a)
    if missing:
        report.append(f"devices/pins missing in schematic: {sorted(missing)[:10]}")
    if extra:
        report.append(f"extra devices/pins in schematic: {sorted(extra)[:10]}")
    floating = sorted(k for k, n in b.items() if n.upper().startswith("NC_"))
    if floating:
        report.append(f"floating pins: {floating}")
    common = set(a) & set(b)
    pa, na = partition({k: a[k] for k in common}, keep)
    pb, nb = partition({k: b[k] for k in common}, keep)
    if pa != pb:
        only_a = sorted(sorted(s)[:4] for s in pa - pb)
        only_b = sorted(sorted(s)[:4] for s in pb - pa)
        report.append(f"net mismatch: intended-only {only_a[:6]} / schematic-only {only_b[:6]}")
    for n in keep:
        if na.get(n) != nb.get(n):
            report.append(f"net '{n}' differs")
    return report


def value_check(intended_text, asc_net_text, subckt=None):
    """Compare W/L/m (and resistor/capacitor values) per instance."""
    def vals(text, sc):
        out, cur = {}, None
        for line in text.splitlines():
            t = line.split()
            if not t:
                continue
            if t[0].lower() == ".subckt":
                cur = t[1]; continue
            if t[0].lower() == ".ends":
                cur = None; continue
            if cur != sc or t[0][0] in "*.":
                continue
            kv = dict(re.findall(r"(\w+)=(\S+)", line.lower()))
            if t[0][0].upper() == "M":
                out[t[0]] = (kv.get("w"), kv.get("l"), kv.get("m", "1"))
            elif t[0][0].upper() in "RC":
                out[t[0]] = (t[3].lower(),)
        return out
    def norm(v):
        def num(s):
            s = s.replace("µ", "u")
            m = re.match(r"([-+0-9.e]+)([a-z]*)", s)
            mult = {"": 1, "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3, "meg": 1e6}
            return float(m.group(1)) * mult.get(m.group(2), 1)
        return tuple(round(num(x), 15) if x else None for x in v)
    a, b = vals(intended_text, None), vals(asc_net_text, subckt)
    return [f"{k}: intended {a[k]} schematic {b.get(k)}" for k in a if k in b and norm(a[k]) != norm(b[k])]
