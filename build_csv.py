#!/usr/bin/env python

"""
Fetch all newsletter emails from the prnti mailbox and build a CSV with:
id, type, nr, date, url

Connects READONLY so nothing in the mailbox is modified.
"""

import csv
import re
import os
import requests
from datetime import datetime
from imap_tools import MailBox, AND
from dotenv import load_dotenv

load_dotenv()

HOST = os.environ["PRNTI_MAIL_HOST"]
USER = os.environ["PRNTI_MAIL_USER"]
PASS = os.environ["PRNTI_MAIL_PASS"]
SENDER = os.environ["WNTI_SENDER"]

# German month names for parsing dates like "12. November 2025"
GERMAN_MONTHS = {
    "Januar": 1, "Februar": 2, "März": 3, "April": 4,
    "Mai": 5, "Juni": 6, "Juli": 7, "August": 8,
    "September": 9, "Oktober": 10, "November": 11, "Dezember": 12,
}

URL_PATTERN = r'https://mailchi\.mp/wnti/[A-Za-z0-9\-_]+(?:[?&][^"\s<>()]+)*'

MONTH_NAMES = '|'.join([
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
])

# Match the full header line as one unit:
#   #137 | 12. November 2025 | ...
#   #99 | 19.09.2025 | ...
HEADER_PATTERN = re.compile(
    r'#(\d+)\s*\|\s*'                                    # nr
    r'(\d{1,2})\.\s*'                                    # day
    r'(?:(\d{1,2})\.(\d{4})|(' + MONTH_NAMES + r')\s+(\d{4}))'  # numeric or named month+year
)


def parse_header_line(text):
    """Extract nr and date from the header line like '#137 | 12. November 2025 | ...'"""
    match = HEADER_PATTERN.search(text)
    if not match:
        return None, None

    nr = int(match.group(1))
    day = int(match.group(2))

    if match.group(3):
        # Numeric: DD.MM.YYYY
        month = int(match.group(3))
        year = int(match.group(4))
    else:
        # Named: DD. MonthName YYYY
        month_name = match.group(5)
        month_map = {name: i for i, name in enumerate(MONTH_NAMES.split('|'), 1)}
        month = month_map[month_name]
        year = int(match.group(6))

    date = datetime(year, month, day).date()
    return nr, date


def extract_url(msg):
    """Extract the mailchimp newsletter URL from the message."""
    content = msg.text or msg.html or ''
    match = re.search(URL_PATTERN, content)
    return match.group(0) if match else None


def classify_type(msg):
    """Determine newsletter type from subject line."""
    subject = (msg.subject or '').lower()
    if 'parlamentsbrief' in subject:
        return 'parlamentsbrief'
    return 'wintibrief'


def url_slug(url):
    """Extract the URL slug (path without query params) for deduplication."""
    return url.split('?')[0]


def load_old_csv(path='newsletters.csv'):
    """Load entries from the old newsletters.csv."""
    if not os.path.exists(path):
        return []
    entries = []
    with open(path) as f:
        for row in csv.DictReader(f):
            if row['url']:
                entries.append({
                    'type': 'wintibrief',
                    'nr': '',
                    'date': '',
                    'url': row['url'],
                })
    return entries


def main():
    print(f"Connecting to {HOST} as {USER} (readonly)...")

    entries = []

    with MailBox(HOST).login(USER, PASS, initial_folder='INBOX') as mailbox:
        mailbox.folder.set('INBOX', readonly=True)

        print(f"Fetching all emails from {SENDER}...")
        messages = list(mailbox.fetch(AND(from_=SENDER)))
        print(f"Found {len(messages)} emails")

        for msg in messages:
            url = extract_url(msg)
            if not url:
                print(f"  SKIP (no URL): {msg.subject}")
                continue

            content = msg.text or msg.html or ''
            nr, date = parse_header_line(content)

            if nr is None:
                print(f"  SKIP (no #nr): {msg.subject}")
                continue

            # Fall back to email date if body date not found
            if date is None:
                date = msg.date.date() if msg.date else None

            newsletter_type = classify_type(msg)

            entries.append({
                'type': newsletter_type,
                'nr': nr,
                'date': date.isoformat() if date else '',
                'url': url_slug(url),
            })
            print(f"  #{nr} | {newsletter_type} | {date} | {url[:60]}...")

    # Merge in old newsletters.csv entries not already found
    seen_slugs = {url_slug(e['url']) for e in entries}
    old_entries = load_old_csv()
    merged = 0
    for old in old_entries:
        if url_slug(old['url']) not in seen_slugs:
            # Fetch the page to get nr and date
            try:
                print(f"  Fetching {old['url'][:60]}...")
                resp = requests.get(old['url'], timeout=15)
                resp.raise_for_status()
                nr, date = parse_header_line(resp.text)
                if nr is not None:
                    old['nr'] = nr
                if date is not None:
                    old['date'] = date.isoformat()
                if 'parlamentsbrief' in resp.text.lower():
                    old['type'] = 'parlamentsbrief'
                print(f"    -> #{nr} | {old['type']} | {date}")
            except Exception as e:
                print(f"    -> Failed to fetch: {e}")

            old['url'] = url_slug(old['url'])
            entries.append(old)
            seen_slugs.add(old['url'])
            merged += 1
    print(f"Merged {merged} entries from newsletters.csv")

    # Sort by date ascending (entries without date go first)
    entries.sort(key=lambda e: (e['date'], e['nr']))

    # Assign continuous IDs
    for i, entry in enumerate(entries, start=1):
        entry['id'] = i

    # Write CSV
    output = 'newsletters_full.csv'
    with open(output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'type', 'nr', 'date', 'url'])
        writer.writeheader()
        writer.writerows(entries)

    print(f"\nWrote {len(entries)} entries to {output}")


if __name__ == '__main__':
    main()
