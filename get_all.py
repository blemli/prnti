#!/usr/bin/env python

"""Fetch the screenshot of every newsletter in newsletters.csv that has a url but no newsletters/<id>.jpg yet.
Failures are logged and skipped; at the end they are listed on stderr and the exit code is 1."""

import os
import sys
from csv import DictReader

from browser import full_page_screenshot
from icecream import ic
from tqdm import tqdm

with open("newsletters.csv", newline="") as f:
    newsletters = list(DictReader(f))

failed = []
for newsletter in tqdm(newsletters):
    if newsletter["url"] == "":
        continue
    path = f"newsletters/{newsletter['id']}.jpg"
    if os.path.isfile(path):
        continue
    ic(newsletter)
    try:
        full_page_screenshot(newsletter["url"], path)
    except Exception as e:
        print(f"#{newsletter['id']} failed: {e}", file=sys.stderr)
        failed.append(newsletter["id"])

if failed:
    print(f"failed: {' '.join(failed)}", file=sys.stderr)
    sys.exit(1)
