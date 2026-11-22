"""Tests for licsbas.scripts._nisar2geoc (NISAR GUNW -> GEOC).

These run WITHOUT h5py/rasterio/asf — licsar_extra is stubbed by monkeypatching
``_load_nisar_ifg`` and the export helper, so we exercise the pure-Python/GDAL
orchestration: pair parsing, corrections bookkeeping, baselines, metadata.txt.
"""
import os
import glob

import pytest
import licsbas.scripts._nisar2geoc as ng


def test_pair_names():
    assert ng._pair_from_name("NISAR_CSL2_PR_GUNW_ABS_IS1-35_25m_IW1_20121112T225055_20121112T232031_...h5") == ("20121112", "20121112")
    assert ng._pair_from_name("20140823_20140906.h5") == ("20140823", "20140906")
    assert ng._pair_from_name("junk.h5") is None


class FakeIfg:
    """Mimics the licsar_data load_gunw() return: .attrs + ['unw']/['coh']."""
    def __init__(self, bperp, corr):
        self.attrs = {"bperp": bperp, "polarization": "VV", "freq": "A",
                      "unw corrections": list(corr), "crs": "EPSG:32633"}


def test_main_end_to_end(tmp_path, monkeypatch):
    indir = tmp_path / "in"
    indir.mkdir()
    h1 = indir / "NISAR_CSL2_PR_GUNW_ABS_IS1-35_25m_IW1_20121112T225055_20121112T232031_001.h5"
    h2 = indir / "NISAR_CSL2_PR_GUNW_ABS_IS1-35_25m_IW1_20121113T224102_20121113T231038_002.h5"
    h3 = indir / "NISAR_CSL2_PR_GUNW_ABS_IS1-35_25m_IW1_20121114T224900_20121114T231800_003.h5"
    for h in (h1, h2, h3):
        h.write_bytes(b"")

    def fake_load(h5path, freq_code="A", iono=True, offsets=True):
        return FakeIfg(bperp=12.5, corr=(["iono", "range offsets"] if offsets else ()))

    def fake_export(ds, pair, out_geoc, cc, do_quad, tmpdir, corrections, ref=None):
        d1, d2 = pair
        ifgdir = d1 + "_" + d2
        d = os.path.join(out_geoc, ifgdir)
        os.makedirs(d, exist_ok=True)
        unw = os.path.join(d, ifgdir + ".geo.unw.tif")
        cc_p = os.path.join(d, ifgdir + ".geo.cc.tif")
        open(unw, "w").write("")
        open(cc_p, "w").write("")
        return {"ifgdir": ifgdir, "ref": unw, "skipped": False}

    monkeypatch.setattr(ng, "_load_nisar_ifg", fake_load)
    monkeypatch.setattr(ng, "_export_ifg", fake_export)

    out = tmp_path / "GEOC"
    ng.main(indir=str(indir), outdir=str(out), cc_thresh=0.5, n_workers=1)

    # GEOC layout: one folder per pair + baselines + metadata.txt
    assert (out / "baselines").exists()
    assert (out / "metadata.txt").exists()
    assert (out / "20121112_20121112" / "20121112_20121112.geo.unw.tif").exists()
    assert (out / "20121114_20121114" / "20121114_20121114.geo.cc.tif").exists()

    baselines = (out / "baselines").read_text().splitlines()
    assert len(baselines) == 3
    for line in baselines:
        parts = line.split()
        assert parts[2] == "12.5000"

    meta_lines = (out / "metadata.txt").read_text().splitlines()
    assert any(l.startswith("center_time=") for l in meta_lines)
    assert "center_time=22:50:55.000000" in meta_lines
    assert "radar_freq=1.270000e+09" in "\n".join(meta_lines)


def test_metadata_center_time():
    assert ng._fmt_seconds(3600.0) == "1:00:00.000000"
    assert ng._fmt_seconds(3661.5) == "1:01:01.500000"


def test_dry_run_writes_nothing(tmp_path):
    indir = tmp_path / "in"
    indir.mkdir()
    (indir / "N_20121112T225055_20121112T232031.h5").write_bytes(b"")
    out = tmp_path / "GEOC"
    ng.main(indir=str(indir), outdir=str(out), dry_run=True)
    assert not (out / "baselines").exists()
