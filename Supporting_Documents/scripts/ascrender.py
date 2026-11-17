"""Render an LTspice .asc to PNG/PDF using the real .asy symbol graphics (for review and report figures)."""
import math, re
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc

SYMDIRS = [Path(__file__).resolve().parents[1] / "work",
           Path.home() / "Library/Application Support/LTspice/Bottles/ltspice/drive_c/users/crossover/AppData/Local/LTspice/lib/sym"]
XF = {"R0": lambda x, y: (x, y), "M0": lambda x, y: (-x, y), "R90": lambda x, y: (-y, x),
      "R180": lambda x, y: (-x, -y), "R270": lambda x, y: (y, -x), "M180": lambda x, y: (x, -y)}


def load_sym(name, extra_dirs=()):
    for d in list(extra_dirs) + SYMDIRS:
        p = Path(d) / f"{name.split(chr(92))[-1]}.asy"
        if p.exists():
            return p.read_text(errors="replace").splitlines()
    return []


def render(asc, out, title=None, extra_dirs=(), scale=1.0, dpi=200):
    asc = Path(asc)
    lines = asc.read_text(errors="replace").splitlines()
    wires, flags, syms, texts = [], [], [], []
    cur = None
    for l in lines:
        t = l.split()
        if not t:
            continue
        if t[0] == "WIRE":
            wires.append(tuple(map(int, t[1:5])))
        elif t[0] == "FLAG":
            flags.append((int(t[1]), int(t[2]), t[3]))
        elif t[0] == "SYMBOL":
            cur = dict(name=t[1], x=int(t[2]), y=int(t[3]), o=t[4], attrs={})
            syms.append(cur)
        elif t[0] == "SYMATTR" and cur is not None:
            cur["attrs"][t[1]] = " ".join(t[2:])
        elif t[0] == "TEXT":
            texts.append((int(t[1]), int(t[2]), " ".join(t[5:])))
    xs = [w[0] for w in wires] + [w[2] for w in wires] + [s["x"] for s in syms]
    ys = [w[1] for w in wires] + [w[3] for w in wires] + [s["y"] for s in syms]
    x0, x1, y0, y1 = min(xs) - 160, max(xs) + 220, min(ys) - 80, max(ys) + 120
    W, H = (x1 - x0) / 220 * scale, (y1 - y0) / 220 * scale
    fig, ax = plt.subplots(figsize=(W, H))
    ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.set_aspect("equal"); ax.axis("off")
    lw = 1.0
    # wires and junction dots (an endpoint shared by >= 3 segment ends, or a T onto a segment)
    ends = {}
    for (a, b, c, d) in wires:
        ax.plot([a, c], [b, d], color="#1f3b99", lw=lw, solid_capstyle="round")
        for p in ((a, b), (c, d)):
            ends[p] = ends.get(p, 0) + 1
    pinpts = set()
    for s in syms:
        o = XF.get(s["o"], XF["R0"])
        for l in load_sym(s["name"], extra_dirs):
            t = l.split()
            if not t:
                continue
            if t[0] == "PIN":
                px, py = o(int(t[1]), int(t[2])); pinpts.add((s["x"] + px, s["y"] + py))
    for p, n in ends.items():
        if n >= 3 or (n == 2 and p in pinpts and False):
            ax.plot(*p, "o", color="#1f3b99", ms=2.6)
    # symbols
    for s in syms:
        o = XF.get(s["o"], XF["R0"])
        X, Y = s["x"], s["y"]
        tp = lambda x, y: (X + o(x, y)[0], Y + o(x, y)[1])
        win = {}
        for l in load_sym(s["name"], extra_dirs):
            t = l.split()
            if not t:
                continue
            if t[0] == "LINE":
                a, b = tp(int(t[2]), int(t[3])); c, d = tp(int(t[4]), int(t[5]))
                ax.plot([a, c], [b, d], color="#8b0000", lw=lw)
            elif t[0] == "RECTANGLE":
                pts = [(int(t[2]), int(t[3])), (int(t[4]), int(t[3])), (int(t[4]), int(t[5])), (int(t[2]), int(t[5])), (int(t[2]), int(t[3]))]
                pts = [tp(*p) for p in pts]
                ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#8b0000", lw=lw)
            elif t[0] in ("CIRCLE", "ARC"):
                a, b = tp(int(t[2]), int(t[3])); c, d = tp(int(t[4]), int(t[5]))
                cx, cy, w, h = (a + c) / 2, (b + d) / 2, abs(c - a), abs(d - b)
                if t[0] == "CIRCLE":
                    ax.add_patch(Arc((cx, cy), w, h, color="#8b0000", lw=lw))
                else:
                    e, f = tp(int(t[6]), int(t[7])); g, h2 = tp(int(t[8]), int(t[9]))
                    a1 = math.degrees(math.atan2(-(f - cy), e - cx)); a2 = math.degrees(math.atan2(-(h2 - cy), g - cx))
                    ax.add_patch(Arc((cx, cy), w, h, theta1=min(a1, a2), theta2=max(a1, a2), color="#8b0000", lw=lw))
            elif t[0] == "WINDOW":
                win[t[1]] = (int(t[2]), int(t[3]))
            elif t[0] == "TEXT" and len(t) > 5:
                a, b = tp(int(t[1]), int(t[2]))
                ax.text(a, b, " ".join(t[5:]), fontsize=4.5, ha="center", va="center", color="#8b0000")
        pinname = None
        for l in load_sym(s["name"], extra_dirs):
            t = l.split()
            if t and t[0] == "PIN":
                pinname = (int(t[1]), int(t[2]), t[3])
            elif t and t[0] == "PINATTR" and t[1] == "PinName" and pinname and "BLOCK" in "".join(load_sym(s["name"], extra_dirs)[:2]):
                a, b = tp(pinname[0], pinname[1])
                dx = {"LEFT": 10, "RIGHT": -10}.get(pinname[2], 0); dy = {"TOP": 14, "BOTTOM": -14}.get(pinname[2], 0)
                rot = 90 if pinname[2] in ("TOP", "BOTTOM") else 0
                ax.text(a + dx, b + dy, t[2], fontsize=3.8, rotation=rot, color="#8b0000",
                        ha={"LEFT": "left", "RIGHT": "right"}.get(pinname[2], "center"),
                        va={"TOP": "top", "BOTTOM": "bottom"}.get(pinname[2], "center"))
        name = s["attrs"].get("InstName", "")
        val = s["attrs"].get("Value2") or s["attrs"].get("Value", "")
        if s["name"].startswith(("nmos", "pmos")):
            val = val.replace("l=", "L=").replace("w=", "W=")
            m = re.search(r"m=(\d+)", val)
            val = re.sub(r"\s*m=\d+", "", val)
            txt = f"{name}\n{val.split()[1] if len(val.split()) > 1 else ''}\n{val.split()[0]}" + (f"\nM={m.group(1)}" if m else "")
            px, py = tp(52, 40) if s["o"] == "R0" else tp(-4, 40)
            ha = "left" if s["o"] == "R0" else "right"
            ax.text(X + (72 if s["o"] == "R0" else -72), Y + 48, txt, fontsize=4.2, ha=ha, va="center", color="black", linespacing=1.05)
        elif s["name"].lower().startswith(("r_ndiff", "res")):
            ax.text(X + 40, Y + 56, f"{name}\n{s['attrs'].get('Value', '')}", fontsize=4.5, ha="left", va="center")
        elif s["name"].lower().startswith("cap"):
            ax.text(X + 40, Y + 32, f"{name}\n{s['attrs'].get('Value', '')}", fontsize=4.5, ha="left", va="center")
        elif s["name"].lower().startswith("npn"):
            ax.text(X + 72, Y + 48, f"{name}\nArea={s['attrs'].get('Value2', s['attrs'].get('Value', ''))}", fontsize=4.5, ha="left", va="center")
        elif s["name"].lower().startswith("voltage"):
            v = s["attrs"].get("Value", "")
            ax.text(X + 24, Y + 56, name if len(v) > 28 else f"{name}\n{v}", fontsize=4.0 if len(v) > 28 else 4.5, ha="left", va="center",
                    rotation=90 if len(v) > 28 else 0)
        else:
            ax.text(X, Y + 8, name, fontsize=5, ha="center", va="center", color="#8b0000")
    for x, y, n in flags:
        if n == "0":
            ax.plot([x - 16, x + 16, x, x - 16], [y + 8, y + 8, y + 24, y + 8], color="black", lw=lw)
            ax.plot([x, x], [y, y + 8], color="black", lw=lw)
        else:
            ax.text(x, y - 10, n, fontsize=4.8, ha="center", va="bottom", color="#006400", weight="bold")
    for x, y, s in texts:
        if s.startswith("!"):
            ax.text(x, y, s[1:].replace("\\n", "\n")[:120], fontsize=4.5, color="#555", va="top", family="monospace")
    if title:
        ax.set_title(title, fontsize=8)
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return out
