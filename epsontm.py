#!/usr/bin/env python

from escpos.printer import Usb


VENDOR_ID = "0x04b8"
PRODUCT_ID = "0x0202"
PROFILE= "TM-T88IV"

allowed_images = ['.jpg', '.gif', '.png', '.bmp']

def print_image(filename):
    p = Usb(VENDOR_ID, PRODUCT_ID, 0, profile=PROFILE)
    p.text("Hello World\n")
    assert filename.endswith(tuple(allowed_images)), "File type not supported"
    p.image(filename)
    p.cut()
    p.close()
