"""Tests for licsbas/steps/_02op_phasebias.py (no phasebias install needed)."""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import licsbas.steps._02op_phasebias as step  # noqa: E402


def _mk_pairs(d, pairs):
    d = str(d)
    os.makedirs(d, exist_ok=True)
    for p in pairs:
        os.mkdir(os.path.join(d, p))
    with open(os.path.join(d, "baselines"), "w") as f:
        f.write("20191201\n")


def test_derive_dates_from_pairs():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        _mk_pairs(td, ["20200505_20210101", "20241230_20250120", "20191201_20200505"])
        start, end, n = step._derive_dates_from_pairs(td)
        # start = first date of the first (earliest) pair;
        # end   = last date of the last (latest) pair
        assert (start, end, n) == ("20191201", "20250120", 3)


def test_derive_dates_none_when_no_pairs():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "baselines"), exist_ok=True)
        assert step._derive_dates_from_pairs(td) == (None, None, 0)
        assert step._derive_dates_from_pairs(os.path.join(td, "missing_dir")) == (None, None, 0)


def test_main_uses_derived_dates_in_config(tmp_path, monkeypatch):
    # fake 'phasebias' package so the import check passes
    monkeypatch.setitem(sys.modules, "phasebias", types.ModuleType("phasebias"))
    in_dir = tmp_path / "GEOC"
    _mk_pairs(in_dir, ["20200505_20210101", "20241230_20250120"])
    out_dir = tmp_path / "GEOC_phasebias"

    rc = step.main(["prog", "-i", str(in_dir), "-o", str(out_dir), "--dry-run"])
    assert rc == 0

    cfg = os.path.join(str(out_dir), "phasebias_config.txt")
    assert os.path.isfile(cfg), "phasebias config.txt not generated"
    text = open(cfg).read()
    assert "start=20200505" in text      # first date of the first pair
    assert "end=20250120" in text        # last date of the last pair

    # explicit values override the derived ones
    rc = step.main(["prog", "-i", str(in_dir), "-o", str(out_dir),
                    "--start", "20200101", "--end", "20220101", "--dry-run"])
    assert rc == 0
    text = open(cfg).read()
    assert "start=20200101" in text and "end=20220101" in text


def test_main_without_pairs_errors(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "phasebias", types.ModuleType("phasebias"))
    in_dir = tmp_path / "empty"
    os.makedirs(str(in_dir), exist_ok=True)
    rc = step.main(["prog", "-i", str(in_dir), "-o", str(tmp_path / "out"),
                    "--dry-run"])
    assert rc == 1
