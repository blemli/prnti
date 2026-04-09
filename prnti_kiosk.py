#!/usr/bin/env python

"""
Kiosk mode for prnti: prints newsletters on button press.

Button on GPIO 27 (active-low, internal pull-up):
  - Short press  (0.1–0.8s): print the most recent newsletter
  - Middle press (1–2s):     enter morse input mode to select newsletter by nr
  - Long press   (>4s):      print all newsletters oldest-first (abort with short press)

Morse input mode (enter with middle press):
  For each digit: tap short presses to count the digit value, then middle press to confirm.
  After 3 digits confirmed, the newsletter with that nr is printed.
  Example for #103: middle(enter), short×1, middle(=1), middle(=0), short×3, middle(=3) → prints #103
"""

import csv
import os
import signal
import sys
import threading
import time

import RPi.GPIO as GPIO

from tsp800 import print_image, reset_printer, Printer

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


def print_newsletter(newsletter, cut=False):
    """Print a newsletter from its pre-downloaded image."""
    path = os.path.join(NEWSLETTERS_DIR, f"{newsletter['id']}.jpg")
    if not os.path.isfile(path):
        print(f"Image not found: {path}")
        return
    print(f"Printing: #{newsletter['nr']} ({newsletter['date']}) — {path}")
    print_image(path, cut=cut)


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


def handle_middle_press():
    """Enter morse input mode to select a newsletter by id."""
    print("Morse input mode — tap short for digit value, middle to confirm digit")
    digits = []

    while len(digits) < 3:
        count = 0
        # Count short taps, middle press confirms the digit
        while True:
            duration = wait_for_press()
            if SHORT_MIN <= duration <= SHORT_MAX:
                count += 1
                print(f"  tap {count}")
            elif MIDDLE_MIN <= duration <= MIDDLE_MAX:
                if count > 9:
                    print(f"  digit too large ({count}), capping to 9")
                    count = 9
                digits.append(count)
                print(f"  confirmed digit: {count}  (so far: {''.join(str(d) for d in digits)})")
                break
            elif duration >= LONG_MIN:
                print("  long press — aborting morse input")
                return
            else:
                print(f"  ignored press ({duration:.2f}s)")

    entered_id = str(digits[0] * 100 + digits[1] * 10 + digits[2]).zfill(3)
    print(f"Morse input complete: id {entered_id}")

    newsletters = load_newsletters()
    match = next((nl for nl in newsletters if nl['id'] == entered_id), None)
    if match:
        print(f"Found newsletter id={entered_id}: #{match['nr']} ({match['date']})")
        print_newsletter(match, cut=True)
    else:
        print(f"Newsletter id={entered_id} not found")


def handle_short_press():
    """Print the most recent newsletter (last row in CSV)."""
    newsletters = load_newsletters()
    if not newsletters:
        print("No newsletters found")
        return
    latest = newsletters[-1]
    print(f"Printing latest newsletter: #{latest['nr']} ({latest['date']})")
    print_newsletter(latest, cut=True)


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
        with Printer() as p:
            for i, nl in enumerate(newsletters, 1):
                if abort.aborted:
                    print(f"Aborted at {i}/{total} — resetting printer")
                    p.reset()
                    return
                path = os.path.join(NEWSLETTERS_DIR, f"{nl['id']}.jpg")
                if not os.path.isfile(path):
                    print(f"Image not found: {path}")
                    continue
                print(f"[{i}/{total}] #{nl['nr']} ({nl['date']}) — {path}")
                p.image(path, cut=False)
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
                handle_middle_press()
            elif duration >= LONG_MIN:
                handle_long_press()
            else:
                print(f"Ignored press ({duration:.2f}s — between thresholds)")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
