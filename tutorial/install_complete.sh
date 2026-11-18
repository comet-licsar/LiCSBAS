#!/bin/bash
# This script installs the minimum necessary software and packages to
# run the COMET LiCSBAS v3 tutorial (local VM / desktop environment).
# Tested on: Debian 12, Ubuntu 22.04/24.04.

echo "Installing dependencies (this may take a while)..."
sudo apt update && sudo apt install -y git curl wget
curl -fsSL https://conda.org/miniconda/Miniconda3-latest-Linux-x86_64.sh -o miniconda.sh
bash miniconda.sh -b -p $HOME/miniconda
rm -f miniconda.sh

# Create and activate a fresh environment
$HOME/miniconda/bin/conda create -y -n licsbas python=3.11
source $HOME/miniconda/bin/activate licsbas

# Install LiCSBAS v3 (pip) with the interactive viewer extras
git clone https://github.com/comet-licsar/LiCSBAS.git -b v3.0.0 $HOME/LiCSBAS
source $HOME/LiCSBAS/bashrc_LiCSBAS.sh   # adds bin/ wrappers to PATH
cd $HOME/LiCSBAS
pip install ".[viewer]"

# Keep the legacy bash-compatible CLI wrappers in PATH for new shells
echo 'source $HOME/LiCSBAS/bashrc_LiCSBAS.sh' >> ~/.bashrc

# Download the tutorial notebook
wget -O ~/notebooks/tutorials/tutorial_bash-compatible.ipynb \
    https://raw.githubusercontent.com/comet-licsar/LiCSBAS/v3.0.0/tutorial_bash-compatible.ipynb

echo "Done. Activate the environment with: source $HOME/miniconda/bin/activate licsbas"
