"""Checks that need neither LTspice nor the course models:
- the four submission schematics are exactly what the Python generators produce;
- the static linearity (INL/DNL) and temperature coefficient in summary.json follow from the committed CSVs;
- the linearity function behaves correctly on ideal and faulty staircases."""
import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Supporting_Documents" / "scripts"))

import char_asc  # noqa: E402
import opamp03_asc  # noqa: E402
import reg02_asc  # noqa: E402
import sys04_asc  # noqa: E402
from sys04_run import lin  # noqa: E402

DAC = ROOT / "Simulation_Results" / "Complete_DAC"


@pytest.mark.parametrize("name,make", [
    ("01_Characterisation.asc", lambda: char_asc.draw()),
    ("02_VREF_Regulator.asc", lambda: reg02_asc.draw_file()),
    ("03_Folded_Cascode_OpAmp.asc", lambda: opamp03_asc.draw_file()),
    ("04_Complete_6Bit_DAC.asc", lambda: sys04_asc.draw()),
])
def test_schematic_is_reproduced_by_its_generator(name, make):
    assert make().text_asc() == (ROOT / name).read_text()


def columns(path):
    with open(path) as fh:
        rows = list(csv.DictReader(fh))
    return {k: np.array([float(r[k]) if r[k] not in ("", "nan") else np.nan for r in rows]) for k in rows[0]}


@pytest.mark.parametrize("tag", ["50R", "noload"])
@pytest.mark.parametrize("node", ["v(vout)", "v(vout_ideal)"])
def test_static_linearity_in_summary_follows_from_csv(tag, node):
    summary = json.loads((DAC / "summary.json").read_text())["static"][tag][node]
    got, _, _ = lin(columns(DAC / f"static_{tag}.csv")[node])
    for key, value in summary.items():
        assert got[key] == pytest.approx(value, rel=1e-9, abs=1e-12), key


def test_temperature_coefficient_follows_from_csv():
    tc = json.loads((DAC / "summary.json").read_text())["tc"]
    for code in (31, 63):
        cols = columns(DAC / f"tc_code{code}.csv")
        temps = list(cols["temp"])
        v = cols["v(vout)"]
        vn = v[temps.index(27)]
        assert tc[f"{code:06b}"]["v(vout)"]["TC_ppm_per_C"] == pytest.approx((v.max() - v.min()) / vn / 80 * 1e6)


def test_lin_ideal_staircase():
    v = np.arange(64) * 12.5e-3
    r, dnl, inl = lin(v)
    assert r["monotonic"] and r["LSB_mV"] == pytest.approx(12.5)
    assert np.abs(dnl).max() < 1e-12 and np.abs(inl).max() < 1e-12 and abs(r["gain_error_LSB"]) < 1e-9


def test_lin_flags_a_missing_code_and_non_monotonicity():
    v = np.arange(64) * 12.5e-3
    v[33:] += 12.5e-3                       # a double step between codes 32 and 33
    r, dnl, _ = lin(v)
    assert dnl[32] == pytest.approx(2 * 63 / 64 - 1, rel=1e-9) and r["monotonic"]
    v2 = np.arange(64) * 12.5e-3
    v2[40] = v2[38]                         # output drops at code 40
    assert not lin(v2)[0]["monotonic"]
