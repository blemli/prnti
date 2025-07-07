#!/usr/bin/env python

from escpos.printer import Usb


VENDOR_ID = 0x0519
PRODUCT_ID = 0x0001
PROFILE= "TSP800"

allowed_images = ['.jpg', '.jpeg', '.gif', '.png', '.bmp']

def print_image(filename,cut=True):
    p = Usb(VENDOR_ID, PRODUCT_ID, 0, profile=PROFILE)
    assert filename.endswith(tuple(allowed_images)), "File type not supported"
    p.image(filename)
    if cut: p.cut()
    p.close()

def print_text(text,cut=True):
    p = Usb(VENDOR_ID, PRODUCT_ID, 0, profile=PROFILE)
    p.text(text)
    if cut: p.cut()
    p.close()


if __name__=="__main__":
    print_image("whitespace.jpg",cut=False)
