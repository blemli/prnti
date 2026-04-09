#!/usr/bin/env python

from escpos.printer import Usb


VENDOR_ID = 0x0519
PRODUCT_ID = 0x0001
PROFILE= "TSP800"

allowed_images = ['.jpg', '.jpeg', '.gif', '.png', '.bmp']


class Printer:
    """Persistent USB printer connection. Use as context manager for batch prints."""

    def __init__(self):
        self.p = None

    def open(self):
        self.p = Usb(VENDOR_ID, PRODUCT_ID, 0, profile=PROFILE)
        return self

    def close(self):
        if self.p:
            self.p.close()
            self.p = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *exc):
        self.close()

    def image(self, filename, cut=True):
        assert filename.endswith(tuple(allowed_images)), "File type not supported"
        self.p.image(filename)
        if cut:
            self.p.cut()

    def text(self, text, cut=True):
        self.p.text(text)
        if cut:
            self.p.cut()

    def cut(self):
        self.p.cut()

    def reset(self):
        self.p._raw(b'\x1b\x40')


def print_image(filename, cut=True):
    with Printer() as p:
        p.image(filename, cut=cut)


def reset_printer():
    """Send ESC @ (initialize) to clear the printer buffer."""
    with Printer() as p:
        p.reset()


def print_text(text, cut=True):
    with Printer() as p:
        p.text(text, cut=cut)


if __name__=="__main__":
    print_image("screenshot.png", cut=False)
