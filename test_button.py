#!/usr/bin/env python

"""Read GPIO 27 button state and print to console. Ctrl+C to exit."""

import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP)

try:
    print("Reading GPIO 27 (expect 1=released, 0=pressed). Ctrl+C to stop.")
    while True:
        print(GPIO.input(27), end=" ", flush=True)
        time.sleep(0.2)
except KeyboardInterrupt:
    print("\nDone")
finally:
    GPIO.cleanup()
