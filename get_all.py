#!/usr/bin/env python

from icecream import ic
from csv import DictReader
from browser import full_page_screenshot
from tqdm import tqdm
import os


newsletters=DictReader(open("newsletters.csv"))

for newsletter in tqdm(newsletters):
    if newsletter["url"]!='':
        ic(newsletter)
        path=f"newsletters/{newsletter['id']}.jpg"
        # does path exist?
        if not os.path.isfile(path):
            full_page_screenshot(newsletter["url"],path)
