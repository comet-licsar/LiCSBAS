#!/usr/bin/env python3
"""Compose the split tutorial notebooks from the original ``tutorial.ipynb``.

Produces (in ``tutorial/``):

* ``tutorial_0.ipynb``        - Module 0, LiCSAR data: steps 0-1 -> 0-5,
                                + the 02to05 re-unwrapping alternative cell
* ``tutorial_0_nisar.ipynb``  - Module 0, NISAR data (experimental)
* ``tutorial_0_sbovl.ipynb``  - SBOVNL (SBOI) chain, steps 0-1 -> 1-6 with --sbovl
* ``tutorial_1.ipynb``        - Module 1: time series, steps 11 -> 16 + viewers

All notebooks share the idempotent setup cell, and are cross-linked so that a
Binder session started on any of them can jump between them with a relative
click (same session) or restart via the badges.

Usage:
    python3 tutorial/build_notebooks.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))

# branch that currently holds the v3 code (switch to "main" once v3 is released)
BRANCH = "towards-v3"
RAW = f"https://raw.githubusercontent.com/comet-licsar/LiCSBAS/{BRANCH}/tutorial"


def _img(name: str, width: str = "100%") -> str:
    return (f'<img src="{RAW}/{name}" width="{width}">'
            f'\n\n*(image not visible? the PNGs also live in `tutorial/{name}`; '
            f'`python3 tutorial/make_flowchart.py` regenerates them)*')


def _nb_link(cell_nb: str, target: str) -> str:
    return (f'**[Continue in `{target}` (opens in this Binder session) '
            f'&raquo;](<{target}>)**')


def _badges(target: str) -> str:
    rel = f"tutorial/{target}"
    return f"""
- [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/comet-licsar/LiCSBAS/HEAD?labpath={rel}) - *new Binder session*
- [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/comet-licsar/LiCSBAS/blob/{BRANCH}/{rel}) - *Colab*
"""


def md(src: str) -> dict:
    return {"cell_type": "markdown",
            "metadata": {},
            "source": src if isinstance(src, list) else src.split("\n")}


def code(src: str) -> dict:
    return {"cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": src if isinstance(src, list) else src.split("\n")}


def load_original_cells():
    nb = json.load(open(os.path.join(HERE, "tutorial.ipynb")))
    return nb["cells"]


def save_nb(path: str, cells: list):
    import uuid
    for i, cell in enumerate(cells):
        if cell.get("cell_type") == "markdown":
            cell.pop("execution_count", None)
        elif cell.get("cell_type") == "code":
            if "outputs" not in cell or cell["outputs"] is None:
                cell["outputs"] = []
            if "execution_count" not in cell:
                cell["execution_count"] = None
        if "id" not in cell:
            cell["id"] = uuid.uuid4().hex
    nb = {"cells": cells, "metadata": {
            "kernelspec": {"display_name": "Python 3 (ipykernel)",
                           "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11.0",
                              "mimetype": "text/x-python",
                              "nbformat": 4, "nbformat_minor": 0,
                              "file_extension": ".py",
                              "pygments_lexer": "ipython3",
                              "codemirror_mode": {"name": "ipython", "version": 3}}},
        "nbformat": 4, "nbformat_minor": 5}
    with open(path, "w") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"[build_notebooks] wrote {os.path.relpath(path, REPO)} "
          f"({len(cells)} cells)")


# ---------------------------------------------------------------------------
# shared cell fragments
# ---------------------------------------------------------------------------
def setup_cell(cells):
    """cell 3 of the original tutorial (idempotent env setup)"""
    return cells[3]


def step_h(entry: str, extra: str = "") -> code:
    return code(f"! licsbas-{entry} {extra}-h".strip())


def main():
    c = load_original_cells()
    assert "# Module 0" in "".join("".join(x["source"]) for x in c[:10])

    # =====================================================================
    # tutorial_0.ipynb  (LiCSAR module 0 + 02to05 alternative)
    # =====================================================================
    n0 = [
        md("""# COMET InSAR Workshop: LiCSBAS Tutorial — **Module 0: dataset preparation (LiCSAR data)**

*A step-by-step tutorial to run LiCSBAS for the time series analysis. This first notebook covers **Module 0** (dataset preparation, steps `0-1` → `0-5`); the time series analysis (steps `11` → `16` + the interactive viewers) lives in [**`tutorial_1.ipynb`**](tutorial_1.ipynb).

> **Other data routes for Module 0**
> - [**NISAR data** (experimental)](tutorial_0_nisar.ipynb) — ALOS-2 L-band NISAR CSL2 GUNW via ASF (per frame)
> - [**SBOVNL / SBOI data**](tutorial_0_sbovl.ipynb) — the `--sbovl` burst-overlap chain (steps `0-1` → `1-6`)"""),
        md(c[1]["source"] if isinstance(c[1]["source"], list) else c[1]["source"]),  # "First, please execute..."
        setup_cell(c),
        md(c[4]["source"]),  # LiCSBAS intro
        md(c[5]["source"]),  # standard workflow fig
        md(c[6]["source"]),  # # Module 0: preparing the dataset
        md("## The processing chain of this module (steps `0-1` → `0-5`, with the **02to05** alternative)\n" + _img("0_licsar.png")),
        # steps 0-1 .. 0-2 (from the original tutor)
        md(c[7]["source"]),
        md(c[8]["source"]),
        md(c[9]["source"]),
        code(c[10]["source"]),
        md(c[11]["source"]),
        md(c[12]["source"]),
        md(c[13]["source"]),
        code(c[14]["source"]),
        # -------- NEW: 02to05 alternative cell (right after 0-2, before 0-3) --------
        md("""## Alternative route: **Step `02to05` — re-unwrapping (substitutes steps `0-2` → `0-5`)**

So far we have consumed *already-unwrapped* data (the normal case, where the interferograms were unwrapped by the data provider).

`LiCSBAS02to05_unwrap.py` is an **alternative route** for cases where the input interferograms are only **wrapped** (`.geo.diff..._pha.tif`, downloaded with `--get_pha`): it performs **the unwrapping itself** and, in a single invocation, carries out *all* of steps `0-2` (multilooking), `0-3` (GACOS, if `--gacos`), `0-4` (masking) and `0-5` (clipping) — i.e. it **substitutes steps `02`–`05`** (see the amber box in the flowchart above).

It unwraps (Goldstein filter, stability/constancy threshold `--thres`, optional cascade re-unwrapping `--cascade`/`--cascade_full`), an optional height-correlation correction (`--hgtcorr`), and produces the same `GEOCml{n}[GACOS][mask][clip]` layout as the standard route (incl. `coherence`, `unw`, `baselines`, `par` files).

> Requires the `unwrap` extra: `pip install licsbas[unwrap]` (uses SNAPHU for some filters)."""),
        code("![-h help] licsbas-02to05-unwrap -h"),
        code("""# EXAMPLE (not run in this tutorial)
# licsbas-02to05-unwrap -i GEOCdir -M 5 --gacos --cascade --thres 0.3
# licsbas-02to05-unwrap -i GEOCdir -M 10 --filter gauss -g 14.00/14.25/40.75/40.95   # + clip
"""),
        md("*In this tutorial we continue with the standard (already-unwrapped) route.*"),
        # steps 0-3 .. 0-5 (from the original)
        md(c[15]["source"]),
        md(c[16]["source"]),
        md(c[17]["source"]),
        md(c[18]["source"]),
        code(c[19]["source"]),
        md(c[20]["source"]),
        md(c[21]["source"]),
        md(c[22]["source"]),
        code(c[23]["source"]),
        md(c[24]["source"]),
        md(c[25]["source"]),
        md(c[26]["source"]),
        code(c[27]["source"]),
        # the data check + ifg plots (original 28..38)
        md(c[28]["source"]),
        md(c[29]["source"]),
        code(c[30]["source"]),
        md(c[31]["source"]),
        code(c[32]["source"]),
        md(c[33]["source"]),
        code(c[34]["source"]),
        md(c[35]["source"]),
        code(c[36]["source"]),
        code(c[37]["source"]),
        code(c[38]["source"]),
        # ---------------- link to module 1 ----------------
        md(f"""## Next step: Module 1 — Time series (steps `11` → `16` + viewers)

{_nb_link('tutorial_0.ipynb', 'tutorial_1.ipynb')}
{_badges('tutorial_1.ipynb')}

*Alternatively, jump to the [NISAR data route](tutorial_0_nisar.ipynb) or the [SBOVNL/SBOI route](tutorial_0_sbovl.ipynb).*"""),
    ]
    save_nb(os.path.join(HERE, "tutorial_0.ipynb"), n0)

    # =====================================================================
    # tutorial_0_nisar.ipynb  (NISAR module 0, experimental)
    # =====================================================================
    n0n = [
        md("""# COMET InSAR Workshop: LiCSBAS Tutorial — **Module 0: dataset preparation (NISAR data, experimental)**

*This notebook is the **NISAR data route** of Module 0: data access (ASF search + download of NISAR CSL2 `GUNW` products), conversion to the LiCSBAS `GEOC/` layout, and then the *same* steps `0-2` → `0-5` as in [the LiCSAR tutorial](tutorial_0.ipynb). The time series part is shared: [**`tutorial_1.ipynb`**](tutorial_1.ipynb).*

> **What is NISAR?** — NISAR / ALOS-2 is a *dual-frequency (L + P band)* radar satellite. The NISAR CSL2 products distributed by ASF are **interferograms (GUNW)** in `.h5` (HDF5) format, organized into **frames (tracks)**. LiCSBAS uses **GUNW only** — GSLC is not needed.
>
> **Frames:** a region is usually covered by *several* frames, and each frame is a self-contained time series that must be processed **separately** (do not combine frames; `nisar2geoc` even warns if the input mixes them).
>
> **Why experimental?** — this chain is new (LiCSBAS v3), and requires the optional extras `licsar_extra[nisar]` + `licsbas[nisar]` (rasterio, rioxarray, dask, xarray, pyproj, h5py, statsmodels; plus `snaphu` for the L-band unwrapping used by the data provider). The steps degrade gracefully (`-h` works everywhere; the heavy imports are lazy).
>
> Full documentation: [`docs/05_nisar.md`](../docs/05_nisar.md)."""),
        md(c[1]["source"]),
        setup_cell(c),
        md("## The processing chain of this module (NISAR route)\n" + _img("0_nisar.png")),
        # ------------- step 0-1n: ASF search + download -------------
        md("""## Step 0-1 (NISAR): **search ASF + download NISAR GUNW** — `LiCSBAS01_get_NISAR_data.py`

Searches [ASF](https://asf.alaska.edu) for NISAR CSL2 GUNW over a bbox and streams them (via an ASF session, no shell `wget`) into **per-frame subfolders** (the NISAR frame id, e.g. `018A_01234`):

```
WORKdir/NISAR_GUNW/
├── 018A_01234/
│   ├── 20250101_20250117.h5
│   └── 20250117_20250133.h5
└── 019A_01235/...
```

Useful options (see `-h` for all):
- `--list-frames` — show the available frames + how many GUNW per frame, *then exit (no download)*;
- `--frame 018A_01234[, 018A_01235, ...]` — download **only** the selected frame(s).

> **Prerequisite:** `pip install licsar_extra[nisar]` (the `nisar_data` module with ASF search + download). The `-h` below works even without it.
>
> **One frame per time series** — each frame folder is its own LiCSBAS dataset (its own `GEOC/`), processed with the steps below and with the time series module."""),
        code("![-h help] licsbas-01-get-nisar-data -h"),
        code("""# EXAMPLES (not run in this tutorial — needs the NISAR deps)
# 1) which frames are available here? (no download)
# licsbas-01-get-nisar-data -g 14.00/14.25/40.75/40.95 --list-frames
# 2) dry-run: what would be downloaded (all frames in the bbox)
# licsbas-01-get-nisar-data -g 14.00/14.25/40.75/40.95 -s 20250101 --dry_run
# 3) download one frame only
# licsbas-01-get-nisar-data -o NISAR_GUNW -g 14.00/14.25/40.75/40.95 --frame 018A_01234 -s 20250101"""),
        # ------------- nisar2geoc -------------
        md("""## NISAR → GEOC conversion — `LiCSBAS_nisar2geoc.py`

One **frame folder** is converted to the LiCSBAS `GEOC/<ifg>/...` layout; from `02` onwards the chain is identical to the LiCSAR route:

- each IFG: `.geo.unw.tif` / `.geo.cc.tif`, with the smooth **ionospheric ramp** and the **range-offset (pixel-offset) ramp** removed *before* writing (following `earthquake_responder.py`), then the coherence mask (default threshold `0.5`);
- top-level files, **written once** from the first GUNW of the frame: `X.geo.E.tif`/`X.geo.N.tif`/`X.geo.U.tif` (from the GUNW's own `radarGrid` metadata) and — with `-D` — `X.geo.hgt.tif` (best-effort NISAR DEM);
- the standard **`baselines`** file (per-IFG perpendicular baseline) and a `metadata.txt` (`center_time`, `radar_freq`);
- **all GeoTIFFs share one WGS-84 grid** (the first IFG defines it, `rasterio` export; the others are re-registered onto it).

> **Do not mix frames (tracks)** — point `-i` at a *single frame* folder (one `GEOC/` per time series). `nisar2geoc` prints a warning if the input GUNWs span more than one frame."""),
        code("![-h help] licsbas-nisar2geoc -h"),
        code("""# EXAMPLES (not run in this tutorial — needs NISAR .h5 input + the NISAR deps)
# one frame (track) per GEOC:
# licsbas-nisar2geoc -i NISAR_GUNW/018A_01234 -o GEOC_018A_01234 -t 0.5
# licsbas-nisar2geoc -i NISAR_GUNW/018A_01234 -o GEOC_018A_01234 -D    # also write hgt (best-effort DEM)
# licsbas-nisar2geoc -i NISAR_GUNW/018A_01234 -o GEOC --no_iono --no_offsets --no_deramp_quad --dry_run"""),
        md("## (alternative, GeoTIFF input) — `LiCSBAS_asf2geoc.py`\n\n`![-h help] licsbas-asf2geoc -h`"),
        # ------------- steps 0-2 .. 0-5 (same as LiCSAR) -------------
        md("""## Steps `0-2` → `0-5`: **identical to the LiCSAR route**

From here on the chain is exactly the one in [the LiCSAR tutorial](tutorial_0.ipynb) — the same steps, the same flags:"""),
        md(c[11]["source"]),
        md(c[12]["source"]),
        code(c[14]["source"]),
        md(c[15]["source"]),
        md(c[18]["source"]),
        code(c[19]["source"]),
        md(c[20]["source"]),
        code(c[23]["source"]),
        md(c[24]["source"]),
        code(c[27]["source"]),
        # ------------- link to module 1 -------------
        md(f"""## Next step: Module 1 — Time series (steps `11` → `16` + viewers)

The time series analysis (`LiCSBAS11` → `LiCSBAS16`) is **independent of the data source** — continue in [**`tutorial_1.ipynb`**](tutorial_1.ipynb).

{_nb_link('tutorial_0_nisar.ipynb', 'tutorial_1.ipynb')}
{_badges('tutorial_1.ipynb')}

*Other Module-0 routes: [LiCSAR data](tutorial_0.ipynb) · [SBOVNL/SBOI](tutorial_0_sbovl.ipynb) · more NISAR details in [`docs/05_nisar.md`](../docs/05_nisar.md)*"""),
    ]
    save_nb(os.path.join(HERE, "tutorial_0_nisar.ipynb"), n0n)

    # =====================================================================
    # tutorial_0_sbovl.ipynb  (SBOVNL/SBOI chain)
    # =====================================================================
    n0s = [
        md("""# COMET InSAR Workshop: LiCSBAS Tutorial — **SBOVNL (SBOI) data processing** (`--sbovl` chain)

*SBOVNL (burst-overlap Very short (baseline) Network) is an **alternative data product and referencing scheme** based on S-1 *burst* overlaps. It runs as a *separate chain*: download (s)bovl data with `--sbovl`, multilook it, then run the time series steps `11` → `16` **all with `--sbovl`** (the referencing in `120` is forced on, and classic loop closure `12` is skipped).

This notebook covers the **whole** SBOVNL chain (steps `0-1` → `1-6`) because *both* modules differ from the standard route. For the standard LiCSAR route see [Module 0](tutorial_0.ipynb) + [Module 1](tutorial_1.ipynb)."""),
        md(c[1]["source"]),
        setup_cell(c),
        md("## The SBOVNL processing chain (steps `0-1` → `1-6`, all with `--sbovl`)\n\n\n" + _img("0_sbovl.png", "65%")),
        # ------------- step 0-1 sbovl -------------
        md("""## Step 0-1: **download SBOVNL data** — `LiCSBAS01_get_geotiff.py --sbovl`

Same download step as the standard route, but with `--sbovl` it pulls the **(s)bovl** products from the portal instead of the unwrapped data (and, optionally, the *azimuth iono/tides* that `131` will use):

```
[- yyyymmdd_yyyymmdd.geo.s(bovldiff).adf.mm.tif] (if --sbovl is used)
[- yyyymmdd_yyyymmdd.geo.s(bovldiff).adf.cc.tif] (if --sbovl is used)
```"""),
        code("![-h help] licsbas-01-get-geotiff -h"),
        code("""# EXAMPLE (SBOVNL: note --sbovl, and the azi iono/tides if you want step 131)
# licsbas-01-get-geotiff -f 022D_04826_121209 --sbovl --get_iono --get_tides"""),
        # ------------- step 0-2 sbovl -------------
        md("""## Step 0-2: **multilook the SBOVNL data** — `LiCSBAS02_ml_prep.py --sbovl`

Multilooking on the (s)bovl `.mm`/`.cc` pairs. Convention: put the SBOVNL output in a **separate** dir, e.g. `GEOC_BOVL_ml5` (it must *not* overwrite the standard `GEOCml5`):

```
LiCSBAS02_ml_prep.py -i GEOCdir -o GEOC_BOVL_ml5 -n 5 --sbovl
```"""),
        code("""![-h help] licsbas-02-ml-prep -h

# EXAMPLE
# licsbas-02-ml-prep -i GEOCdir -o GEOC_BOVL_ml5 -n 5 --sbovl"""),
        # ------------- steps 0-3..0-5 optional -------------
        md("""## Optional steps `0-3` → `0-5` (GACOS / mask / clip)

The optional `GACOS` correction, the coherence mask and the clipping are **exactly as in the standard [Module-0 tutorial](tutorial_0.ipynb)** — they are not part of the SBOVNL scheme itself, and are typically *skipped* for (s)bovl (the scheme is already referenced on very short baselines)."""),
        # ------------- step 1-1 sbovl -------------
        md("""## Step 1-1: **quality check** — `LiCSBAS11_check_unw.py --sbovl`

Checks the (s)bovl stack for coherence/unwrapping outliers and prepares the TS dir. With `--sbovl` this step **forces the reference selection (step `120`) on**, because (s)bovl data are already referenced on the *overlap* (no classic re-referencing on a stable point).

> In the SBOVNL chain, step `12` (loop closure) is **skipped** — the re-referencing is done on the very-short-overlap network instead."""),
        code("""![-h help] licsbas-11-check-unw -h

# EXAMPLE
# licsbas-11-check-unw -d GEOC_BOVL_ml5 -t TS_GEOC_BOVL_ml5 --sbovl -c 0.05 -u 0.3"""),
        # ------------- step 1-2 (120) sbovl -------------
        md("""## Step 1-2: **choose the (s)bovl reference point** — `LiCSBAS120_choose_reference.py --sbovl`

Used (and forced) in the SBOVNL chain to pick/reference a *stable point* within the (s)bovl network (it builds the TS reference on the very-short baselines):

```
LiCSBAS120_choose_reference.py -c GEOC_BOVL_ml5 -d GEOC_BOVL_ml5 -t TS_... --sbovl
```"""),
        code("""![-h help] licsbas-120-choose-reference -h

# EXAMPLE
# licsbas-120-choose-reference -c GEOC_BOVL_ml5 -d GEOC_BOVL_ml5 -t TS_GEOC_BOVL_ml5 --sbovl"""),
        # ------------- step 1-3 sbovl -------------
        md("""## Step 1-3: **SBOVNL inversion** — `LiCSBAS13_sb_inv.py --sbovl` (or `--sbovl_abs`)

Two flavours:

- `--sbovl` — inversion of the (s)bovl `mm` + `cc` values (the network is already close-referenced; *no re-referencing is done here*).
- `--sbovl_abs` — **SBOI absolute**: recompute the *absolute* velocity (the reference/correction steps are skipped); afterwards `LiCSBAS131_boi_absolute.py` can apply the **ICC + ESD** offset and the absolute SET/Iono corrections.

```
LiCSBAS13_sb_inv.py -d GEOC_BOVL_ml5 -t TS_GEOC_BOVL_ml5 --sbovl
LiCSBAS13_sb_inv.py -d GEOC_BOVL_ml5 -t TS_GEOC_BOVL_ml5 --sbovl_abs
```"""),
        code("""![-h help] licsbas-13-sb-inv -h

# EXAMPLES
# licsbas-13-sb-inv -d GEOC_BOVL_ml5 -t TS_GEOC_BOVL_ml5 --sbovl
# licsbas-13-sb-inv -d GEOC_BOVL_ml5 -t TS_GEOC_BOVL_ml5 --sbovl_abs --mem_size 8000"""),
        # ------------- steps 1-4 -> 1-6 sbovl -------------
        md("""## Steps 1-4 → 1-6: **velocity STD / mask / filter (all `--sbovl`)**

The same three steps as Module 1, but run with `--sbovl` (and, on the *absolute* chain, `--sbovl_abs`). For the full flag reference + the interactive viewers, see [**Module 1 →**](tutorial_1.ipynb)."""),
        code("""![-h help] licsbas-14-vel-std -h
# EXAMPLE
# licsbas-14-vel-std -t TS_GEOC_BOVL_ml5 --sbovl --mem_size 4000"""),
        code("""![-h help] licsbas-15-mask-ts -h
# EXAMPLE (sbovl thresholds differ from the standard ones)
# licsbas-15-mask-ts -t TS_GEOC_BOVL_ml5 --sbovl -c 0.05 -u 0.5 -g 50 -s 10 -i 1000"""),
        code("""![-h help] licsbas-16-filt-ts -h
# EXAMPLE
# licsbas-16-filt-ts -t TS_GEOC_BOVL_ml5 --sbovl -r 1"""),
        # ------------- viewers + links -------------
        md(f"""## Viewers & exports

The interactive `plot-ts`/`out2nc`/`net2tif` viewer cells from [Module 1](tutorial_1.ipynb) work on a SBOVNL `TS_...` dir exactly as on a standard one.

**Other routes:** [Module 0 — LiCSAR data](tutorial_0.ipynb) · [Module 0 — NISAR data](tutorial_0_nisar.ipynb) · [Module 1 — Time series (standard)](tutorial_1.ipynb)

{_nb_link('tutorial_0_sbovl.ipynb', 'tutorial_1.ipynb')}
{_badges('tutorial_1.ipynb')}"""),
    ]
    save_nb(os.path.join(HERE, "tutorial_0_sbovl.ipynb"), n0s)

    # =====================================================================
    # tutorial_1.ipynb  (module 1: TS, cells 39.. of the original)
    # =====================================================================
    n1 = [
        md("""# COMET InSAR Workshop: LiCSBAS Tutorial — **Module 1: time series** (steps `11` → `16` + viewers)

*This notebook continues [Module 0 (dataset preparation)](tutorial_0.ipynb) with the **time series analysis** (steps `11` → `16`) and the **interactive viewers** / NetCDF & GeoTIFF exports. It is **data-source agnostic**: it works on the stack produced by any Module-0 route — [LiCSAR data](tutorial_0.ipynb), [NISAR data](tutorial_0_nisar.ipynb), or the [SBOVNL/SBOI chain](tutorial_0_sbovl.ipynb) (which uses `--sbovl` on these same steps).*

We run it here on the **pre-processed** `GEOCml2GACOSclip` stack (Campi Flegrei, 2016–2021) that is already in the session, so every step is a live example. Steps are marked **(skipping)** where the heavy processing is only shown via `-h`."""),
        md("## The time series chain (steps `11` → `16`, then the viewers)\n" + _img("1_ts.png")),
    ] + c[39:]
    # the original module-1 block already starts with "# Running basic time-series analysis"
    save_nb(os.path.join(HERE, "tutorial_1.ipynb"), n1)

    # =====================================================================
    print("\n[build_notebooks] done. New notebooks:")
    for f in ["tutorial_0.ipynb", "tutorial_0_nisar.ipynb",
              "tutorial_0_sbovl.ipynb", "tutorial_1.ipynb"]:
        p = os.path.join(HERE, f)
        if os.path.exists(p):
            print(f"  tutorial/{f}  ({os.path.getsize(p):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
