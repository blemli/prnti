#!/usr/bin/env python

from tsp800 import print_image
from glob import glob
from icecream import ic
from time import sleep
from tqdm import tqdm


files=sorted(glob("newsletters/*.jpg"))
for file in (pbar:= tqdm(files)):
    pbar.set_postfix_str(file)
    print_image(file,cut=False)
