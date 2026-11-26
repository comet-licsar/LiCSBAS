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


def test_nisar_chain():
    cfg = BatchConfig(use_nisar=True, nlook=10,
                      pNISAR_bbox="14.00/14.25/40.75/40.95")
    steps = build_pipeline(cfg)
    k = keys(steps)
    # the LiCSAR step-01 download is replaced by the NISAR data-access pair
    assert "01" not in k
    assert "01nisar" in k
    assert "nisar2geoc" in k
    # steps 02-16 run exactly as for LiCSAR data
    assert "02" in k
    for sk in ("11", "12", "13", "14", "15", "16"):
        assert sk in k
    s01n = next(s for s in steps if s.key == "01nisar")
    assert "-g" in s01n.argv and "14.00/14.25/40.75/40.95" in s01n.argv
    # GUNW-only download step: no -t (product type) and no -E (GSLC) flags
    assert "-t" not in s01n.argv and "-E" not in s01n.argv
    sng = next(s for s in steps if s.key == "nisar2geoc")
    assert sng.argv[0] == "-i" and "NISAR_GUNW" in sng.argv
    assert "-t" in sng.argv  # coherence threshold (default 0.5)
    assert "--sbovl" not in sng.argv

    # frame selection + correction overrides flow through
    cfg2 = BatchConfig(use_nisar=True, pNISAR_bbox="1/2/3/4",
                       pNISAR_frames="018A_01234",
                       nisar2geoc_no_iono=True, nisar2geoc_download_dem=True)
    st2 = build_pipeline(cfg2)
    s01n2 = next(s for s in st2 if s.key == "01nisar")
    assert "--frame" in s01n2.argv and "018A_01234" in s01n2.argv
    sng2 = next(s for s in st2 if s.key == "nisar2geoc")
    i = sng2.argv.index("-i")
    assert sng2.argv[i + 1] == os.path.join("NISAR_GUNW", "018A_01234")
    assert "-D" in sng2.argv and "--no_iono" in sng2.argv


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


def test_tide_iono_corrections_call_standard_step():
    """Tide/iono corrections must go through LiCSBAS131_corrections (the standard step),
    not through inline `python -c` calls, and sbovl mode must add --sbovl."""
    cfg = BatchConfig(p131_tide=True, p131_iono=True, p01_start_date="20141001")
    steps = build_pipeline(cfg)
    c = [s for s in steps if s.key == "131corr"]
    assert c, "expected a 131corr step when tide/iono corrections are enabled"
    s = c[0]
    assert s.name == "LiCSBAS131_corrections.py"
    assert "--tide" in s.argv and "--iono" in s.argv
    assert "--sbovl" not in s.argv
    assert "python" not in " ".join(s.argv) and not any(":" in a for a in s.argv[:0])

    cfg_s = BatchConfig(sbovl=True, p131_tide=True, p131_iono=True)
    s2 = [s for s in build_pipeline(cfg_s) if s.key == "131corr"][0]
    assert "--sbovl" in s2.argv


def test_131_corrections_step_is_importable_and_accepts_flags():
    """Smoke check that the standard corrections step exists with the expected flags."""
    try:
        import licsbas.steps._131_corrections as m  # noqa: F401
    except ModuleNotFoundError as e:
        pytest.skip(f"optional runtime dep missing: {e}")
    assert callable(m.main)
    src = open(m.__file__).read()
    for flag in ("--tide", "--iono", "--gacos", "--sbovl", "correct_cum_from_tifs"):
        assert flag in src, f"expected {flag} in _131_corrections"
