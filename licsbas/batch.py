"""Python batch processor for LiCSBAS (replacement for ``batch_LiCSBAS.sh``).

This module ports the settings/flags of the legacy ``batch_LiCSBAS.sh`` into
a plain Python configuration object (:class:`BatchConfig`) and builds the
list of processing steps to run (:func:`build_pipeline`). Steps are executed
in-process through the updated ``licsbas.steps.*`` modules (v3 package
layout), so no PATH-based ``LiCSBAS*.py`` wrappers are required anymore.

Quick usage
-----------
>>> from licsbas.batch import BatchConfig, run_batch
>>> cfg = BatchConfig()                       # standard chain, 01 -> 16
>>> run_batch(cfg, dry_run=True)              # print commands only
>>> run_batch(cfg)                            # actually run the chain

A PNG flowchart of the chain can be written with :func:`save_flowchart`.

Command line (also installed as ``licsbas-batch``):
    python -m licsbas.batch --check-only [--start 11 --end 16] [--sbovl] ...
"""
from __future__ import annotations

import importlib
import inspect
import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import List, Optional

__all__ = ["BatchConfig", "BatchStep", "build_pipeline", "run_batch",
           "save_flowchart", "make_config", "list_workflows",
           "register_workflow", "main"]

# ---------------------------------------------------------------------------
# Step / pipeline data structures
# ---------------------------------------------------------------------------

# legacy step id -> (module inside licsbas.steps or licsbas.scripts, legacy script name for logs)
_STEP_MODULES = {
    "01":         ("licsbas.steps._01_get_geotiff",            "LiCSBAS01_get_geotiff.py"),
    "02":         ("licsbas.steps._02_ml_prep",                "LiCSBAS02_ml_prep.py"),
    "02to05":     ("licsbas.steps._02to05_unwrap",             "LiCSBAS02to05_unwrap.py"),
    "03":         ("licsbas.steps._03op_gacos",                "LiCSBAS03op_GACOS.py"),
    "04":         ("licsbas.steps._04op_mask_unw",             "LiCSBAS04op_mask_unw.py"),
    "05":         ("licsbas.steps._05op_clip_unw",             "LiCSBAS05op_clip_unw.py"),
    "06":         ("licsbas.steps._03op_era5",                 "LiCSBAS03op_ERA5.py"),
    "11":         ("licsbas.steps._11_check_unw",              "LiCSBAS11_check_unw.py"),
    "120":        ("licsbas.steps._120_choose_reference",      "LiCSBAS120_choose_reference.py"),
    "12":         ("licsbas.steps._12_loop_closure",           "LiCSBAS12_loop_closure.py"),
    "13":         ("licsbas.steps._13_sb_inv",                 "LiCSBAS13_sb_inv.py"),
    "131abs":     ("licsbas.steps._131_boi_absolute",          "LiCSBAS131_boi_absolute.py"),
    "131corr":    ("licsbas.steps._131_corrections",           "LiCSBAS131_corrections.py"),
    "14":         ("licsbas.steps._14_vel_std",                "LiCSBAS14_vel_std.py"),
    "15":         ("licsbas.steps._15_mask_ts",                "LiCSBAS15_mask_ts.py"),
    "16":         ("licsbas.steps._16_filt_ts",                "LiCSBAS16_filt_ts.py"),
    "eqoffs":     ("licsbas.scripts._get_eqoffsets",         "LiCSBAS_get_eqoffsets.py"),
    "residcheck": ("licsbas.scripts._resid_check",           "LiCSBAS_resid_check.py"),
    # NISAR data-access route (alternative to the LiCSAR step-01 download)
    "01nisar":    ("licsbas.steps._01_get_nisar_data",        "LiCSBAS01_get_NISAR_data.py"),
    "nisar2geoc": ("licsbas.scripts._nisar2geoc",             "LiCSBAS_nisar2geoc.py"),
    "asf2geoc":   ("licsbas.scripts._asf2geoc",               "LiCSBAS_asf2geoc.py"),
}

_PHASES = {
    "01": "Download & data preparation (steps 01-06)",
    "02": "Download & data preparation (steps 01-06)",
    "02to05": "Download & data preparation (steps 01-06)",
    "03": "Download & data preparation (steps 01-06)",
    "04": "Download & data preparation (steps 01-06)",
    "05": "Download & data preparation (steps 01-06)",
    "06": "Download & data preparation (steps 01-06)",
    "11": "Time-series estimation (steps 11-13)",
    "120": "Time-series estimation (steps 11-13)",
    "12": "Time-series estimation (steps 11-13)",
    "13": "Time-series estimation (steps 11-13)",
    "131abs": "Time-series estimation (steps 11-13)",
    "131corr": "Time-series estimation (steps 11-13)",
    "eqoffs": "Time-series estimation (steps 11-13)",
    "residcheck": "Time-series estimation (steps 11-13)",
    "14": "Velocity, masking & filtering (steps 14-16)",
    "15": "Velocity, masking & filtering (steps 14-16)",
    "16": "Velocity, masking & filtering (steps 14-16)",
    "01nisar": "NISAR data access (01-nisar)",
    "nisar2geoc": "GEOC conversion (nisar2geoc)",
    "asf2geoc": "GEOC conversion (asf2geoc)",
}


@dataclass
class BatchStep:
    """One executable step of the chain."""
    key: str                 # internal key, e.g. "13" or "02to05"
    name: str                # legacy script name used for logging/flowchart
    module: str              # licsbas.steps._XX or licsbas.scripts._XX
    argv: List[str]          # command line arguments (without the name)
    optional: bool = False   # True = optional step (shown grey in flowchart if off)
    note: str = ""           # extra annotation for the flowchart
    phase: str = ""          # flowchart cluster


# ---------------------------------------------------------------------------
# Configuration (mirrors the settings section of batch_LiCSBAS.sh)
# ---------------------------------------------------------------------------

@dataclass
class BatchConfig:
    """Settings for :func:`build_pipeline` / :func:`run_batch`.

    All defaults reproduce the historical defaults of ``batch_LiCSBAS.sh``
    (standard chain, ``sbovl="n"``, optional steps 03-06 off, ...).
    """
    # --- run range -------------------------------------------------------
    start_step: int = 1                  # 1-16
    end_step: int = 16                   # 1-16
    nlook: int = 1                       # multilook factor, used in step 02
    check_only: bool = False             # y/n: only print the commands
    n_para: Optional[int] = None         # None: number of usable CPUs
    gpu: bool = False                    # y/n

    # --- misc ------------------------------------------------------------
    freq: Optional[str] = None           # default: 5.405e9 Hz
    logdir: str = "log"

    # --- processing switches --------------------------------------------
    sbovl: bool = False                  # SBOI/SBOVL processing chain
    sbovl_abs: bool = False              # close referencing + ICC/ESD offsets + abs SET/Iono corr (SBOI)
    cometdev: bool = False               # COMET experimental functions (not recommended)
    eqoffs: bool = False                 # earthquake offsets (get_eqoffsets + inversion)
    eqoffs_minmag: float = 0.0           # 0 = skip auto-find
    eqoffs_txtfile: str = "eqoffsets.txt"
    eqoffs_buffer: float = 0.1

    # --- updated pipeline: re-unwrapping with 02to05 ---------------------
    run_reunw: bool = False              # use LiCSBAS02to05_unwrap.py instead of 02[,03,04,05]
    p02to05_gacos: bool = False          # use GACOS data if available
    p02to05_hgtcorr: bool = False        # recommended for high, varying topography
    p02to05_cascade: bool = False        # cascade from higher ML factor
    p02to05_filter: str = ""             # gold / gauss / adf (default gold)
    p02to05_thres: str = ""              # default 0.35
    p02to05_cliparea_geo: str = ""       # e.g. 130.11/131.12/34.34/34.6
    p02to05_op_GEOCdir: str = ""         # default: GEOC

    # --- NISAR data access (alternative to the LiCSAR step-01 download) ---
    # When enabled, LiCSAR step 01 is replaced by:
    #   01nisar  = licsbas-01-get-nisar-data (ASF search + download of NISAR GUNW .h5,
    #             per frame; --list-frames / --frame supported)
    #   nisar2geoc = licsbas-nisar2geoc (.h5 -> LiCSBAS GEOC/ layout, iono+offsets
    #                corrected, shared WGS-84 grid, baselines + metadata.txt)
    # Steps 02-16 then run exactly as for LiCSAR data.
    use_nisar: bool = False
    pNISAR_bbox: str = ""                # -g  lon1/lon2/lat1/lat2 (needed if use_nisar)
    pNISAR_frames: str = ""              # --frame FID[,FID2,...] (optional; e.g. 018A_01234)
    pNISAR_start_date: str = ""          # -s  yyyymmdd (default 20250101)
    pNISAR_end_date: str = ""            # -e  yyyymmdd (default today)
    pNISAR_outdir: str = ""              # -o  (default ./NISAR_GUNW)
    pNISAR_max: str = ""                 # --max scenes (default 500)
    nisar2geoc_freq: str = ""            # nisar2geoc -f A|B (empty = keep scene's band)
    nisar2geoc_cc_thre: str = "0.5"      # nisar2geoc -t coherence mask threshold
    nisar2geoc_no_iono: bool = False     # --no_iono
    nisar2geoc_no_offsets: bool = False  # --no_offsets
    nisar2geoc_no_deramp_quad: bool = False  # --no_deramp_quad
    nisar2geoc_download_dem: bool = False    # -D (try to fetch a NISAR DEM)

    # --- optional steps 03-06 ---------------------------------------------
    order_op03_05: List[int] = field(default_factory=lambda: [3, 4, 5, 6])
    do03op_GACOS: bool = False
    do04op_mask: bool = False
    do05op_clip: bool = False
    do06op_ERA5: bool = False
    p03_gacosdir: str = "GACOS"
    p03_fillhole: bool = True
    p04_mask_coh_thre_avg: str = ""
    p04_mask_coh_thre_ifg: str = ""
    p04_mask_range: str = ""
    p05_clip_range: str = ""
    p05_clip_range_geo: str = ""
    p06_era5dir: str = "ERA5"
    p06_fillhole: bool = True

    # --- step 01 -----------------------------------------------------------
    p01_frame: str = ""
    p01_start_date: str = ""             # default 20141001
    p01_end_date: str = ""               # default today
    p01_minbtemp: str = ""
    p01_maxbtemp: str = ""
    p01_get_gacos: bool = False
    p01_get_era5: bool = False
    p01_get_iono: bool = False
    p01_get_tides: bool = False
    p01_get_pha: bool = False            # forced "y" when run_reunw
    p01_get_mli: bool = False            # forced "y" when run_reunw
    p01_skip_unw: bool = False
    p01_rngoff: bool = False

    # --- step 02 ------------------------------------------------------------
    p02_GEOCdir: str = ""                # default GEOC
    p02_GEOCmldir: str = ""              # default GEOCml{nlook}
    p02_freq: str = ""
    p02_rngoff: bool = False

    # --- steps 11-13 ---------------------------------------------------------
    p11_GEOCmldir: str = ""
    p11_TSdir: str = ""
    p11_unw_thre: str = ""               # default 0.3
    p11_coh_thre: str = ""               # default 0.05
    p11_s_param: bool = False
    p11_minbtemp: str = ""
    p11_maxbtemp: str = ""

    p120_use: bool = False
    p120_ignoreconncomp: bool = False

    p12_GEOCmldir: str = ""
    p12_TSdir: str = ""
    p12_loop_thre: str = ""              # default 1.5 rad
    p12_multi_prime: bool = True         # "y" recommended
    p12_nullify: bool = False            # "y" recommended
    p12_nullify_fix_ref: bool = False
    p12_rm_ifg_list: str = ""
    p12_skippngs: bool = False

    p13_GEOCmldir: str = ""
    p13_TSdir: str = ""
    p13_inv_alg: str = ""                # LS (default) or WLS
    p13_mem_size: str = ""               # default 8000 MB
    p13_gamma: str = ""                  # default 0.0001
    p13_inputunit: str = ""              # rad by default
    p13_n_unw_r_thre: str = ""
    p13_keep_incfile: bool = False
    p13_ignore_nullification: bool = False
    p13_nullify_noloops: bool = False
    p13_singular: bool = False
    p13_singular_gauss: bool = False
    p13_skippngs: bool = False
    p13resid_rerun: bool = False         # sbovl iterative rerun (identify & drop high-RMS ifgs)

    # corrections after step 13
    p131_sbovl_model: bool = True        # use RANSAC model directly (sbovl_abs path)
    p131_tide: bool = False
    p131_iono: bool = False
    p131_gacos: bool = False

    # --- steps 14-16 --------------------------------------------------------
    p14_TSdir: str = ""
    p14_mem_size: str = ""               # default 4000 MB

    p15_TSdir: str = ""
    p15_coh_thre: str = ""               # default 0.05
    p15_n_unw_r_thre: str = ""           # default 1.5
    p15_vstd_thre: str = ""              # default 100 mm/yr
    p15_maxTlen_thre: str = "1"          # default 1 yr
    p15_n_gap_thre: str = ""             # default 10
    p15_stc_thre: str = ""               # default 10 mm
    p15_n_ifg_noloop_thre: str = ""      # default 500
    p15_n_loop_err_thre: str = ""        # default 5
    p15_n_loop_err_ratio_thre: str = ""  # default 0.7
    p15_resid_rms_thre: str = ""         # default 15 mm
    p15_avg_phasebias: str = ""          # not used by default
    p15_n_gap_use_merged: bool = True
    p15_vmin: str = ""
    p15_vmax: str = ""
    p15_keep_isolated: bool = False
    p15_noautoadjust: bool = False

    p16_TSdir: str = ""
    p16_filtwidth_km: str = ""           # default 2
    p16_filtwidth_yr: str = ""           # default avg_interval*3
    p16_deg_deramp: str = ""             # 1, bl, or 2
    p16_demerr: bool = False
    p16_hgt_linear: bool = False
    p16_hgt_min: str = ""                # default 200
    p16_hgt_max: str = ""                # default 10000
    p16_range: str = ""
    p16_range_geo: str = ""
    p16_ex_range: str = ""
    p16_ex_range_geo: str = ""
    p16_interpolate_nans: bool = True
    p16_nomask: bool = False
    p16_skippngs: bool = False

    # ------------------------------------------------------------------
    @property
    def GEOCmldir(self) -> str:
        """Base GEOC multilook directory (before optional suffixes)."""
        return f"GEOCml{self.nlook}"

    def __post_init__(self):
        # historical behaviour: sbovl forces use of step 120
        if self.sbovl and not self.p120_use:
            self.p120_use = True


# ---------------------------------------------------------------------------
# Predefined workflow templates
# ---------------------------------------------------------------------------
# A workflow is a named factory producing a BatchConfig: a stable, reusable
# starting point (e.g. "reunw_5" = re-unwrapping with multilook 5).
# New templates can be registered at runtime or in project-local scripts:
#
#     from licsbas.batch import register_workflow, BatchConfig
#
#     @register_workflow("my_study", "study-specific chain")
#     def _():
#         return BatchConfig(sbovl=True, nlook=10, p01_start_date="20141001")

_WORKFLOWS: dict = {}


def register_workflow(name: str, description: str = ""):
    """Register a factory (name -> BatchConfig) under ``name``."""
    def deco(fn):
        _WORKFLOWS[name] = (description, fn)
        return fn
    return deco


def list_workflows() -> dict:
    """``{name: description}`` of all registered workflows."""
    return {n: d for n, (d, _) in _WORKFLOWS.items()}


def make_config(workflow: str = "standard", **overrides) -> BatchConfig:
    """Create a :class:`BatchConfig` from a named workflow template.

    Any ``BatchConfig`` field may be overridden, e.g.
    ``make_config("reunw_5", nlook=10, start_date...)``.
    """
    if workflow not in _WORKFLOWS:
        raise ValueError(f"unknown workflow '{workflow}'; "
                         f"known: {', '.join(sorted(_WORKFLOWS))}")
    cfg = _WORKFLOWS[workflow][1]()
    for k, v in overrides.items():
        if not hasattr(cfg, k):
            raise ValueError(f"'BatchConfig' has no field '{k}'")
        setattr(cfg, k, v)
    return cfg


@register_workflow("standard",
                   "standard chain 01->16 (historical batch_LiCSBAS.sh defaults)")
def _wf_standard():
    return BatchConfig()


@register_workflow("reunw_5",
                   "re-unwrapping via LiCSBAS02to05_unwrap.py, multilook 5")
def _wf_reunw_5():
    return BatchConfig(run_reunw=True, nlook=5)


@register_workflow("reunw_10",
                   "re-unwrapping via LiCSBAS02to05_unwrap.py, multilook 10")
def _wf_reunw_10():
    return BatchConfig(run_reunw=True, nlook=10)

@register_workflow("reunw_cascade",
                   "re-unwrapping via LiCSBAS02to05_unwrap.py, cascading towards multilook 1")
def _wf_reunw_cascade():
    return BatchConfig(run_reunw=True, nlook=1, p02to05_cascade=True)

@register_workflow("sbovl",
                   "SBOI chain (--sbovl options)")
def _wf_sbovl():
    return BatchConfig(sbovl=True)


@register_workflow("sbovl_abs",
                   "SBOI absolute chain (sbovl + sbovl_abs)")
def _wf_sbovl_abs():
    return BatchConfig(sbovl=True, sbovl_abs=True)


@register_workflow("nisar",
                   "NISAR chain: 01-get-nisar-data + nisar2geoc -> 02-05 -> 11-16 "
                   "(set pNISAR_bbox!)")
def _wf_nisar():
    return BatchConfig(
        use_nisar=True,
        nlook=10,
        # pNISAR_bbox="14.00/14.25/40.75/40.95",   # e.g. Campi Flegrei - set to your AOI
    )


# ---------------------------------------------------------------------------
# Pipeline construction
# ---------------------------------------------------------------------------

def _add(argv: List[str], flag: str, value:
         object) -> List[str]:
    """Append ``flag value`` only when ``value`` is non-empty."""
    if value not in (None, ""):
        argv.extend([str(flag), str(value)])
    return argv


def build_pipeline(cfg: BatchConfig) -> List[BatchStep]:
    """Translate :class:`BatchConfig` into the ordered list of steps."""
    steps: List[BatchStep] = []
    geocmldir = cfg.GEOCmldir
    start, end = int(cfg.start_step), int(cfg.end_step)

    sbovl = cfg.sbovl
    p = _STEP_MODULES

    def add(key: str, argv: List[str], optional: bool = False, note: str = ""):
        module, name = p[key]
        steps.append(BatchStep(key=key, name=name, module=module,
                               argv=list(argv), optional=optional, note=note,
                               phase=_PHASES[key]))

    # ---------------- step 01 ----------------
    if start <= 1 <= end and not cfg.use_nisar:
        argv: List[str] = []
        _add(argv, "-f", cfg.p01_frame)
        _add(argv, "-s", cfg.p01_start_date)
        _add(argv, "-e", cfg.p01_end_date)
        if cfg.n_para:
            argv += ["--n_para", str(cfg.n_para)]
        _add(argv, "--minbtemp", cfg.p01_minbtemp)
        _add(argv, "--maxbtemp", cfg.p01_maxbtemp)
        if sbovl:
            argv.append("--sbovl")
        if cfg.p01_rngoff:
            argv.append("--rngoff")
        if cfg.p01_get_gacos:
            argv.append("--get_gacos")
        if cfg.p01_get_era5:
            argv.append("--get_era5")
        if cfg.p01_get_iono:
            argv.append("--get_iono")
        if cfg.p01_get_tides:
            argv.append("--get_tides")
        if cfg.p01_get_pha or cfg.run_reunw:
            argv.append("--get_pha")
        if cfg.p01_get_mli or cfg.run_reunw:
            argv.append("--get_mli")
        if cfg.p01_skip_unw:
            argv.append("--skip_unw")
        add("01", argv, note="reunw: also downloads pha & mli" if cfg.run_reunw else "")

    # ---------------- NISAR data access (alternative to step 01) ------------
    if cfg.use_nisar and start <= 1 <= end:
        if not cfg.pNISAR_bbox:
            print("WARNING: use_nisar is set but pNISAR_bbox (-g lon1/lon2/lat1/lat2) "
                  "is empty; the search will have no search area.", flush=True)
        argv: List[str] = []
        if cfg.pNISAR_bbox:
            argv += ["-g", cfg.pNISAR_bbox]
        _add(argv, "--frame", cfg.pNISAR_frames)
        _add(argv, "-s", cfg.pNISAR_start_date)
        _add(argv, "-e", cfg.pNISAR_end_date)
        _add(argv, "-o", cfg.pNISAR_outdir)
        _add(argv, "--max", cfg.pNISAR_max)
        add("01nisar", argv, note="ASF search + NISAR GUNW .h5 download (per frame; one frame per time series)")

        argv = []
        # one frame per time series: if exactly one frame is selected, point -i at
        # its subfolder; otherwise -i is the download dir (nisar2geoc will warn
        # if the GUNWs span several frames).
        _in_dir = cfg.pNISAR_outdir or "NISAR_GUNW"
        _fids = [f for f in cfg.pNISAR_frames.replace(",", " ").split() if f.strip()]
        if len(_fids) == 1:
            _in_dir = os.path.join(_in_dir, _fids[0])
        argv = ["-i", _in_dir]
        _add(argv, "-f", cfg.nisar2geoc_freq)
        _add(argv, "-t", cfg.nisar2geoc_cc_thre)
        if cfg.nisar2geoc_download_dem:
            argv.append("-D")
        if cfg.nisar2geoc_no_iono:
            argv.append("--no_iono")
        if cfg.nisar2geoc_no_offsets:
            argv.append("--no_offsets")
        if cfg.nisar2geoc_no_deramp_quad:
            argv.append("--no_deramp_quad")
        add("nisar2geoc", argv,
            note="NISAR .h5 -> GEOC (iono+range-offset corrected, shared grid, baselines)")

    # ---------------- step 02 / 02to05 ----------------
    if cfg.run_reunw:
        # updated workflow: 02to05 instead of 02[,03,04,05]
        argv = ["-i", cfg.p02to05_op_GEOCdir or "GEOC", "-M", str(cfg.nlook)]
        _add(argv, "--freq", cfg.freq)
        if cfg.n_para:
            argv += ["--n_para", str(cfg.n_para)]
        _add(argv, "--thres", cfg.p02to05_thres)
        _add(argv, "--filter", cfg.p02to05_filter)
        _add(argv, "-g", cfg.p02to05_cliparea_geo or cfg.p05_clip_range_geo)
        if cfg.p02to05_cascade:
            argv.append("--cascade")
        if cfg.p02to05_hgtcorr:
            argv.append("--hgtcorr")
        if cfg.p02to05_gacos:
            argv.append("--gacos")
        add("02to05", argv, note="re-unwrapping (02to05) workflow")
    elif start <= 2 <= end:
        argv = ["-i", cfg.p02_GEOCdir or "GEOC"]
        _add(argv, "-o", cfg.p02_GEOCmldir)
        argv += ["-n", str(cfg.nlook)]
        _add(argv, "--freq", cfg.p02_freq or cfg.freq)
        if cfg.n_para:
            argv += ["--n_para", str(cfg.n_para)]
        if sbovl:
            argv.append("--sbovl")
        if cfg.p02_rngoff:
            argv.append("--rngoff")
        add("02", argv)

    # ---------------- optional 03-06 ----------------
    for step in cfg.order_op03_05:
        if not (start <= step <= end):
            continue
        if step == 3 and cfg.do03op_GACOS:
            inGEOCmldir = geocmldir
            outGEOCmldir = inGEOCmldir + "GACOS"
            argv = ["-i", inGEOCmldir, "-o", outGEOCmldir, "-g", cfg.p03_gacosdir]
            if cfg.p03_fillhole:
                argv.append("--fillhole")
            if cfg.n_para:
                argv += ["--n_para", str(cfg.n_para)]
            add("03", argv)
            geocmldir = outGEOCmldir
        if step == 4 and cfg.do04op_mask:
            inGEOCmldir = geocmldir
            outGEOCmldir = inGEOCmldir + "mask"
            argv = ["-i", inGEOCmldir, "-o", outGEOCmldir]
            _add(argv, "-c", cfg.p04_mask_coh_thre_avg)
            _add(argv, "-s", cfg.p04_mask_coh_thre_ifg)
            _add(argv, "-r", cfg.p04_mask_range)
            if cfg.n_para:
                argv += ["--n_para", str(cfg.n_para)]
            add("04", argv)
            geocmldir = outGEOCmldir
        if step == 5 and cfg.do05op_clip:
            inGEOCmldir = geocmldir
            outGEOCmldir = inGEOCmldir + "clip"
            argv = ["-i", inGEOCmldir, "-o", outGEOCmldir]
            _add(argv, "-r", cfg.p05_clip_range)
            _add(argv, "-g", cfg.p05_clip_range_geo)
            if cfg.n_para:
                argv += ["--n_para", str(cfg.n_para)]
            add("05", argv)
            geocmldir = outGEOCmldir
        if step == 6 and cfg.do06op_ERA5:
            inGEOCmldir = geocmldir
            outGEOCmldir = inGEOCmldir + "ERA5"
            argv = ["-i", inGEOCmldir, "-o", outGEOCmldir, "-g", cfg.p06_era5dir]
            if cfg.p06_fillhole:
                argv.append("--fillhole")
            if cfg.n_para:
                argv += ["--n_para", str(cfg.n_para)]
            add("06", argv)
            geocmldir = outGEOCmldir
        # show skipped optional steps in the flowchart (greyed out)
        if start <= step <= end:
            if step == 3 and not cfg.do03op_GACOS:
                steps.append(BatchStep(key="03off", name="LiCSBAS03op_GACOS.py",
                                       module="", argv=[], optional=True, phase=_PHASES["03"]))
            if step == 4 and not cfg.do04op_mask:
                steps.append(BatchStep(key="04off", name="LiCSBAS04op_mask_unw.py",
                                       module="", argv=[], optional=True, phase=_PHASES["04"]))
            if step == 5 and not cfg.do05op_clip:
                steps.append(BatchStep(key="05off", name="LiCSBAS05op_clip_unw.py",
                                       module="", argv=[], optional=True, phase=_PHASES["05"]))
            if step == 6 and not cfg.do06op_ERA5:
                steps.append(BatchStep(key="06off", name="LiCSBAS03op_ERA5.py",
                                       module="", argv=[], optional=True, phase=_PHASES["06"]))

    # ---------------- TSdir ----------------
    TSdir = f"TS_{geocmldir}"

    # ---------------- step 11 ----------------
    if start <= 11 <= end:
        argv = ["-d", cfg.p11_GEOCmldir or geocmldir]
        _add(argv, "-t", cfg.p11_TSdir or TSdir)
        _add(argv, "-u", cfg.p11_unw_thre)
        _add(argv, "-c", cfg.p11_coh_thre)
        _add(argv, "--minbtemp", cfg.p11_minbtemp)
        _add(argv, "--maxbtemp", cfg.p11_maxbtemp)
        if sbovl:
            argv.append("--sbovl")
        if cfg.p11_s_param:
            argv.append("-s")
        add("11", argv)

    # ---------------- steps 120 / 12 ----------------
    if start <= 12 <= end:
        p120_use = cfg.p120_use or cfg.cometdev or sbovl
        if p120_use:
            argv = ["-c", geocmldir, "-d", geocmldir, "-t", TSdir]
            if cfg.p120_ignoreconncomp:
                argv.append("--ignore_comp")
            if sbovl:
                argv.append("--sbovl")
            add("120", argv, note="recommended, especially with nullification")
        if not sbovl:
            argv = ["-d", cfg.p12_GEOCmldir or geocmldir]
            _add(argv, "-t", cfg.p12_TSdir or TSdir)
            _add(argv, "-l", cfg.p12_loop_thre)
            if cfg.p12_multi_prime:
                argv.append("--multi_prime")
            if cfg.p12_nullify:
                argv.append("--nullify")
            if cfg.p12_nullify_fix_ref:
                argv.append("--nullify_fix_ref")
            if cfg.p12_skippngs:
                argv.append("--nopngs")
            _add(argv, "--rm_ifg_list", cfg.p12_rm_ifg_list)
            if cfg.n_para:
                argv += ["--n_para", str(cfg.n_para)]
            add("12", argv)
            if cfg.p12_nullify and p120_use:
                # 2024/11/13: refreshed nullification may create all-NaN ref areas -> re-pick reference
                argv120 = ["-c", geocmldir, "-d", geocmldir, "-t", TSdir]
                if cfg.p120_ignoreconncomp:
                    argv120.append("--ignore_comp")
                steps.append(BatchStep(
                    key="120b", name="LiCSBAS120_choose_reference.py",
                    module=p["120"][0], argv=argv120, optional=False,
                    note="re-run after nullified loop closure", phase=_PHASES["120"]))

    # ---------------- step 13 (with optional eqoffsets) ----------------
    if start <= 13 <= end:
        if cfg.eqoffs:
            argv = ["-t", TSdir, "-o", cfg.eqoffs_txtfile, "--buffer", str(cfg.eqoffs_buffer)]
            if cfg.eqoffs_minmag and float(cfg.eqoffs_minmag) > 0:
                argv += ["-M", str(cfg.eqoffs_minmag)]
            add("eqoffs", argv, optional=True, note="earthquake offsets (auto-find)")
        argv = ["-d", cfg.p13_GEOCmldir or geocmldir]
        _add(argv, "-t", cfg.p13_TSdir or TSdir)
        _add(argv, "--inv_alg", cfg.p13_inv_alg)
        _add(argv, "--mem_size", cfg.p13_mem_size)
        _add(argv, "--gamma", cfg.p13_gamma)
        _add(argv, "--input_units", cfg.p13_inputunit)
        if cfg.n_para:
            argv += ["--n_para", str(cfg.n_para)]
        _add(argv, "--n_unw_r_thre", cfg.p13_n_unw_r_thre)
        if cfg.p13_keep_incfile:
            argv.append("--keep_incfile")
        if cfg.p13_ignore_nullification:
            argv.append("--ignore_nullification")
        if cfg.p13_nullify_noloops:
            argv.append("--nullify_noloops")
        if cfg.p13_singular:
            argv.append("--singular")
        if cfg.sbovl_abs:
            argv.append("--sbovl_abs")
        elif sbovl:
            argv.append("--sbovl")
        if cfg.p13_singular_gauss:
            argv.append("--singular_gauss")
        if cfg.p13_skippngs:
            argv.append("--nopngs")
        if cfg.gpu:
            argv.append("--gpu")
        if cfg.cometdev:
            argv.append("--nopngs")
            if not cfg.p13_n_unw_r_thre:
                argv += ["--n_unw_r_thre", "0.4"]
        if cfg.eqoffs:
            argv += ["--offsets", cfg.eqoffs_txtfile]
        note = "may be re-run automatically if ref-area NaNs appear (nullify)" \
               if (cfg.p12_nullify and not sbovl) else ""
        add("13", argv, note=note)

    # ---------------- post-13 corrections / sbovl absolute ----------------
    if start <= 13 <= end:
        if cfg.sbovl_abs:
            argv = ["-t", TSdir]
            if cfg.p131_sbovl_model:
                argv.append("--model")
            add("131abs", argv, note="ICCP+ESD offset, absolute SET/Iono correction (SBOI)")
        else:
            corr = [c for c, on in (("--tide", cfg.p131_tide),
                                           ("--iono", cfg.p131_iono),
                                           ("--gacos", cfg.p131_gacos)) if on]
            if corr:
                argv = ["-t", TSdir] + corr
                if sbovl:
                    argv.append("--sbovl")
                add("131corr", argv, optional=True, note="tide/iono/gacos corrections")

    # ---------------- step 14 ----------------
    if start <= 14 <= end:
        argv = ["-t", cfg.p14_TSdir or TSdir]
        _add(argv, "--mem_size", cfg.p14_mem_size)
        if cfg.sbovl_abs:
            argv.append("--sbovl_abs")
        elif sbovl:
            argv.append("--sbovl")
        if cfg.gpu:
            argv.append("--gpu")
        if cfg.eqoffs and not sbovl:
            argv.append("--skipexisting")
        add("14", argv)

    # ---------------- step 15 ----------------
    if start <= 15 <= end:
        argv = ["-t", cfg.p15_TSdir or TSdir]
        _add(argv, "-c", cfg.p15_coh_thre)
        _add(argv, "-u", cfg.p15_n_unw_r_thre)
        _add(argv, "-v", cfg.p15_vstd_thre)
        _add(argv, "-T", cfg.p15_maxTlen_thre)
        _add(argv, "-g", cfg.p15_n_gap_thre)
        _add(argv, "-s", cfg.p15_stc_thre)
        _add(argv, "-i", cfg.p15_n_ifg_noloop_thre)
        _add(argv, "-l", cfg.p15_n_loop_err_thre)
        _add(argv, "-L", cfg.p15_n_loop_err_ratio_thre)
        if not sbovl:
            _add(argv, "--avg_phase_bias", cfg.p15_avg_phasebias)
        _add(argv, "-r", cfg.p15_resid_rms_thre)
        _add(argv, "--vmin", cfg.p15_vmin)
        _add(argv, "--vmax", cfg.p15_vmax)
        if cfg.p15_keep_isolated:
            argv.append("--keep_isolated")
        if cfg.p15_noautoadjust:
            argv.append("--noautoadjust")
        if cfg.sbovl_abs:
            argv.append("--sbovl_abs")
        elif sbovl:
            argv.append("--sbovl")
        if cfg.p15_n_gap_use_merged:
            argv.append("--n_gap_use_merged")
        add("15", argv)

    # ---------------- step 16 ----------------
    if start <= 16 <= end:
        argv = ["-t", cfg.p16_TSdir or TSdir]
        _add(argv, "-s", cfg.p16_filtwidth_km)
        _add(argv, "-y", cfg.p16_filtwidth_yr)
        _add(argv, "-r", cfg.p16_deg_deramp)
        if cfg.p16_demerr:
            argv.append("--demerr")
        if cfg.p16_hgt_linear:
            argv.append("--hgt_linear")
        _add(argv, "--hgt_min", cfg.p16_hgt_min)
        _add(argv, "--hgt_max", cfg.p16_hgt_max)
        if cfg.p16_nomask:
            argv.append("--nomask")
        if cfg.n_para:
            argv += ["--n_para", str(cfg.n_para)]
        _add(argv, "--range", cfg.p16_range)
        _add(argv, "--range_geo", cfg.p16_range_geo)
        _add(argv, "--ex_range", cfg.p16_ex_range)
        _add(argv, "--ex_range_geo", cfg.p16_ex_range_geo)
        if cfg.p16_interpolate_nans:
            argv.append("--interpolate_nans")
        if sbovl:
            argv.append("--sbovl")
            if cfg.sbovl_abs:
                argv.append("--sbovl_abs")
        if cfg.p16_skippngs:
            argv.append("--nopngs")
        if cfg.eqoffs:
            argv += ["--from_model", f"{TSdir}/model.h5"]
        add("16", argv)

    return steps


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def _run_step(step: BatchStep) -> int:
    """Execute one step in-process via the ``licsbas.steps`` package."""
    if step.optional and not step.module:
        print(f"[batch] skipping optional step: {step.name}")
        return 0
    mod = importlib.import_module(step.module)
    fn = getattr(mod, "main")
    argv = [step.name] + list(step.argv)
    try:
        sig = inspect.signature(fn)
        takes_argv = "argv" in sig.parameters
    except (TypeError, ValueError):
        takes_argv = False
    if takes_argv:
        ret = fn(argv)
    else:  # e.g. LiCSBAS120 uses sys.argv via init_args()
        saved = sys.argv
        sys.argv = argv
        try:
            ret = fn()
        finally:
            sys.argv = saved
    if ret is None:
        return 0
    if isinstance(ret, int):
        return ret
    return 0


def run_batch(cfg: BatchConfig, dry_run: Optional[bool] = None) -> int:
    """Execute (or just print) the full chain described by ``cfg``.

    Returns 0 on success, non-zero exit code of the first failed step otherwise.
    """
    if dry_run is None:
        dry_run = cfg.check_only
    steps = build_pipeline(cfg)
    to_run = [s for s in steps if not (s.optional and not s.module)]

    print("\n" + "=" * 70)
    print("LiCSBAS batch processing (python) - {} step(s)".format(len(to_run)))
    print("=" * 70)
    if dry_run:
        for s in to_run:
            print(f"{s.name} {' '.join(s.argv)}")
        print("\n(check_only mode: nothing was executed)")
        return 0

    for i, s in enumerate(to_run, 1):
        print(f"\n[batch] ({i}/{len(to_run)}) running: {s.name} {' '.join(s.argv)}")
        try:
            rc = _run_step(s)
        except Exception as exc:  # step crashed
            print(f"[batch] step '{s.name}' raised: {exc}")
            return 1
        if rc not in (0, None):
            if s.key in ("120", "120b"):
                print("[batch] WARNING: LiCSBAS120_choose_reference failed; "
                      "continuing with the original reference selection.")
                continue
            print(f"[batch] step '{s.name}' failed with code {rc}; aborting.")
            return int(rc) if isinstance(rc, int) else 1
    print("\n[batch] finished successfully.")
    return 0


# ---------------------------------------------------------------------------
# Flowchart
# ---------------------------------------------------------------------------

def save_flowchart(cfg: BatchConfig, out_png: str,
                   title: str = "LiCSBAS processing chain (python batch)",
                   rankdir: str = "TB") -> str:
    """Write a PNG flowchart of the chain to ``out_png``.

    ``rankdir``: "TB" (default, vertical) or "LR" (landscape - better for
    embedding in notebooks/documents). Uses :mod:`licsbas.flowchart`, which
    requires the Graphviz ``dot`` binary.
    """
    from licsbas.flowchart import FlowStep, render_flowchart

    fs = []
    for s in build_pipeline(cfg):
        active = not s.optional
        cmd = " ".join(a for a in s.argv if a)
        if len(cmd) > 80:
            cmd = cmd[:77] + "..."
        fs.append(FlowStep(name=s.name, details=cmd, active=active,
                           phase=s.phase, note=s.note))
    return render_flowchart(fs, out_png, title=title, rankdir=rankdir)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(
        prog="licsbas-batch",
        description="Run the LiCSBAS processing chain in python (v3 batch). "
                    "A predefined workflow template (see --list-workflows) can be "
                    "selected with --workflow, e.g. 'reunw_5'; licsbas.batch.BatchConfig "
                    "/ examples/ hold the full set of options.")
    ap.add_argument("--list-workflows", action="store_true",
                    help="show the predefined workflow templates and exit")
    ap.add_argument("--workflow", default="standard",
                    help="workflow template to start from "
                         "(default: standard; choices via --list-workflows)")
    ap.add_argument("--start", type=int, default=None, help="first step, 1-16 (overrides workflow)")
    ap.add_argument("--end", type=int, default=None, help="last step, 1-16 (overrides workflow)")
    ap.add_argument("--nlook", type=int, default=None, help="multilook factor (overrides workflow)")
    ap.add_argument("--n-para", type=int, default=None, help="parallel workers (default: usable CPUs)")
    ap.add_argument("--gpu", action="store_true", help="use GPU where supported")
    ap.add_argument("--check-only", action="store_true", help="print commands only")
    ap.add_argument("--sbovl", action="store_true", help="SBOI/SBOVL chain (--sbovl options)")
    ap.add_argument("--sbovl-abs", action="store_true", help="SBOI absolute (close referencing, ICC+ESD, abs corr)")
    ap.add_argument("--nisar", action="store_true",
                    help="NISAR data access: 01-get-nisar-data + nisar2geoc instead of step 01")
    ap.add_argument("--nisar-bbox", dest="nisar_bbox", default="",
                    help="NISAR bbox lon1/lon2/lat1/lat2 (with --nisar)")
    ap.add_argument("--nisar-frames", dest="nisar_frames", default="",
                    help="NISAR frame id(s) FID[,FID2,...] for 01-get-nisar-data --frame "
                         "(e.g. 018A_01234); see its --list-frames")
    ap.add_argument("--reunw", action="store_true", help="use LiCSBAS02to05_unwrap.py (re-unwrapping workflow)")
    ap.add_argument("--gacos", action="store_true", help="enable optional GACOS step (03op)")
    ap.add_argument("--mask", action="store_true", help="enable optional unw masking step (04op)")
    ap.add_argument("--clip", action="store_true", help="enable optional clip step (05op)")
    ap.add_argument("--era5", action="store_true", help="enable optional ERA5 step (06op/03op_ERA5)")
    ap.add_argument("--no-multi-prime", dest="multi_prime", action="store_false",
                    help="turn OFF step 12: --multi_prime (on by default)")
    ap.add_argument("--nullify", action="store_true", help="step 12: --nullify")
    ap.add_argument("--tide", action="store_true", help="post-13 tide corrections")
    ap.add_argument("--iono", action="store_true", help="post-13 iono corrections")
    ap.add_argument("--gacos-corr", action="store_true", dest="gacos_corr",
                    help="post-13 gacos corrections")
    ap.add_argument("--flowchart", default="", help="also write a PNG flowchart to this path")
    a = ap.parse_args(argv)

    if a.list_workflows:
        print("Predefined workflow templates (pick with --workflow NAME):")
        for name in sorted(list_workflows()):
            print(f"  {name:<12} {list_workflows()[name]}")
        return 0

    config = make_config(a.workflow)
    overrides = {}
    if a.start is not None:
        overrides["start_step"] = a.start
    if a.end is not None:
        overrides["end_step"] = a.end
    if a.nlook is not None:
        overrides["nlook"] = a.nlook
    if a.n_para is not None:
        overrides["n_para"] = a.n_para
    if a.gpu:
        overrides["gpu"] = True
    if a.sbovl:
        overrides["sbovl"] = True
    if a.sbovl_abs:
        overrides["sbovl_abs"] = True
    if a.nisar:
        overrides["use_nisar"] = True
    # NISAR search params apply with BOTH --nisar and --workflow nisar
    if a.nisar_bbox:
        overrides["pNISAR_bbox"] = a.nisar_bbox
    if a.nisar_frames:
        overrides["pNISAR_frames"] = a.nisar_frames
    if a.reunw:
        overrides["run_reunw"] = True
    if a.gacos or a.gacos_corr:
        overrides["do03op_GACOS"] = True
    if a.mask:
        overrides["do04op_mask"] = True
    if a.clip:
        overrides["do05op_clip"] = True
    if a.era5:
        overrides["do06op_ERA5"] = True
    if not a.multi_prime:
        overrides["p12_multi_prime"] = False
    if a.nullify:
        overrides["p12_nullify"] = True
    if a.tide:
        overrides["p131_tide"] = True
    if a.iono:
        overrides["p131_iono"] = True
    if a.gacos_corr:
        overrides["p131_gacos"] = True
    cfg = make_config(a.workflow, **overrides)
    cfg.check_only = a.check_only

    if a.flowchart:
        save_flowchart(cfg, a.flowchart)
        print(f"[batch] flowchart written to: {a.flowchart}")
    return run_batch(cfg)


if __name__ == "__main__":
    sys.exit(main() or 0)
