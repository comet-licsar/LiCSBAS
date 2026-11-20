"""Functional test for the post-hoc GACOS correction plots in LiCSBAS02to05_unwrap.

Stubs the optional dependencies that are not required for the plotting logic
(h5py / astropy / cmcrameri) and the licsar_extra ``lics_unwrap`` helper API,
then drives ``plot_gacos_corrections`` on a synthetic GEOCmlX output and checks
that the standard LiCSBAS-style PNGs are produced.
"""
import os
import sys
import types
import tempfile

import numpy as np
import pytest


def _stub_module(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


def _stub_package(name, submods=()):
    """Create a package stub plus optional submodules, wired together."""
    pkg = _stub_module(name)
    pkg.__path__ = []  # mark as package
    for s in submods:
        full = name + "." + s
        sm = _stub_module(full, bootstrap=lambda *a, **k: None,
                          NumpyRNGContext=object, romaO="inferno", batlow="viridis")
        setattr(pkg, s, sm)
        sys.modules[full] = sm
    return pkg


@pytest.fixture(scope="module")
def _deps():
    """Provide minimal stubs for optional deps missing in a bare environment."""
    if "h5py" not in sys.modules:
        _stub_module("h5py", File=object, FileID=object)
    if "pandas" not in sys.modules:
        _stub_module("pandas")
    if "statsmodels" not in sys.modules:
        _stub_package("statsmodels", submods=["api"])
        sys.modules["statsmodels"].__version__ = "0-stub"
    if "astropy" not in sys.modules:
        _stub_package("astropy", submods=["stats", "utils"])
    if "cmcrameri" not in sys.modules:
        pkg = _stub_module("cmcrameri")
        cm = _stub_module("cmcrameri.cm", romaO="inferno", batlow="viridis")
        pkg.cm = cm
    # matplotlib backend offscreen safety
    import matplotlib as mpl
    mpl.use("Agg")
    yield


@pytest.fixture
def fake_lics_unwrap():
    """Minimal stand-in for the licsar_extra lics_unwrap API used by the step."""
    class FakeArr:
        def __init__(self, values):
            self.values = np.asarray(values, dtype=np.float32)
        def where(self, mask):
            if np.shape(mask) == self.values.shape:
                return FakeArr(np.where(mask, self.values, 0.0))
            return self  # xarray would align by coordinates; shapes differ in the fake
        def __sub__(self, other):
            return FakeArr(self.values - other.values)

    # sltd tifs are full-resolution (ml times larger than the output unw grid)
    full = (1000, 1000)  # with ny=nx=100 and ml=10 below -> exactly the unw grid
    mod = types.SimpleNamespace()
    mod.load_tif2xr = lambda tif, cliparea_geo=None, **kw: FakeArr(
        np.random.randn(*full).astype(np.float32))

    def _multilook(da, ml=10, coords=("lon", "lat")):
        v = da.values
        ny, nx = v.shape
        return FakeArr(v.reshape(ny // ml, ml, nx // ml, ml).mean(axis=(1, 3)))

    mod.multilook_xrda = _multilook
    return mod


@pytest.fixture
def workdir(tmp_path):
    """Synthetic 02to05 output dir (GEOCml5) + GACOS dir."""
    ny, nx, ml = 100, 100, 10
    outdir = tmp_path / "GEOCml5"
    pair = "20160909_20160925"
    (outdir / pair).mkdir(parents=True)
    unw = np.random.randn(ny, nx).astype(np.float32)
    unw[:10, :10] = 0.0
    unw.tofile(str(outdir / pair / (pair + ".unw")))
    with open(outdir / "slc.mli.par", "w") as f:
        f.write("range_samples: %d\nazimuth_lines: %d\nradar_frequency: 5405000000 Hz\n" % (nx, ny))
    gacos = tmp_path / "GACOS"
    gacos.mkdir()
    (gacos / (pair.split("_")[0] + ".sltd.geo.tif")).write_bytes(b"fake")
    (gacos / (pair.split("_")[1] + ".sltd.geo.tif")).write_bytes(b"fake")
    return str(tmp_path), str(outdir), str(gacos), ml


def test_plot_gacos_corrections_generates_standard_pngs(_deps, fake_lics_unwrap, workdir):
    workdir_root, outdir, gacos, ml = workdir

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import licsbas.steps._02to05_unwrap as step
    step.unw = fake_lics_unwrap  # inject stand-in for licsar_extra.lics_unwrap

    step.plot_gacos_corrections(outdir, gacos, ml, cliparea_geo=None)

    pair = "20160909_20160925"
    assert os.path.exists(os.path.join(outdir, pair, pair + ".gacos.png")), \
        "standard 3-panel correction plot (pair.gacos.png) missing"
    assert os.path.getsize(os.path.join(outdir, pair, pair + ".gacos.png")) > 1000
    assert os.path.exists(os.path.join(outdir, "GACOS_info2.txt"))
    with open(os.path.join(outdir, "GACOS_info2.txt")) as f:
        lines = f.read().strip().splitlines()
    assert len(lines) >= 2 and lines[0].split()[0] == "pair"
    assert pair in lines[1]


def test_plot_gacos_corrections_safe_without_licsar_extra(_deps, workdir):
    workdir_root, outdir, gacos, ml = workdir
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import licsbas.steps._02to05_unwrap as step
    step.unw = None  # licsar_extra not installed -> must skip gracefully, not raise
    step.plot_gacos_corrections(outdir, gacos, ml)
    pair = "20160909_20160925"
    assert not os.path.exists(os.path.join(outdir, pair, pair + ".gacos.png"))
