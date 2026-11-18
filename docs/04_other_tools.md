# 4. Other tools

Helper utilities outside the main pipeline. All are console entry points (`licbas-*`),
with the legacy `LiCSBAS_*.py` names available via `bin/`. Run any command with `--help`.

## Convert between h5 and other formats

| Tool | v3 entry point | Description |
| --- | --- | --- |
| `LiCSBAS_cum2flt.py` | — (bin wrapper) | Output a float32 cumulative displacement for one date from `cum*.h5` |
| `LiCSBAS_cum2tif.py` | — (bin wrapper) | Output a GeoTIFF of cumulative displacement |
| `LiCSBAS_cum2tstxt.py` | `licbas-cum2tstxt` | Output the time series at one point as text |
| `LiCSBAS_cum2vel.py` | `licbas-cum2vel` | Velocity + vstd from `cum*.h5`; `--sin` annual signal; `--eqoffsets` earthquake offsets |
| `LiCSBAS_cum2vel_weighted.py` | `licbas-cum2vel-weighted` | Weighted velocity estimate (COMET extra) |
| `LiCSBAS_flt2geotiff.py` | `licbas-flt2geotiff` | Convert a float32 file to GeoTIFF (for QGIS etc.) |
| `LiCSBAS_out2nc.py` | `licbas-out2nc` | Export results as NetCDF4 (see [visualization](03_visualization.md)) |
| `LiCSBAS_epochs2cum.py` | `licbas-epochs2cum` | Convert single-epoch (SBAS) displacements to cumulative |

## Float file helpers

| Tool | v3 entry point | Description |
| --- | --- | --- |
| `LiCSBAS_mask_flt.py` | — (bin wrapper) | Mask a float32 file with a mask file (`-i infile -m maskfile`) |
| `LiCSBAS_decomposeLOS.py` | — (bin wrapper) | Decompose LOS displacement into vertical/horizontal components |
| `LiCSBAS_get_value_geo.py` | `licbas-get-value-geo` | Get the value of a GeoTIFF at a geographic coordinate |
| `LiCSBAS_contour.py` | `licbas-contour` | Draw contours from a GeoTIFF → GeoJSON (GSI Maps style) |
| `LiCSBAS_color_geotiff.py` | `licbas-color-geotiff` | Create a colored GeoTIFF from a data GeoTIFF (colormaps as in [visualization](03_visualization.md)) |

## COMET extra steps (not in the original wiki)

| Tool | v3 entry point | Description |
| --- | --- | --- |
| `LiCSBAS130_remove_noloops.py` | — (bin wrapper) | Remove no-loop ifgs from the network |
| `LiCSBAS131_residual_threshold.py` | `licbas-residual-threshold` | Flag pixels/ifgs with high residuals |
| `LiCSBAS_cum_clip.py` | — (bin wrapper) | Clip cumulative displacement |
| `LiCSBAS_cum_interpolate.py` | — (bin wrapper) | Interpolate/repair cumulative displacement |
| `LiCSBAS_cum_plate_motion.py` | — (bin wrapper) | Estimate/remove plate motion from cum |
| `LiCSBAS_densify_ifgs.py` | `licbas-densify-ifgs` | Add ifgs to densify the network |
| `LiCSBAS_detect_coreg_error.py` | — (bin wrapper) | Detect coregistration errors |
| `LiCSBAS_get_eqoffsets.py` | `licsbas-get-eqoffsets` | Fetch earthquake offsets (needs `usgs-libcomcat`, manual install) |
| `LiCSBAS_remove_reference_effect_from_vstd.py` | — (bin wrapper) | Remove reference-area effect from vstd |
| `LiCSBAS_reset_nulls.py` | — (bin wrapper) | Reset null pixels in results |
| `LiCSBAS_resid_check.py` | — (bin wrapper) | Check inversion residuals |
| `LiCSBAS_vel_plate_motion.py` | — (bin wrapper) | Estimate plate motion from velocity |
| `LiCSBAS13_sb_inv.py` / `LiCSBAS130_sb_inv.py` | `licbas-sb-inv` | Small-baselines inversion (130 variant: iterative) |

**Back to [workflow](02_workflow.md) · [visualization](03_visualization.md) · [file structure](file_structure.md)**
