#!/usr/bin/env python3
"""Winterthur Fame Index — Who and what gets mentioned most in WNTI newsletters."""

import csv
import re
import shutil
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import spacy
from bs4 import BeautifulSoup

CSV_FILE = "newsletters.csv"
JOURNALISTS_FILE = "journalists.txt"
MAX_WORKERS = 10
TIMEOUT = 30

# Generic terms to filter out (not real named entities)
STOPNAMES = {
    "winterthur", "zürich", "wnti", "wintibrief", "parlamentsbrief",
    "morsebrief", "newsletter", "mailchimp", "foto", "bild", "quelle",
    "impressum", "redaktion", "copyright", "archiv", "datum", "abonnieren",
    "weiterlesen", "kommentar", "kommentare", "antworten", "teilen",
    "facebook", "twitter", "instagram", "whatsapp", "email", "e-mail",
    "montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag",
    "januar", "februar", "märz", "april", "mai", "juni", "juli", "august",
    "september", "oktober", "november", "dezember",
    # Generic nouns / non-entities spaCy picks up
    "bleib", "tickets", "hause", "velos", "halle", "tempo", "zentrum",
    "partei", "kommission", "ok", "ki", "franken", "linkedin",
    "dorfet", "dörfet", "sohn", "gestern", "unterstütze", "bewohner",
    "person", "komm", "guten",
    # Winterthur aliases and newsletter greetings
    "winti", "morge winti", "guete morge winti",
}

# Misspellings and duplicate forms, merged into one canonical name
ALIASES = {
    "sadtbus": "Stadtbus",
    "kommision": "Kommission",
    "stadt": "Stadt Winterthur",
    "der schweiz": "Schweiz",
    "fcw": "FC Winterthur",
    "grünen": "Grüne",
    "mattia mayer": "Mattea Meyer",
    "mfw": "Musikfestwochen",
    "oskar reinhart": "Stiftung Oskar Reinhart",
}

# Real entities spaCy tends to put in the wrong bucket: name → correct label
RELABEL = {
    "rieter": "ORG",           # Rieter AG
    "terresta": "ORG",         # Terresta Immobilien
    "stadtbus": "ORG",         # Stadtbus Winterthur
    "bund": "ORG",             # der Bund = federal government, not a place
    "fc winterthur": "ORG",
    "grüne": "ORG",
    "stadtgrün": "ORG",        # Stadtgrün Winterthur
    "pfadi winterthur": "ORG",
    "stiftung oskar reinhart": "ORG",
    "geschichtennetzwerk winterthur": "ORG",
    "musikfestwochen": "ORG",
    "hegi": "LOC",             # Stadtteil, not a person
    "kva": "LOC",              # Kehrichtverbrennungsanlage
    "stadt winterthur": "LOC",
    "schweiz": "LOC",
}

# Names that are wrong under a specific label but may be valid under another
BLOCKED = {
    "ORG": {"gioia"},  # first name, not an organization
}


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
        return row["id"], row["date"], text, None
    except Exception as e:
        return row["id"], row["date"], "", str(e)


def clean_name(name):
    """Normalize an entity name."""
    name = re.sub(r"\s+", " ", name).strip()
    # Strip surrounding punctuation, emoji and other symbols
    name = re.sub(r"^[\W_]+|[\W_]+$", "", name)
    # Drop trailing "Guten" glued on from "Guten Morgen ..." greetings
    name = re.sub(r"\s+Guten$", "", name)
    return name


def load_journalists():
    """Names of the newsletter's own journalists, excluded from all counts."""
    try:
        with open(JOURNALISTS_FILE, encoding="utf-8") as f:
            return {
                line.strip().lower()
                for line in f
                if line.strip() and not line.startswith("#")
            }
    except FileNotFoundError:
        return set()


def print_top(title, counter, top_n=30):
    print(f"\n{title}")
    print("-" * 40)
    ranking = counter.most_common(top_n)
    if not ranking:
        return
    # Scale bars so the longest one fits the terminal width
    prefix_width = 44  # "  NN. name<30> NNNNx  "
    bar_max = max(10, shutil.get_terminal_size().columns - prefix_width)
    top_count = ranking[0][1]
    for rank, (name, count) in enumerate(ranking, 1):
        bar = "█" * max(1, round(count / top_count * bar_max))
        print(f"  {rank:2}. {name:<30} {count:4}x  {bar}")


def main():
    nlp = spacy.load("de_core_news_sm")
    journalists = load_journalists()
    if journalists:
        print(f"Excluding {len(journalists)} journalists from {JOURNALISTS_FILE}")

    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Fetching {len(rows)} newsletters...\n")

    texts = {}
    errors = []
    done = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_text, row): row for row in rows}
        for future in as_completed(futures):
            nid, date, text, err = future.result()
            done += 1
            if err:
                errors.append((nid, err))
                print(f"  [{done}/{len(rows)}] {nid} ERROR: {err}")
            else:
                texts[nid] = (date, text)
                print(f"  [{done}/{len(rows)}] {nid} ({date}) fetched ({len(text):,} chars)")

    print(f"\nFetched {len(texts)} newsletters. Running NER...\n")

    persons = Counter()
    locations = Counter()
    orgs = Counter()

    for i, (nid, (date, text)) in enumerate(sorted(texts.items()), 1):
        doc = nlp(text)
        for ent in doc.ents:
            name = clean_name(ent.text)
            if len(name) < 2:
                continue
            key = name.lower()
            if key in ALIASES:
                name = ALIASES[key]
                key = name.lower()
            # Skip journalists, stopnames and boilerplate ("WNTI Werben", "Maria WNTI", ...)
            if key in journalists or key in STOPNAMES or "wnti" in key.split():
                continue
            label = RELABEL.get(key, ent.label_)
            if key in BLOCKED.get(label, ()):
                continue
            if label == "PER":
                persons[name] += 1
            elif label == "LOC":
                locations[name] += 1
            elif label == "ORG":
                orgs[name] += 1
        if i % 25 == 0:
            print(f"  NER processed {i}/{len(texts)}...")

    print("\n" + "=" * 60)
    print("  WINTERTHUR FAME INDEX")
    print("=" * 60)

    print_top("🏆 TOP 30 PEOPLE", persons)
    print_top("📍 TOP 30 PLACES", locations)
    print_top("🏢 TOP 30 ORGANIZATIONS", orgs)

    total_entities = sum(persons.values()) + sum(locations.values()) + sum(orgs.values())
    print(f"\n{'=' * 60}")
    print(f"Total named entities found: {total_entities:,}")
    print(f"  Unique people:       {len(persons):,}")
    print(f"  Unique places:       {len(locations):,}")
    print(f"  Unique organizations: {len(orgs):,}")
    if errors:
        print(f"  Fetch errors:        {len(errors)}")


if __name__ == "__main__":
    main()
