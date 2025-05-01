#!/usr/bin/env python

from escpos.printer import Usb


""" Seiko Epson Corp. Receipt Printer (EPSON TM-T88IV) """
p = Usb(0x04b8, 0x0202, 0, profile="TM-T88IV")
p.text("Hello World\n")
p.image("logo.gif")
p.barcode('4006381333931', 'EAN13', 64, 2, '', '')
p.cut()
