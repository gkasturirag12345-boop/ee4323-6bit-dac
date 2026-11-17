"""LTspice batch helpers for the EE4323 DAC submission.

LTspice 26 on macOS runs inside a Wine wrapper; LTspice.exe is called through the bundled wine binary.
Batch mode ("-b") on a schematic hangs under Wine, so a schematic is first netlisted by LTspice itself
("-netlist") and the resulting .net is simulated. Runs happen in a space-free work directory (SIMDIR);
the four submission schematics in the project root are never modified by a run.
"""
import os, re, shutil, signal, subprocess, sys, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # repository root (holds the four .asc files)
# Machine-specific settings; override with environment variables.
SIMDIR = Path(os.environ.get("DAC_SIMDIR", Path.home() / "dac_sim_final"))
WINE = os.environ.get("LTSPICE_WINE", "/Applications/LTspice.app/Contents/SharedSupport/ltspice/bin/wine")
EXE = r"C:\Program Files\ADI\LTspice\LTspice.exe"
# EE4323_cmos.mos / EE4323_bjt.lib are course-provided models: not in the repository, place them in ROOT.
SUPPORT = ["EE4323_cmos.mos", "EE4323_bjt.lib", "nmos_NWS.asy", "pmos_PHL.asy", "npn_npn.asy", "R_ndiff.asy"]
LTSPICE_MCP_SRC = Path(os.environ.get("LTSPICE_MCP_SRC", Path.home() / "mcp-servers/ltspice-mcp/src"))


def parse_raw_file(path):
    """LTspice .raw reader from the ltspice-mcp package, imported only when a simulation result is read."""
    sys.path.insert(0, str(LTSPICE_MCP_SRC))
    from ltspice_mcp.raw_parser import parse_raw_file as _parse
    return _parse(path)

_SLOTS = threading.BoundedSemaphore(2)   # more concurrent LTspice instances in one Wine bottle were seen to deadlock


def _stage():
    SIMDIR.mkdir(exist_ok=True)
    for f in SUPPORT:
        shutil.copy(ROOT / f, SIMDIR / f)


def winpath(p):
    return "Z:" + str(p).replace("/", "\\")


def _exec(cmd, target, timeout):
    """Run one LTspice command; on timeout kill the process group and any LTspice.exe left for this target."""
    with _SLOTS:
        p = subprocess.Popen(cmd, cwd=SIMDIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            subprocess.run(["pkill", "-9", "-f", f"LTspice.exe.*{Path(target).name}"])
            raise


def lt(flag, target, timeout):
    _exec([WINE, "--bottle", "ltspice", "--no-gui", "--wait-children", EXE, flag, winpath(target)], target, timeout)


def netlist(asc_text, name, timeout=300):
    """Write asc_text to SIMDIR/name.asc, netlist it with LTspice and return the .net text."""
    _stage()
    asc = SIMDIR / f"{name}.asc"
    asc.write_text(asc_text)
    net = asc.with_suffix(".net")
    if net.exists():
        net.unlink()
    lt("-netlist", asc, timeout)
    if not net.exists():
        raise RuntimeError(f"LTspice did not netlist {asc.name}")
    return net.read_text(errors="replace")


def run_asc(asc_text, name, timeout=1800):
    """Netlist a schematic text with LTspice, simulate the netlist, return (log, net_text, raw_path)."""
    net_text = netlist(asc_text, name)
    net = SIMDIR / f"{name}.net"
    for ext in (".log", ".raw", ".op.raw"):
        p = net.with_suffix(ext)
        if p.exists():
            p.unlink()
    lt("-b", net, timeout)
    return read_log(net.with_suffix(".log")), net_text, (net.with_suffix(".raw") if net.with_suffix(".raw").exists() else None)


def run_net(text, name, timeout=1800):
    """Simulate a plain netlist (design-tuning runs). Returns (log, raw_path)."""
    _stage()
    cir = SIMDIR / f"{name}.cir"
    cir.write_text(text)
    for ext in (".log", ".raw", ".op.raw"):
        p = cir.with_suffix(ext)
        if p.exists():
            p.unlink()
    lt("-b", cir, timeout)
    return read_log(cir.with_suffix(".log")), (cir.with_suffix(".raw") if cir.with_suffix(".raw").exists() else None)


def read_log(path):
    if not Path(path).exists():
        return ""
    b = Path(path).read_bytes()
    return b.decode("utf-16le") if b"\x00" in b[:40] else b.decode("latin-1")


def errors(log):
    return [l for l in log.splitlines() if re.search(r"error|singular|failed|floating|timestep too small", l, re.I)
            and not re.search(r"gmin stepping|source stepping|succeeded", l, re.I)]


def raw(path):
    return parse_raw_file(path)


def getter(d, step=None, cplx=False):
    """g(name) -> numpy array of a vector (one step of a stepped run if step is given)."""
    import numpy as np
    names = [v.name.lower() for v in d.variables]
    def g(n):
        vals = d.values[names.index(n.lower())]
        if step is not None:
            st = d.steps[step]
            vals = vals[st.start:st.end]
        return np.array(vals) if cplx else np.array([x.real for x in vals])
    return g, names
