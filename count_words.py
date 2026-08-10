#!/usr/bin/env python3
"""Count words on all newsletter pages listed in newsletters.csv."""

import csv
import sys
import time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

CSV_FILE = "newsletters.csv"
MAX_WORKERS = 10
TIMEOUT = 30


def fetch_word_count(row):
    """Fetch a URL and return its word count."""
    url = row["url"]
    newsletter_id = row["id"]
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove script and style elements
        for tag in soup(["script", "style", "head"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        words = len(text.split())
        return newsletter_id, row["type"], row["nr"], row["date"], url, words, None
    except Exception as e:
        return newsletter_id, row["type"], row["nr"], row["date"], url, 0, str(e)


def main():
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Fetching {len(rows)} newsletters...\n")

    results = []
    errors = []
    total_words = 0
    done = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_word_count, row): row for row in rows}
        for future in as_completed(futures):
            nid, ntype, nr, date, url, words, err = future.result()
            done += 1
            if err:
                errors.append((nid, url, err))
                print(f"  [{done}/{len(rows)}] {nid} ERROR: {err}")
            else:
                total_words += words
                results.append((nid, ntype, nr, date, words))
                print(f"  [{done}/{len(rows)}] {nid} ({date}) — {words:,} words")

    # Sort results by id
    results.sort(key=lambda r: r[0])

    print("\n" + "=" * 60)
    print(f"Total newsletters fetched: {len(results)}")
    print(f"Errors: {len(errors)}")
    print(f"Total word count: {total_words:,}")
    if results:
        avg = total_words / len(results)
        print(f"Average words per newsletter: {avg:,.0f}")

    # Breakdown by type
    by_type = {}
    for nid, ntype, nr, date, words in results:
        by_type.setdefault(ntype, []).append(words)

    print("\nBreakdown by type:")
    for ntype, counts in sorted(by_type.items()):
        print(f"  {ntype}: {len(counts)} issues, {sum(counts):,} words (avg {sum(counts)//len(counts):,})")

    if errors:
        print(f"\nFailed URLs ({len(errors)}):")
        for nid, url, err in errors:
            print(f"  {nid}: {url} — {err}")


if __name__ == "__main__":
    main()
