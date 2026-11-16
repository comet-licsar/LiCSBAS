#!/bin/bash
# LiCSBAS v3: the licsbas python package should be installed via pip
# (pip install licsbas or: pip install . from a source checkout).
# This only adds the legacy bash-compatible CLI wrappers (bin/) to PATH.
if [ -n "$BASH_SOURCE" ]; then
    LICSBAS_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
    LICSBAS_PATH="$(cd "$(dirname "$0")" && pwd)"
fi
export PATH="$LICSBAS_PATH/bin:$PATH"
