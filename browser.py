#!/usr/bin/env python

from pathlib import Path
from playwright.sync_api import sync_playwright


import sys
from argparse import ArgumentParser
from PIL import Image

def resize_image(path: str, width: int = 384) -> Image.Image:
    """
    Resize the image at the given path to the specified width while maintaining the aspect ratio.
    """
    with Image.open(path) as img:
        orig_width, orig_height = img.size
        scale_factor = width / float(orig_width)
        new_height = int(orig_height * scale_factor)
        resized = img.resize((width, new_height))
        return resized


def full_page_screenshot(url: str,
                         path: str | Path = "screenshot.png",
                         device_name: str = "iPhone 12") -> str:
    """
    Render *url* in the chosen mobile device emulation and
    save a scrolling / full-page PNG to *path*.
    Returns the absolute path of the screenshot.
    """
    path = Path(path).expanduser().resolve()

    with sync_playwright() as p:
        print("Launching browser...")
        device = p.devices[device_name]          # iPhone, Pixel, Galaxy, …
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(**device)
        page = context.new_page()
        print(f"Taking screenshot of {url} on {device_name}...")
        page.goto(url, wait_until="networkidle")

        # Scroll through the page once to trigger lazy-loaded elements
        page.evaluate("""
            (async () => {
                const step = window.innerHeight;
                for (let y = 0; y < document.body.scrollHeight; y += step) {
                    window.scrollTo(0, y);
                    await new Promise(r => setTimeout(r, 100));
                }
                window.scrollTo(0, 0);          // back to top for clean shot
            })();
        """)
        print("Taking screenshot...")

        page.screenshot(path=str(path), full_page=True)
        browser.close()
        resized_img = resize_image(path, width=384)
        resized_img.save(path)
    return str(path)


if __name__ == "__main__":

    parser = ArgumentParser(description="Take a full-page screenshot of a URL.")
    parser.add_argument("url", help="URL to screenshot")
    parser.add_argument("-p", "--path", default="screenshot.png",
                        help="Path to save the screenshot")
    parser.add_argument("-d", "--device", default="iPhone 12",
                        help="Device name for emulation (default: iPhone 12)")
    args = parser.parse_args()

    path = full_page_screenshot(args.url, args.path, args.device)
    print(f"Screenshot saved to {path}")
