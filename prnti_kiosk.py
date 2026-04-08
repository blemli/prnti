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
import threading
import time

import RPi.GPIO as GPIO

from tsp800 import print_image

BUTTON_PIN = 27
CSV_PATH = "newsletters.csv"
NEWSLETTERS_DIR = "newsletters"

# Press duration thresholds (seconds)
SHORT_MIN = 0.1
SHORT_MAX = 0.8
MIDDLE_MIN = 1.0
MIDDLE_MAX = 2.0
LONG_MIN = 4.0


def load_newsletters():
    with open(CSV_PATH) as f:
        return list(csv.DictReader(f))


def print_newsletter(newsletter):
    """Print a newsletter from its pre-downloaded image."""
    path = os.path.join(NEWSLETTERS_DIR, f"{newsletter['id']}.jpg")
    if not os.path.isfile(path):
        print(f"Image not found: {path}")
        return
    print(f"Printing: #{newsletter['nr']} ({newsletter['date']}) — {path}")
    print_image(path, cut=False)
    print_image("whitespace.jpg", cut=False)


def wait_for_press():
    """Wait for button press and return the duration in seconds."""
    # Wait for button press (falling edge, active-low)
    # Poll for button press (wait_for_edge broken on this kernel)
    while GPIO.input(BUTTON_PIN) == GPIO.HIGH:
        time.sleep(0.01)
    press_start = time.monotonic()

    # Wait for release
    while GPIO.input(BUTTON_PIN) == GPIO.LOW:
        time.sleep(0.01)

    return time.monotonic() - press_start


class AbortMonitor:
    """Monitors button in a background thread to detect abort presses during printing."""

    def __init__(self):
        self._abort = threading.Event()
        self._thread = None

    def start(self):
        self._abort.clear()
        self._thread = threading.Thread(target=self._watch, daemon=True)
        self._thread.start()

    def stop(self):
        self._abort.set()
        if self._thread:
            self._thread.join(timeout=2)

    @property
    def aborted(self):
        return self._abort.is_set()

    def _watch(self):
        while not self._abort.is_set():
            if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                press_start = time.monotonic()
                while GPIO.input(BUTTON_PIN) == GPIO.LOW:
                    time.sleep(0.01)
                duration = time.monotonic() - press_start
                if SHORT_MIN <= duration <= SHORT_MAX:
                    print("Abort press detected!")
                    self._abort.set()
                    return
            time.sleep(0.01)


def handle_short_press():
    """Print the most recent newsletter (last row in CSV)."""
    newsletters = load_newsletters()
    if not newsletters:
        print("No newsletters found")
        return
    latest = newsletters[-1]
    print(f"Printing latest newsletter: #{latest['nr']} ({latest['date']})")
    print_newsletter(latest)


def handle_long_press():
    """Print all newsletters oldest-first. Abort with a short press."""
    newsletters = load_newsletters()
    if not newsletters:
        print("No newsletters found")
        return

    total = len(newsletters)
    print(f"Printing all {total} newsletters... (short press to abort)")

    abort = AbortMonitor()
    abort.start()

    try:
        for i, nl in enumerate(newsletters, 1):
            if abort.aborted:
                print(f"Aborted at {i}/{total}")
                return
            print(f"[{i}/{total}] #{nl['nr']} ({nl['date']})")
            print_newsletter(nl)
    finally:
        abort.stop()

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
