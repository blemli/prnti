#!/usr/bin/env python

import base64, sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def full_page_screenshot(url: str,
                         output_path: str = "screenshot.png",
                         device_name: str = "iPhone X") -> None:
    mobile_emulation = {"deviceName": device_name}

    opts = Options()
    opts.add_experimental_option("mobileEmulation", mobile_emulation)
    opts.add_argument("--headless=new")      # Chrome ≥109
    opts.add_argument("--hide-scrollbars")   # keine Scroll-Leisten im Bild

    driver = webdriver.Chrome(options=opts)
    try:
        driver.get(url)
        driver.implicitly_wait(10)           # DOM / JS fertig

        # Vollständigen Screenshot via DevTools-Befehl holen
        png_b64 = driver.execute_cdp_cmd(
            "Page.captureScreenshot",
            {"fromSurface": True, "captureBeyondViewport": True}
        )["data"]

        with open(output_path, "wb") as fh:
            fh.write(base64.b64decode(png_b64))
    finally:
        driver.quit()

if __name__ == "__main__":
    full_page_screenshot(sys.argv[1], "example.png", "iPhone X")
    print("Screenshot saved as example.png")
