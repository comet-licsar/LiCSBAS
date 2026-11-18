"""Smoke tests: package import, submodules, step modules, entry points, version.

Run from an environment where licsbas is installed (``pip install .`` or ``pip install -e .``):
    pytest tests/ -v
"""
import importlib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _all_eps():
    from importlib.metadata import entry_points
    return list(entry_points().select(group="console_scripts"))


def test_version():
    import licsbas
    assert licsbas.__version__ == "3.0.0"


def test_core_submodules_import():
    for mod in ("licsbas.meta", "licsbas.io_lib",
                "licsbas.tools_lib", "licsbas.loop_lib", "licsbas.inv_lib",
                "licsbas.plot_lib", "licsbas.extras_light", "licsbas.steps"):
        importlib.import_module(mod)


def _step_modules():
    steps = REPO / "licsbas" / "steps"
    return sorted(p.stem for p in steps.glob("_[0-9]*.py"))


@pytest.mark.parametrize("stem", _step_modules())
def test_step_module_imports(stem):
    """Every command-line step module must import cleanly with base deps only."""
    importlib.import_module(f"licsbas.steps.{stem}")


def test_entry_points_registered():
    names = {e.name for e in _all_eps() if e.value.split(":")[0].startswith("licsbas.")}
    for expected in ("licsbas-01-get-geotiff", "licsbas-02-ml-prep",
                     "licsbas-02to05-unwrap", "licsbas-03op-era5",
                     "licsbas-03op-gacos", "licsbas-04op-mask-unw",
                     "licsbas-05op-clip-unw", "licsbas-11-check-unw",
                     "licsbas-12-loop-closure", "licsbas-120-choose-reference",
                     "licsbas-130-sb-inv", "licsbas-131-boi-absolute",
                     "licsbas-131-bovl2abs", "licsbas-131-corrections",
                     "licsbas-132-unwrapping-correction", "licsbas-133-write-h5",
                     "licsbas-14-vel-std", "licsbas-15-mask-ts",
                     "licsbas-16-filt-ts", "licsbas-17-plot-corrections",
                     "licsbas-plot-network", "licsbas-plot-ts",
                     "licsbas-flt2geotiff", "licsbas-out2nc",
                     "licsbas-get-geotiff", "licsbas-unwrap"):
        assert expected in names, f"missing entry point: {expected}"


def test_all_entry_points_resolve():
    """Every declared entry point must target an importable module with main()."""
    import importlib
    for e in _all_eps():
        if not e.value.split(":")[0].startswith("licsbas"):
            continue
        mod_name, attr = e.value.split(":")
        mod = importlib.import_module(mod_name)
        assert callable(getattr(mod, attr)), f"{e.name} -> {e.value} not callable"


def test_step_mains_exist():
    """Each step module exposes a main() callable (console-script target)."""
    for stem in _step_modules():
        mod = importlib.import_module(f"licsbas.steps.{stem}")
        assert callable(getattr(mod, "main", None)), f"{stem} has no main()"
