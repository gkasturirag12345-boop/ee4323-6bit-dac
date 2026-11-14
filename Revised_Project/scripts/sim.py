"""LTspice batch helpers for the EE4323 DAC project.

LTspice 26 on macOS runs inside a Wine wrapper; the app launcher's -b flag
returns immediately without simulating, so LTspice.exe is called through the
bundled wine binary instead. Simulations run in a space-free work directory
(SIMDIR) and the results are copied back into the project afterwards.
"""
import os, re, shutil, signal, subprocess, sys, threading
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SIMDIR = Path.home() / "dac_sim"
WINE = "/Applications/LTspice.app/Contents/SharedSupport/ltspice/bin/wine"
EXE = r"C:\Program Files\ADI\LTspice\LTspice.exe"
MODELS = ["EE4323_cmos.mos", "EE4323_bjt.lib"]
SYMS = ["nmos_NWS.asy", "pmos_PHL.asy", "npn_npn.asy", "R_ndiff.asy"]

sys.path.insert(0, str(Path.home() / "mcp-servers/ltspice-mcp/src"))
from ltspice_mcp.raw_parser import parse_raw_file  # noqa: E402

INCLUDES = ".include EE4323_cmos.mos\n.include EE4323_bjt.lib\n"


def _stage(extra=()):
    SIMDIR.mkdir(exist_ok=True)
    for f in MODELS + SYMS:
        src = PROJECT / "work" / f
        if src.exists():
            shutil.copy(src, SIMDIR / f)
    for f in extra:
        shutil.copy(f, SIMDIR / Path(f).name)


def winpath(p):
    return "Z:" + str(p).replace("/", "\\")


_SLOTS = threading.BoundedSemaphore(2)   # >2 concurrent LTspice instances in one Wine bottle were seen to deadlock


def _exec(cmd, target, timeout):
    """Run one LTspice command; on timeout kill the whole process group and any LTspice.exe left for this target."""
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


def run(name, text=None, path=None, extra=(), ascii=False, timeout=900):
    """Run a netlist (text) or an existing .cir/.asc (path). Returns (log_text, raw_path)."""
    _stage(extra)
    if text is not None:
        target = SIMDIR / f"{name}.cir"
        target.write_text(text)
    else:
        target = SIMDIR / Path(path).name
        if Path(path).resolve() != target.resolve():
            shutil.copy(path, target)
    for ext in (".log", ".raw", ".op.raw"):
        p = target.with_suffix(ext)
        if p.exists():
            p.unlink()
    if target.suffix == ".asc":
        # "-b" on a schematic hangs under Wine when several runs overlap; netlist first, then simulate the .net
        net = target.with_suffix(".net")
        if net.exists():
            net.unlink()
        _exec([WINE, "--bottle", "ltspice", "--no-gui", "--wait-children", EXE, "-netlist", winpath(target)], target, 300)
        if not net.exists():
            raise RuntimeError(f"LTspice did not netlist {target.name}")
        target = net
    cmd = [WINE, "--bottle", "ltspice", "--no-gui", "--wait-children", EXE, "-b", winpath(target)]
    if ascii:
        cmd.append("-ascii")
    _exec(cmd, target, timeout)
    log = target.with_suffix(".log")
    text_log = ""
    if log.exists():
        b = log.read_bytes()
        text_log = b.decode("utf-16le") if b[:2] in (b"\xff\xfe",) or b"\x00" in b[:40] else b.decode("latin-1")
    raw = target.with_suffix(".raw")
    return text_log, (raw if raw.exists() else None)


def meas(log):
    """Parse .meas results from a log -> dict name -> value (or list for .step runs)."""
    out = {}
    for m in re.finditer(r"^(\w+):\s.*?=\s*([-+0-9.eE]+)", log, re.M):
        out.setdefault(m.group(1).lower(), []).append(float(m.group(2)))
    # stepped measurements are printed as a table
    for block in re.finditer(r"Measurement: (\w+)\n\s+step\s+[^\n]*\n((?:\s+\d+\s+[^\n]+\n)+)", log):
        vals = [float(l.split()[1]) for l in block.group(2).strip().splitlines()]
        out[block.group(1).lower()] = vals
    return {k: (v[0] if len(v) == 1 else v) for k, v in out.items()}


def errors(log):
    bad = [l for l in log.splitlines() if re.search(r"error|singular|failed|floating|timestep too small", l, re.I)]
    return bad


def raw(path):
    return parse_raw_file(path)


def save(name, *files):
    """Copy simulation outputs into results/<name>/."""
    dst = PROJECT / "results" / name
    dst.mkdir(parents=True, exist_ok=True)
    for f in files:
        if f and Path(f).exists():
            shutil.copy(f, dst / Path(f).name)
    return dst
