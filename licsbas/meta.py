# version control
from licsbas import __version__ as ver  # single version source (licsbas/__init__.py)
date='2024-11-26'
author="The COMET dev team (ML,QO,JM,LS,MN,..) on top of original codes by Dr. Yu Morishita, supervised primarily by Prof. Andy Hooper"

# setting number of threads to small number (e.g. 1), as the multiprocessing appears slow otherwise
# solution found by Richard Rigby, Uni of Leeds
import os
os.environ["OMP_NUM_THREADS"] = '1'