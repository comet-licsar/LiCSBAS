"""Tests for the python batch processor (``licsbas.batch``) and flowchart.

These tests only exercise the *pipeline construction* (no LiCSAR data, no
step imports), and the flowchart PNG writer (skipped if ``dot`` is absent).
"""
import os
import shutil

import pytest

from licsbas.batch import BatchConfig, build_pipeline, run_batch

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def keys(steps):
    return [s.key for s in steps]


def test_standard_chain():
    cfg = BatchConfig()
    steps = build_pipeline(cfg)
    k = keys(steps)
    assert "01" in k and "02" in k
    assert "02to05" not in k
    for sk in ("11", "12", "13", "14", "15", "16"):
        assert sk in k
    # no --sbovl anywhere
    assert all("--sbovl" not in s.argv for s in steps)
    # step 12 gets --multi_prime by default
    s12 = next(s for s in steps if s.key == "12")
    assert "--multi_prime" in s12.argv
    # TS dir defaults
    s13 = next(s for s in steps if s.key == "13")
    assert "-t" in s13.argv and "TS_GEOCml1" in s13.argv


def test_sbovl_chain():
    cfg = BatchConfig(sbovl=True)
    steps = build_pipeline(cfg)
    k = keys(steps)
    assert "120" in k                       # forced by sbovl
    assert "12" not in k                    # skipped for sbovl data
    for key in ("01", "02", "11", "13", "14", "15", "16"):
        s = next(x for x in steps if x.key == key)
        assert "--sbovl" in s.argv
    s120 = next(s for s in steps if s.key == "120")
    assert "--sbovl" in s120.argv


def test_sbovl_abs_chain():
    cfg = BatchConfig(sbovl=True, sbovl_abs=True)
    steps = build_pipeline(cfg)
    assert any(s.key == "131abs" for s in steps)
    s13 = next(s for s in steps if s.key == "13")
    assert "--sbovl_abs" in s13.argv


def test_reunw_chain():
    cfg = BatchConfig(run_reunw=True, nlook=20)
    steps = build_pipeline(cfg)
    k = keys(steps)
    assert "02to05" in k
    assert "02" not in k
    s01 = next(s for s in steps if s.key == "01")
    assert "--get_pha" in s01.argv and "--get_mli" in s01.argv
    s02to05 = next(s for s in steps if s.key == "02to05")
    assert "-M" in s02to05.argv and "20" in s02to05.argv


def test_optional_steps_off_shown_grey():
    cfg = BatchConfig()
    steps = build_pipeline(cfg)
    off = [s for s in steps if s.optional and not s.module]
    names = {s.name for s in off}
    assert "LiCSBAS03op_GACOS.py" in names
    assert "LiCSBAS04op_mask_unw.py" in names


def test_optional_gacos_on():
    cfg = BatchConfig(do03op_GACOS=True)
    steps = build_pipeline(cfg)
    s03 = next(s for s in steps if s.key == "03")
    assert s03.argv[:2] == ["-i", "GEOCml1"]
    assert "GACOS" in s03.argv[3]           # out dir ...GACOS
    # following steps should use the suffixed dir
    s11 = next(s for s in steps if s.key == "11")
    assert "GEOCml1GACOS" in " ".join(s11.argv)


def test_add_omits_empty_values():
    """Flags with empty settings must not leak into the argv."""
    from licsbas.batch import _add
    argv: list = []
    _add(argv, "-x", "")
    _add(argv, "-x", None)
    assert argv == []
    _add(argv, "-x", "5")
    assert argv == ["-x", "5"]


def test_no_empty_argv_entries():
    cfg = BatchConfig()
    for s in build_pipeline(cfg):
        assert all(a != "" for a in s.argv), f"empty argv entry in {s.name}"


def test_run_batch_dry_run_returns_zero(capsys):
    cfg = BatchConfig()
    rc = run_batch(cfg, dry_run=True)
    assert rc == 0
    out = capsys.readouterr().out
    assert "LiCSBAS13_sb_inv.py" in out


def test_flowchart_png(tmp_path):
    if shutil.which("dot") is None:
        pytest.skip("graphviz 'dot' not installed")
    from licsbas.batch import save_flowchart
    cfg = BatchConfig(sbovl=True)
    out = tmp_path / "chain" / "fc.png"
    p = save_flowchart(cfg, str(out))
    assert os.path.exists(p)
    assert os.path.getsize(p) > 1000
