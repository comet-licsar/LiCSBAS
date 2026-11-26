#!/bin/bash -eu

# LiCSBAS batch processing
# =========================
# As of v3 (branch towards-v3), the batch pipeline is implemented in Python:
#
#     licsbas/batch.py          (module with BatchConfig + full step chain)
#     examples/example_1_standard.py         standard chain (historical defaults)
#     examples/example_2_reunw_02to05.py     chain using LiCSBAS02to05_unwrap.py
#     examples/example_3_sbovl.py            SBOI chain using the --sbovl options
#
# This wrapper keeps the old invocation working. Settings that used to be
# edited here (start/end step, nlook, sbovl, ...) now live in the Python
# BatchConfig in the example scripts, or can be passed as CLI options:
#
#     ./batch_LiCSBAS.sh --help
#     ./batch_LiCSBAS.sh --check-only                 # print commands only
#     ./batch_LiCSBAS.sh --start 11 --end 16          # start from step 11
#     ./batch_LiCSBAS.sh --sbovl                      # SBOI chain
#     ./batch_LiCSBAS.sh --reunw                      # 02to05 re-unwrapping
#     ./batch_LiCSBAS.sh --flowchart flow.png         # also write a PNG flowchart
#
# For fully custom chains (all p0X_... options of the old script), use
# `licsbas.batch.BatchConfig` directly in python:
#
#     from licsbas.batch import BatchConfig, run_batch
#     cfg = BatchConfig(start_step=1, end_step=16)   # all old options available
#     run_batch(cfg)

exec python3 -m licsbas.batch "$@"
