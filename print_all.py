#!/usr/bin/env python

from tsp800 import Printer
from glob import glob
from tqdm import tqdm


files = sorted(glob("newsletters/*.jpg"))
with Printer() as p:
    for file in (pbar := tqdm(files)):
        pbar.set_postfix_str(file)
        p.image(file, cut=False)
