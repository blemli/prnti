#!/usr/bin/env python3
# pip install selenium pillow webdriver-manager

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType      # korrigierter Import
from PIL import Image
import base64, io

options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_experimental_option("mobileEmulation",
                                {"deviceName": "iPhone 12 Pro"})
options.binary_location = "/usr/bin/chromium-browser"

service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
driver = webdriver.Chrome(service=service, options=options)
try:
    driver.get(URL)

    # Vollseiten-PNG via DevTools
    result = driver.execute_cdp_cmd("Page.captureScreenshot",
                                    {"captureBeyondViewport": True,
                                     "fromSurface": True})
    raw_png = base64.b64decode(result["data"])

    # Breite fix auf 384 px, Höhe proportional
    img = Image.open(io.BytesIO(raw_png))
    factor = 384 / img.width
    img = img.resize((384, int(img.height * factor)), Image.LANCZOS)
    img.save("page.png")
finally:
    driver.quit()
