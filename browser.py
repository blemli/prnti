#!/usr/bin/env python

import os
import time
import argparse
import platform
import subprocess
from PIL import Image

from epsontm import print_image
from playwright.sync_api import sync_playwright
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from pdf2image import convert_from_path
from PIL import Image
from PIL import Image


# Import epsontm only when needed to avoid errors if not printing
def get_print_image():
    return print_image

def visit_and_print(url, output_file="screenshot.png", print_output=True, mobile_mode=True, 
                   width=384, height=800, wait_time=5, full_page=True):
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
        full_page: Whether to capture the full page (scrolling if needed)
    
    Returns:
        The path to the screenshot file
    """
    print(f"Visiting URL: {url}")
    
    # Detect Raspberry Pi
    is_raspi = _is_raspberry_pi()
    if is_raspi:
        print("Detected Raspberry Pi environment")
    
    # Determine which approach to use based on available libraries and platform
    if is_raspi:
        # On Raspberry Pi, prefer lighter-weight options
        try:
            return _visit_with_wkhtmltopdf(url, output_file, print_output, mobile_mode, width, height, wait_time, full_page)
        except Exception as e:
            print(f"wkhtmltopdf failed: {str(e)}")
            try:
                return _visit_with_playwright(url, output_file, print_output, mobile_mode, width, height, wait_time, full_page)
            except ImportError:
                print("Playwright not available, trying Selenium...")
                try:
                    return _visit_with_selenium(url, output_file, print_output, mobile_mode, width, height, wait_time, full_page)
                except Exception as e:
                    print(f"All methods failed: {str(e)}")
                    return None
    else:
        # On other platforms, prefer Playwright
        try:
            return _visit_with_playwright(url, output_file, print_output, mobile_mode, width, height, wait_time, full_page)
        except ImportError:
            print("Playwright not available, trying Selenium...")
            try:
                return _visit_with_selenium(url, output_file, print_output, mobile_mode, width, height, wait_time, full_page)
            except ImportError:
                print("Selenium not available, trying wkhtmltopdf...")
                try:
                    return _visit_with_wkhtmltopdf(url, output_file, print_output, mobile_mode, width, height, wait_time, full_page)
                except Exception as e:
                    print(f"Error with wkhtmltopdf: {str(e)}")
                    print("All browser automation methods failed. Please install one of: playwright, selenium, or wkhtmltopdf")
                    return None

def _is_raspberry_pi():
    """Check if running on a Raspberry Pi"""
    # Check for Raspberry Pi-specific files
    if os.path.exists('/proc/device-tree/model'):
        with open('/proc/device-tree/model') as f:
            model = f.read()
            if 'Raspberry Pi' in model:
                return True
    
    # Check CPU info
    if os.path.exists('/proc/cpuinfo'):
        with open('/proc/cpuinfo') as f:
            cpuinfo = f.read()
            if 'BCM2708' in cpuinfo or 'BCM2709' in cpuinfo or 'BCM2711' in cpuinfo or 'BCM2835' in cpuinfo:
                return True
    
    # Check platform
    if platform.machine().startswith('arm') and platform.system() == 'Linux':
        return True
    
    return False

def _visit_with_playwright(url, output_file, print_output, mobile_mode, width, height, wait_time, full_page):
    """Use Playwright to visit the URL and take a screenshot"""
    try:
        
        print("Using Playwright for browser automation")
        with sync_playwright() as p:
            # Choose browser (chromium is usually most reliable)
            browser_type = p.chromium
            
            # Launch browser with appropriate options for the platform
            browser_args = []
            if _is_raspberry_pi():
                # Additional args for Raspberry Pi
                browser_args = [
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--single-process'  # Important for low-memory devices
                ]
            
            browser = browser_type.launch(headless=True, args=browser_args)
            
            if mobile_mode:
                print("Using mobile emulation mode")
                # Mobile device settings
                device = browser_type.devices["Pixel 5"]
                context = browser.new_context(**device)
            else:
                # Desktop settings
                context = browser.new_context(viewport={"width": width, "height": height})
            
            # Create a new page and navigate to the URL
            page = context.new_page()
            print(f"Navigating to {url}...")
            page.goto(url)
            
            # Wait for the page to load
            print(f"Waiting {wait_time} seconds for page to load...")
            page.wait_for_timeout(wait_time * 1000)  # Convert to milliseconds
            
            # Ensure content is fully loaded by scrolling
            if full_page:
                print("Scrolling through page to ensure all content is loaded...")
                # Get page height
                page_height = page.evaluate("""() => {
                    return Math.max(
                        document.body.scrollHeight,
                        document.documentElement.scrollHeight,
                        document.body.offsetHeight,
                        document.documentElement.offsetHeight
                    );
                }""")
                
                # Scroll through the page to ensure all content is loaded
                viewport_height = page.viewport_size['height']
                for scroll_pos in range(0, page_height, viewport_height // 2):  # Overlap by 50%
                    page.evaluate(f"window.scrollTo(0, {scroll_pos})")
                    page.wait_for_timeout(500)  # Wait for any lazy-loaded content
                
                # Scroll back to top
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(500)
            
            # Take a screenshot
            print(f"Taking screenshot and saving to {output_file}...")
            
            if full_page:
                print("Capturing full page...")
                # Playwright has built-in full page screenshot capability
                page.screenshot(path=output_file, full_page=True)
            else:
                # Just capture the viewport
                page.screenshot(path=output_file)
            
            # Close the browser
            browser.close()
            print("Browser closed")
            
            # Resize image if needed to fit printer width
            _resize_image_if_needed(output_file, width)
            
            # Print the screenshot if requested
            if print_output:
                print("Printing screenshot...")
                print_image = get_print_image()
                print_image(output_file)
                print("Screenshot printed successfully")
            
            return output_file
    except ImportError:
        raise

def _visit_with_selenium(url, output_file, print_output, mobile_mode, width, height, wait_time, full_page):
    """Use Selenium to visit the URL and take a screenshot"""
    
    print("Using Selenium for browser automation")
    
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Additional options for Raspberry Pi
    if _is_raspberry_pi():
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--single-process")
    
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
        # Initialize the browser - handle different platforms
        system = platform.system()
        is_raspi = _is_raspberry_pi()
        
        if is_raspi or (system == "Darwin" and platform.processor() == "arm"):
            # Raspberry Pi or macOS on Apple Silicon
            print(f"Detected special platform: {'Raspberry Pi' if is_raspi else 'macOS ARM'}")
            driver = webdriver.Chrome(options=chrome_options)
        else:
            # Other platforms
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Navigate to the URL
        print(f"Navigating to {url}...")
        driver.get(url)
        
        # Wait for the page to load
        print(f"Waiting {wait_time} seconds for page to load...")
        time.sleep(wait_time)
        
        if full_page:
            print("Capturing full page (scrolling if needed)...")
            
            # Get page dimensions
            total_height = driver.execute_script("return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight, document.body.offsetHeight, document.documentElement.offsetHeight, document.body.clientHeight, document.documentElement.clientHeight);")
            viewport_height = driver.execute_script("return window.innerHeight")
            viewport_width = driver.execute_script("return window.innerWidth")
            
            print(f"Page dimensions: {viewport_width}x{total_height} (viewport height: {viewport_height})")
            
            if total_height > viewport_height:
                # First scroll through the entire page to ensure all content is loaded
                print("Pre-scrolling to load all content...")
                for pos in range(0, total_height, viewport_height // 2):  # Overlap by 50%
                    driver.execute_script(f"window.scrollTo(0, {pos});")
                    time.sleep(0.5)  # Wait for any lazy-loaded content
                
                # Scroll back to top
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)
                
                # Re-measure height after scrolling (in case of dynamic content)
                total_height = driver.execute_script("return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight, document.body.offsetHeight, document.documentElement.offsetHeight, document.body.clientHeight, document.documentElement.clientHeight);")
                print(f"Updated page height after scrolling: {total_height}")
                
                # Need to scroll and stitch
                temp_screenshots = []
                
                # Take screenshots at different scroll positions
                scroll_positions = list(range(0, total_height, viewport_height - 50))  # 50px overlap
                if scroll_positions[-1] < total_height:
                    scroll_positions.append(total_height - viewport_height)  # Add the bottom of the page
                
                print(f"Taking {len(scroll_positions)} screenshots at different scroll positions...")
                for i, pos in enumerate(scroll_positions):
                    driver.execute_script(f"window.scrollTo(0, {pos});")
                    time.sleep(0.5)  # Wait for scroll to complete
                    
                    temp_file = f"temp_screenshot_{i}.png"
                    driver.save_screenshot(temp_file)
                    temp_screenshots.append(temp_file)
                    print(f"Took screenshot at scroll position {pos}/{total_height}")
                
                # Stitch screenshots together
                _stitch_screenshots(temp_screenshots, output_file, width)
                
                # Clean up temp files
                for temp_file in temp_screenshots:
                    os.remove(temp_file)
            else:
                # Page fits in viewport, just take a single screenshot
                print("Page fits in viewport, taking single screenshot")
                driver.save_screenshot(output_file)
        else:
            # Just capture the current viewport
            driver.save_screenshot(output_file)
        
        # Close the browser
        driver.quit()
        print("Browser closed")
        
        # Resize image if needed
        _resize_image_if_needed(output_file, width)
        
        # Print the screenshot if requested
        if print_output:
            print("Printing screenshot...")
            print_image = get_print_image()
            print_image(output_file)
            print("Screenshot printed successfully")
        
        return output_file
        
    except Exception as e:
        print(f"Selenium error: {str(e)}")
        raise

def _visit_with_wkhtmltopdf(url, output_file, print_output, mobile_mode, width, height, wait_time, full_page):
    """Use wkhtmltopdf to visit the URL and take a screenshot"""
    print("Using wkhtmltopdf for browser automation")
    
    # Ensure output file has .png extension
    if not output_file.endswith('.png'):
        pdf_file = output_file + '.pdf'
    else:
        pdf_file = output_file.replace('.png', '.pdf')
    
    # Build the command
    cmd = ['wkhtmltopdf']
    
    # Add options
    if mobile_mode:
        print("Using mobile emulation mode")
        cmd.extend(['--user-agent', 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36'])
    
    # Set width
    cmd.extend(['--width', str(width)])
    
    # For full page, don't set height to allow it to be as long as needed
    if not full_page:
        cmd.extend(['--height', str(height)])
    
    # Other options
    cmd.extend(['--javascript-delay', str(wait_time * 1000)])  # Convert to milliseconds
    cmd.extend(['--no-stop-slow-scripts'])
    cmd.extend(['--enable-javascript'])
    cmd.extend(['--enable-plugins'])
    
    # Quality options
    cmd.extend(['--image-quality', '100'])
    
    # Add URL and output file
    cmd.extend([url, pdf_file])
    
    # Run the command
    print(f"Running command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    
    # Convert PDF to PNG
    if output_file.endswith('.png'):
        try:
            print(f"Converting PDF to PNG: {pdf_file} -> {output_file}")
            
            # On Raspberry Pi, we might need to use lower DPI for memory constraints
            dpi = 150 if _is_raspberry_pi() else 300
            
            images = convert_from_path(pdf_file, dpi=dpi)
            images[0].save(output_file)
            
            # Remove the PDF file
            os.remove(pdf_file)
        except ImportError:
            print("pdf2image not available, keeping PDF output")
            output_file = pdf_file
    
    # Resize image if needed
    _resize_image_if_needed(output_file, width)
    
    # Print the screenshot if requested
    if print_output:
        print("Printing screenshot...")
        print_image = get_print_image()
        print_image(output_file)
        print("Screenshot printed successfully")
    
    return output_file

def _stitch_screenshots(screenshot_files, output_file, target_width=None):
    """Stitch multiple screenshots together vertically"""
    
    print(f"Stitching {len(screenshot_files)} screenshots together...")
    
    # Open all images
    images = [Image.open(f) for f in screenshot_files]
    
    # Get dimensions
    widths, heights = zip(*(i.size for i in images))
    max_width = max(widths)
    
    # Calculate total height with overlap removal
    # Assuming 50px overlap between screenshots
    overlap = 50
    total_height = sum(heights) - overlap * (len(images) - 1)
    
    # Create a new image with the combined height
    stitched = Image.new('RGB', (max_width, total_height))
    
    # Paste each image with overlap
    y_offset = 0
    for i, img in enumerate(images):
        stitched.paste(img, (0, y_offset))
        
        # For all but the last image, move offset by height minus overlap
        if i < len(images) - 1:
            y_offset += img.size[1] - overlap
        else:
            y_offset += img.size[1]
    
    # Resize if needed
    if target_width and max_width != target_width:
        ratio = target_width / max_width
        new_height = int(total_height * ratio)
        stitched = stitched.resize((target_width, new_height), Image.LANCZOS)
    
    # Save the result
    stitched.save(output_file)
    print(f"Stitched image saved to {output_file}")

def _resize_image_if_needed(image_path, target_width):
    """Resize an image to the target width while maintaining aspect ratio"""
    try:
        
        # Check if the file exists and is an image
        if not os.path.exists(image_path):
            print(f"Image file not found: {image_path}")
            return
        
        # Skip for PDF files
        if image_path.lower().endswith('.pdf'):
            return
        
        # Open the image
        img = Image.open(image_path)
        width, height = img.size
        
        # Check if resizing is needed
        if width != target_width:
            print(f"Resizing image from {width}x{height} to {target_width} width...")
            
            # Calculate new height to maintain aspect ratio
            ratio = target_width / width
            new_height = int(height * ratio)
            
            # Resize the image
            resized = img.resize((target_width, new_height), Image.LANCZOS)
            
            # Save the resized image
            resized.save(image_path)
            print(f"Resized image saved to {image_path}")
    except Exception as e:
        print(f"Error resizing image: {str(e)}")

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
    parser.add_argument("--no-full-page", action="store_true", help="Don't capture the full page (just the viewport)")
    
    args = parser.parse_args()
    
    # Visit the URL and print the screenshot
    visit_and_print(
        args.url,
        output_file=args.output,
        print_output=not args.no_print,
        mobile_mode=not args.desktop,
        width=args.width,
        height=args.height,
        wait_time=args.wait,
        full_page=not args.no_full_page
    )
