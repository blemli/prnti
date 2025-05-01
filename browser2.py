#!/usr/bin/env python

#!/usr/bin/env python3
# pip install selenium pillow webdriver-manager

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import base64, io


URL = "https://example.com"               # anpassen
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")    # aktuelles Headless-Flag
options.add_argument("--disable-gpu")
options.add_experimental_option("mobileEmulation",
                                {"deviceName": "iPhone 12 Pro"})  # Mobile-Mode

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                          options=options)
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
