"""Tests for licsbas/steps/_01_get_geotiff_nisar.py (no network, no asf_search).

We stub the licsar_extra helpers (nisar_data, lics_proc_tools) with an in-memory
fake that mimics the real API (get_nisar_data -> product collection, get_frameid,
get_asf_session -> an object whose .get() streams bytes), then assert the step
builds per-frame subfolders, downloads, and skips existing files.
"""
import importlib
import os
import sys
import types
import pytest


def _install_fake_nisar(tmpdir, scene_urls):
    """scene_urls: list of (sceneName, fid, sizeMB, url). Installs fake modules."""
    # --- lics_proc_tools ---
    lp = types.ModuleType("lics_proc_tools")
    def cliparea_geo2coords(cliparea_geo, outputaswkt=False):
        assert outputaswkt is True
        return "POLYGON((-118.4 33.7, -118.2 33.7, -118.2 33.8, -118.4 33.8, -118.4 33.7))"
    lp.cliparea_geo2coords = cliparea_geo2coords

    # --- nisar_data ---
    nd = types.ModuleType("nisar_data")
    class FakeProd:
        def __init__(self, name, size, url):
            self.properties = {"sceneName": name, "sizeMB": size, "acquisitionTime": "20250601T00:00:00", "url": url}
    prods = [FakeProd(n, s, u) for (n, _, s, u) in scene_urls]
    def get_nisar_data(wkt, dtype='GSLC', startdate=None, enddate=None, outAspd=False, shortpd=False):
        assert 'POLYGON' in wkt
        assert dtype == 'GUNW'
        if outAspd:
            raise AssertionError("step must request product collection (outAspd=False)")
        return list(prods)
    nd.get_nisar_data = get_nisar_data
    def get_frameid(fileid, return_pubpath=False):
        # real one: ff[5]+ff[6]+'_'+ff[7]; emulate for our fake names
        m = scene_urls[[s[0] for s in scene_urls].index(fileid)][1]
        return m
    nd.get_frameid = get_frameid
    # fake ASF session: .get(url, stream=True) -> context manager w/ iter_content
    class FakeResp:
        def __init__(self, payload): self._payload = payload
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def raise_for_status(self): pass
        def iter_content(self, chunk_size=None): yield self._payload
    class FakeSession:
        def get(self, url, stream=True, timeout=None):
            return FakeResp(b"FAKE-H5-" + url.split("/")[-1].encode("latin1", "ignore")[:16])
    nd.get_asf_session = lambda: FakeSession()

    sys.modules["lics_proc_tools"] = lp
    sys.modules["nisar_data"] = nd
    return prods


@pytest.fixture(autouse=True)
def _reset_modules():
    saved = {m: sys.modules.get(m) for m in ("lics_proc_tools", "nisar_data",
                                             "licsbas.steps._01_get_geotiff_nisar")}
    yield
    for m, mod in saved.items():
        if mod is None:
            sys.modules.pop(m, None)
        else:
            sys.modules[m] = mod
    import licsbas.steps._01_get_geotiff_nisar as step
    importlib.reload(step)


def test_groups_by_frame_and_downloads(tmp_path):
    prods = _install_fake_nisar(
        tmp_path,
        [
            ("NISAR_L2_PR_GUNW_009_018_A_007_20250601.h5", "07_2025", 40, "https://asf/f1.h5"),
            ("NISAR_L2_PR_GUNW_009_018_A_007_20250615.h5", "07_2025", 42, "https://asf/f2.h5"),
            ("NISAR_L2_PR_GUNW_009_021_B_008_20250601.h5", "08_2025", 41, "https://asf/f3.h5"),
        ])
    mod = importlib.import_module("licsbas.steps._01_get_geotiff_nisar")
    outdir = str(tmp_path / "NISAR_GUNW")
    rc = mod.main(["prog", "-g", "-118.4/-118.2/33.8/33.7", "-o", outdir, "--max", "500"])
    assert rc == 0
    d1 = os.path.join(outdir, "07_2025")
    d2 = os.path.join(outdir, "08_2025")
    assert os.path.isfile(os.path.join(d1, "NISAR_L2_PR_GUNW_009_018_A_007_20250601.h5"))
    assert os.path.isfile(os.path.join(d1, "NISAR_L2_PR_GUNW_009_018_A_007_20250615.h5"))
    assert os.path.isfile(os.path.join(d2, "NISAR_L2_PR_GUNW_009_021_B_008_20250601.h5"))
    assert os.path.getsize(os.path.join(d1, "NISAR_L2_PR_GUNW_009_018_A_007_20250601.h5")) > 0

    # Re-run: everything is skipped, still rc==0
    rc = mod.main(["prog", "-g", "-118.4/-118.2/33.8/33.7", "-o", outdir])
    assert rc == 0

    # Dry run: no download, rc==0
    outdir2 = str(tmp_path / "NISAR_GUNW_dry")
    rc = mod.main(["prog", "-g", "-118.4/-118.2/33.8/33.7", "-o", outdir2, "--dry_run"])
    assert rc == 0
    assert not os.path.exists(os.path.join(outdir2, "07_2025", "NISAR_L2_PR_GUNW_009_018_A_007_20250601.h5"))


def test_list_frames_only(tmp_path, capsys):
    _install_fake_nisar(
        tmp_path,
        [
            ("NISAR_L2_PR_GUNW_009_018_A_007_20250601.h5", "07_2025", 40, "https://asf/f1.h5"),
            ("NISAR_L2_PR_GUNW_009_021_B_008_20250601.h5", "08_2025", 41, "https://asf/f3.h5"),
        ])
    mod = importlib.import_module("licsbas.steps._01_get_geotiff_nisar")
    outdir = str(tmp_path / "NISAR_GUNW")
    rc = mod.main(["prog", "-g", "-118.4/-118.2/33.8/33.7", "-o", outdir,
                   "--list-frames",
                   ])
    out = capsys.readouterr()
    assert rc == 0
    assert "07_2025" in out.out and "08_2025" in out.out
    assert "--frame" in out.out  # usage hint shown
    # nothing was downloaded
    assert not os.path.exists(outdir)


def test_frame_filter(tmp_path, capsys):
    _install_fake_nisar(
        tmp_path,
        [
            ("NISAR_L2_PR_GUNW_009_018_A_007_20250601.h5", "07_2025", 40, "https://asf/f1.h5"),
            ("NISAR_L2_PR_GUNW_009_021_B_008_20250601.h5", "08_2025", 41, "https://asf/f3.h5"),
        ])
    mod = importlib.import_module("licsbas.steps._01_get_geotiff_nisar")
    outdir = str(tmp_path / "NISAR_GUNW")
    # keep frame 07_2025 only
    rc = mod.main(["prog", "-g", "-118.4/-118.2/33.8/33.7", "-o", outdir,
                   "--frame", "07_2025"])
    assert rc == 0
    assert os.path.isfile(os.path.join(outdir, "07_2025", "NISAR_L2_PR_GUNW_009_018_A_007_20250601.h5"))
    assert not os.path.exists(os.path.join(outdir, "08_2025"))
    # unknown frame -> rc 1 + availability listed
    outdir2 = str(tmp_path / "NISAR_GUNW_bad")
    rc = mod.main(["prog", "-g", "-118.4/-118.2/33.8/33.7", "-o", outdir2,
                   "--frame", "99_2025"])
    err = capsys.readouterr().err
    assert rc == 1 and "99_2025" in err


def test_missing_bbox(tmp_path, capsys):
    mod = importlib.import_module("licsbas.steps._01_get_geotiff_nisar")
    rc = mod.main(["prog"])
    assert rc == 1
    assert "required" in capsys.readouterr().err
