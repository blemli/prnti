#!/usr/bin/env python

import os
import time
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from epsontm import print_image

def visit_and_print(url, output_file="screenshot.png", print_output=True, mobile_mode=True, width=384, height=800, wait_time=5):
    """
    Visit a URL in a browser (optionally in mobile mode), take a screenshot, and print it.
    
    Args:
        url: The URL to visit
        output_file: The filename to save the screenshot to
        print_output: Whether to print the screenshot
        mobile_mode: Whether to use mobile emulation mode
        width: The width of the browser window/screenshot
        height: The height of the browser window/screenshot
        wait_time: How long to wait for the page to load before taking a screenshot
    
    Returns:
        The path to the screenshot file
    """
    print(f"Visiting URL: {url}")
    
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    if mobile_mode:
        print("Using mobile emulation mode")
        # Set up mobile emulation
        mobile_emulation = {
            "deviceMetrics": {"width": width, "height": height, "pixelRatio": 2.0},
            "userAgent": "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36"
        }
        chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    else:
        # Set window size for desktop mode
        chrome_options.add_argument(f"--window-size={width},{height}")
    
    try:
        # Initialize the browser
        print("Initializing browser...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Navigate to the URL
        print(f"Navigating to {url}...")
        driver.get(url)
        
        # Wait for the page to load
        print(f"Waiting {wait_time} seconds for page to load...")
        time.sleep(wait_time)
        
        # Take a screenshot
        print(f"Taking screenshot and saving to {output_file}...")
        driver.save_screenshot(output_file)
        
        # Print the screenshot if requested
        if print_output:
            print("Printing screenshot...")
            print_image(output_file)
            print("Screenshot printed successfully")
        
        # Close the browser
        driver.quit()
        print("Browser closed")
        
        return output_file
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Visit a URL and print a screenshot")
    parser.add_argument("url", help="The URL to visit")
    parser.add_argument("--output", "-o", default="screenshot.png", help="Output filename for the screenshot")
    parser.add_argument("--no-print", action="store_true", help="Don't print the screenshot")
    parser.add_argument("--desktop", action="store_true", help="Use desktop mode instead of mobile mode")
    parser.add_argument("--width", type=int, default=384, help="Width of the browser window/screenshot")
    parser.add_argument("--height", type=int, default=800, help="Height of the browser window/screenshot")
    parser.add_argument("--wait", type=int, default=5, help="How long to wait for the page to load (seconds)")
    
    args = parser.parse_args()
    
    # Visit the URL and print the screenshot
    visit_and_print(
        args.url,
        output_file=args.output,
        print_output=not args.no_print,
        mobile_mode=not args.desktop,
        width=args.width,
        height=args.height,
        wait_time=args.wait
    )
