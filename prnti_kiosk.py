#!/usr/bin/env python

"""
Kiosk mode for prnti: prints newsletters on button press.

Button on GPIO 27 (active-low, internal pull-up):
  - Short press  (0.1–0.3s): print the most recent newsletter
  - Middle press (1–2s):     reserved for future use
  - Long press   (>4s):      print all newsletters oldest-first (abort with short press)
"""

import csv
import os
import signal
import sys
import time

import RPi.GPIO as GPIO

from browser import full_page_screenshot
from tsp800 import print_image

BUTTON_PIN = 27
CSV_PATH = "newsletters.csv"

# Press duration thresholds (seconds)
SHORT_MIN = 0.1
SHORT_MAX = 0.5
MIDDLE_MIN = 1.0
MIDDLE_MAX = 2.0
LONG_MIN = 4.0


def load_newsletters():
    with open(CSV_PATH) as f:
        return list(csv.DictReader(f))


def print_newsletter(url):
    """Take a screenshot of the URL and print it."""
    print(f"Printing: {url}")
    screenshot = full_page_screenshot(url)
    if screenshot:
        print_image(screenshot, cut=False)
        print_image("whitespace.jpg", cut=False)
        os.remove(screenshot)
    else:
        print("Failed to take screenshot")


def wait_for_press():
    """Wait for button press and return the duration in seconds."""
    # Wait for button press (falling edge, active-low)
    GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)
    press_start = time.monotonic()

    # Wait for release
    while GPIO.input(BUTTON_PIN) == GPIO.LOW:
        time.sleep(0.01)

    return time.monotonic() - press_start


def check_short_press():
    """Non-blocking check for a short button press (used to abort print-all)."""
    if GPIO.input(BUTTON_PIN) == GPIO.LOW:
        press_start = time.monotonic()
        while GPIO.input(BUTTON_PIN) == GPIO.LOW:
            time.sleep(0.01)
        duration = time.monotonic() - press_start
        if SHORT_MIN <= duration <= SHORT_MAX:
            return True
    return False


def handle_short_press():
    """Print the most recent newsletter (last row in CSV)."""
    newsletters = load_newsletters()
    if not newsletters:
        print("No newsletters found")
        return
    latest = newsletters[-1]
    print(f"Printing latest newsletter: #{latest['nr']} ({latest['date']})")
    print_newsletter(latest['url'])


def handle_long_press():
    """Print all newsletters oldest-first. Abort with a short press."""
    newsletters = load_newsletters()
    if not newsletters:
        print("No newsletters found")
        return

    total = len(newsletters)
    print(f"Printing all {total} newsletters...")

    for i, nl in enumerate(newsletters, 1):
        if check_short_press():
            print(f"Aborted at {i}/{total}")
            return
        print(f"[{i}/{total}] #{nl['nr']} ({nl['date']})")
        print_newsletter(nl['url'])

    print("All newsletters printed")


def signal_handler(sig, frame):
    print("\nShutting down...")
    GPIO.cleanup()
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    print("prnti kiosk ready. Waiting for button press...")

    try:
        while True:
            duration = wait_for_press()
            print(f"Button pressed for {duration:.2f}s")

            if SHORT_MIN <= duration <= SHORT_MAX:
                handle_short_press()
            elif MIDDLE_MIN <= duration <= MIDDLE_MAX:
                print("Middle press detected (not yet implemented)")
            elif duration >= LONG_MIN:
                handle_long_press()
            else:
                print(f"Ignored press ({duration:.2f}s — between thresholds)")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
