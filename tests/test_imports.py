"""Import smoke tests for the v3 ``licsbas`` package and its legacy shims.

All import checks run in **subprocesses** because several step modules have
module-level side effects (and some intentionally exit when an optional
tool is missing) — we isolate those instead of polluting the test process.
"""

import importlib
import importlib.util
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# modules that SystemExit at import time by design when their optional
# tool (licsar_extra / usgs-libcomcat) is not installed
OK_EXIT = {
    "licsbas.steps._02to05_unwrap",
    "licsbas.scripts._get_eqoffsets",
    "licsbas.steps._17_plot_corrections",
    # optional 'viewer' extras (pygmt + system GMT) not installed
    "licsbas.extras",
}


def py_subprocess(code):
    env = dict(os.environ, MPLBACKEND="Agg", PYTHONIOENCODING="utf-8")
    env.pop("PYTHONPATH", None)  # test the *installed* package, not the checkout
    # CI: real install in the venv. Locally: `LICSBAS_TEST_TARGET` points at a
    # `pip install --target` dir (e.g. from `pip install --target /tmp/t3 .`).
    target = env.pop("LICSBAS_TEST_TARGET", None)
    if target:
        env["PYTHONPATH"] = target
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=600, env=env,
    )


def check_import(module):
    code = (
        "import importlib; m = importlib.import_module(%r); "
        "print('IMPORTED', m.__name__)" % module
    )
    r = py_subprocess(code)
    if r.returncode != 0 and module in OK_EXIT:
        # expected: clean exit message about a missing optional tool
        out = (r.stdout + r.stderr).lower()
        assert "not installed" in out or "not found" in out or "licsar_extra" in out, r.stderr
        return r
    assert r.returncode == 0, f"import {module} failed:\n{r.stdout}\n{r.stderr}"
    return r


CORE_MODULES = [
    "licsbas",
    "licsbas.meta",
    "licsbas.tools_lib",
    "licsbas.io_lib",
    "licsbas.loop_lib",
    "licsbas.inv_lib",
    "licsbas.plot_lib",
    "licsbas.extras",
    "licsbas.extras_light",
]


def _legacy_step_shims():
    d = os.path.join(REPO, "LiCSBAS_lib", "_shims")
    # The legacy shim layer was removed in v3.0.0; if it is absent there is
    # nothing to collect/test here.
    if not os.path.isdir(d):
        return []
    out = []
    for name in sorted(os.listdir(d)):
        if os.path.isfile(os.path.join(d, name, "__init__.py")):
            out.append(name)
    return out


LEGACY_SHIMS = _legacy_step_shims()


def test_version_consistency():
    import licsbas
    assert licsbas.__version__
    import licsbas.meta as meta
    assert meta.ver == licsbas.__version__
    try:
        dist = importlib.metadata.version("LiCSBAS")
    except importlib.metadata.PackageNotFoundError:
        pytest.skip("LiCSBAS not installed as a distribution")
    assert dist == licsbas.__version__, (dist, licsbas.__version__)


@pytest.mark.parametrize("module", CORE_MODULES)
def test_core_imports(module):
    check_import(module)


@pytest.mark.parametrize("module", LEGACY_SHIMS)
def test_legacy_shims(module):
    check_import(module)


def test_legacy_shim_aliases_to_licsbas():
    if not os.path.isdir(os.path.join(REPO, "LiCSBAS_lib")):
        pytest.skip("legacy LiCSBAS_lib shim layer removed in v3.0.0")
    r = py_subprocess(
        "import importlib\n"
        "m1 = importlib.import_module('LiCSBAS_meta')\n"
        "m2 = importlib.import_module('licsbas.meta')\n"
        "assert m1 is m2\n"
        "import LiCSBAS14_vel_std as v\n"
        "assert v.__name__ == 'licsbas.steps._14_vel_std'\n"
        "print('ALIAS_OK')\n"
    )
    assert r.returncode == 0, r.stderr
    assert "ALIAS_OK" in r.stdout


def _step_modules():
    d = os.path.join(REPO, "licsbas", "steps")
    out = []
    for name in sorted(os.listdir(d)):
        if name.endswith(".py") and name != "__init__.py":
            out.append("licsbas.steps." + name[:-3])
    return out


STEPS = _step_modules()


@pytest.mark.parametrize("module", STEPS)
def test_steps_import(module):
    check_import(module)


def test_entry_points_exist_and_resolve():
    import importlib.metadata as md
    try:
        eps = md.entry_points(group="console_scripts")
    except TypeError:  # py<3.10
        eps = md.entry_points().get("console_scripts", [])
    # for --target installs, dist-info is found via sys.path/PYTHONPATH
    script_eps = [e for e in eps if e.name.startswith("licsbas-") and e.value.startswith("licsbas.")]
    must_have = {"licsbas-01-get-geotiff", "licsbas-14-vel-std",
                 "licsbas-check-install", "licsbas-plot-ts"}
    names = {e.name for e in script_eps}
    if not must_have <= names:
        pytest.skip("LiCSBAS distribution metadata not visible "
                    f"(got {len(script_eps)} entry points)")
    assert len(script_eps) >= 50, sorted(names)
    for e in sorted(script_eps, key=lambda x: x.name):
        modname, _, attr = e.value.partition(":")
        code = (
            "import importlib; m = importlib.import_module(%r); "
            "assert hasattr(m, %r); print('EP_OK')"
            % (modname, attr)
        )
        r = py_subprocess(code)
        if r.returncode != 0 and modname in OK_EXIT:
            # expected: clean exit message about a missing optional tool
            out = (r.stdout + r.stderr).lower()
            assert ("not installed" in out or "not found" in out
                    or "not loaded" in out or "licsar_extra" in out), r.stdout
            continue
        assert r.returncode == 0, (e.name, r.stderr)
        assert "EP_OK" in r.stdout


def test_colomaps_bundled():
    r = py_subprocess(
        "from licsbas.colormaps import cmocean, GMT, SCM\n"
        "assert cmocean.ice is not None\n"
        "assert GMT.polar is not None\n"
        "assert SCM.berlin is not None\n"
        "import matplotlib\n"
        "matplotlib.use('Agg')\n"
        "import licsbas.tools_lib as tl\n"
        "cmap = tl.get_cmap('cmocean.ice')\n"
        "assert cmap is not None\n"
        "print('CMAPS_OK')\n"
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "CMAPS_OK" in r.stdout
