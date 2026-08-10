#!/usr/bin/env python3
"""Fetch WNTI newsletters, feed them to Claude, and generate a fictional Wintibrief."""

import csv
import random
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic
import dotenv
import requests

dotenv.load_dotenv()
from bs4 import BeautifulSoup

CSV_FILE = "newsletters.csv"
MAX_WORKERS = 10
TIMEOUT = 30
# Stay well within 1M context: ~80 newsletters ≈ 300k tokens, leaves room for output
MAX_NEWSLETTERS = 80
MODEL = "claude-sonnet-4-6-20250514"


def fetch_text(row):
    """Fetch a URL and return cleaned text."""
    url = row["url"]
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "head", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return row, text, None
    except Exception as e:
        return row, "", str(e)


def main():
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Sample if we have too many
    if len(rows) > MAX_NEWSLETTERS:
        sample = random.sample(rows, MAX_NEWSLETTERS)
        print(f"Sampled {MAX_NEWSLETTERS} of {len(rows)} newsletters")
    else:
        sample = rows
        print(f"Using all {len(rows)} newsletters")

    # Sort by date for coherent reading
    sample.sort(key=lambda r: r["date"])

    print(f"Fetching {len(sample)} newsletters...\n")

    texts = []
    errors = 0
    done = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_text, row): row for row in sample}
        for future in as_completed(futures):
            row, text, err = future.result()
            done += 1
            if err:
                errors += 1
                print(f"  [{done}/{len(sample)}] {row['id']} ERROR: {err}")
            else:
                texts.append((row, text))
                print(f"  [{done}/{len(sample)}] {row['id']} ({row['date']}) — {len(text.split()):,} words")

    texts.sort(key=lambda t: t[0]["date"])

    total_words = sum(len(t.split()) for _, t in texts)
    print(f"\nFetched {len(texts)} newsletters ({total_words:,} words, ~{total_words * 4 // 3:,} tokens)")
    if errors:
        print(f"Errors: {errors}")

    # Build the prompt
    newsletter_block = ""
    for row, text in texts:
        newsletter_block += f"\n\n--- {row['type'].upper()} #{row['nr']} ({row['date']}) ---\n{text}"

    prompt = f"""Hier sind {len(texts)} echte Ausgaben des WNTI-Newsletters aus Winterthur.
Studiere den Stil, den Ton, die Struktur, die wiederkehrenden Themen und die typische Länge genau.

{newsletter_block}

---

Schreibe nun einen fiktiven Wintibrief für den {__import__('datetime').date.today().strftime('%d.%m.%Y')}.
Erfinde eine plausible, aber komplett fiktive Winterthurer Lokalgeschichte.
Sie soll sich lesen, als wäre sie echt — gleicher Stil, gleicher Ton, gleiche Struktur.
Verwende fiktive (aber realistisch klingende) Zitate von Winterthurer:innen.
Die Geschichte soll unterhaltsam und überraschend sein, aber glaubwürdig bleiben."""

    print(f"\nSending {len(prompt):,} chars to Claude ({MODEL})...\n")

    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)
    client = anthropic.Anthropic(api_key=api_key)

    # Stream the response
    print("=" * 60)
    print("  FIKTIVER WINTIBRIEF")
    print("=" * 60)
    print()

    full_response = ""
    with client.messages.stream(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_response += text

    print("\n\n" + "=" * 60)
    print(f"Generated {len(full_response.split()):,} words")

    # Save to file
    outfile = "fictional_wintibrief.md"
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(full_response)
    print(f"Saved to {outfile}")


if __name__ == "__main__":
    main()
