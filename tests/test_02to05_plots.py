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
import importlib.util as _iu

import numpy as np
import pytest

# every sys.modules key we create ourselves, so we can remove it on teardown.
# We must NEVER leak a fake `pandas`/`statsmodels`/... into the interpreter:
# other test modules (and xarray, io_lib, ...) import those for real.
_STUBBED = set()


def _reg(name, obj):
    sys.modules[name] = obj
    _STUBBED.add(name)
    return obj


def _stub_module(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return _reg(name, mod)


def _stub_package(name, submods=()):
    """Create a package stub plus optional submodules, wired together."""
    pkg = types.ModuleType(name)
    pkg.__path__ = []  # mark as package
    _reg(name, pkg)
    for s in submods:
        full = name + "." + s
        sm = _stub_module(full, bootstrap=lambda *a, **k: None,
                          NumpyRNGContext=object, romaO="inferno", batlow="viridis")
        setattr(pkg, s, sm)
    return pkg


def _installed(name):
    try:
        return _iu.find_spec(name) is not None
    except Exception:
        return False


@pytest.fixture(scope="module")
def _deps():
    """Provide minimal stubs ONLY for optional deps that are genuinely absent,
    leave real (installed) packages alone, and remove any stub we inject when
    this module's tests are done so it never leaks into other test modules."""
    def ensure(name, maker):
        if name in sys.modules:
            return  # already present (imported earlier) -> keep it
        if _installed(name):
            return  # installed -> use the REAL package, don't stub over it
        maker()
    ensure("h5py", lambda: _stub_module("h5py", File=object, FileID=object))
    ensure("pandas", lambda: _stub_module("pandas"))

    def _statsmodels():
        p = _stub_package("statsmodels", submods=["api"])
        p.__version__ = "0-stub"
    ensure("statsmodels", _statsmodels)

    ensure("astropy", lambda: _stub_package("astropy", submods=["stats", "utils"]))

    def _cmcrameri():
        pkg = types.ModuleType("cmcrameri")
        _reg("cmcrameri", pkg)
        cm = _stub_module("cmcrameri.cm", romaO="inferno", batlow="viridis")
        pkg.cm = cm
    ensure("cmcrameri", _cmcrameri)

    # matplotlib backend offscreen safety
    import matplotlib as mpl
    mpl.use("Agg")
    yield
    # teardown: remove only the stubs we injected this module
    for k in list(_STUBBED):
        sys.modules.pop(k, None)
    _STUBBED.clear()


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
    with open(outdir / "EQA.dem_par", "w") as f:
        f.write("width: %d\nnlines: %d\npost_lon: 5e-05\npost_lat: 5e-05\n"
                "corner_lon: -120.0\ncorner_lat: 40.0\n" % (nx, ny))
    gacos = tmp_path / "GACOS"
    gacos.mkdir()

    def _mk_tif(path):
        """A small **valid** GeoTIFF (gdal.Warp must be able to read it)."""
        from osgeo import gdal
        drv = gdal.GetDriverByName("GTiff")
        dst = drv.Create(str(path), nx * ml, ny * ml, 1, gdal.GDT_Float32)
        res = 100.0 / (nx * ml)
        dst.SetGeoTransform((-120.0 + nx * ml * res, res, 0.0,
                             40.0 - ny * ml * res, 0.0, -res))
        import numpy as _np
        band = dst.GetRasterBand(1)
        band.WriteArray(_np.random.randn(ny * ml, nx * ml).astype(_np.float32))
        band = None
        dst = None

    for tag in pair.split("_"):
        _mk_tif(gacos / (tag + ".sltd.geo.tif"))
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
    """Must never raise - these are best-effort QC plots."""
    workdir_root, outdir, gacos, ml = workdir
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import licsbas.steps._02to05_unwrap as step
    step.unw = None  # licsar_extra not installed
    step.plot_gacos_corrections(outdir, gacos, ml)  # must not raise
