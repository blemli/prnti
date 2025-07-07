#!/usr/bin/env python

from tsp800 import print_image
from mailbox import MailMonitor, extract_article_url
from browser import full_page_screenshot
from icecream import ic
import os
import signal
import sys
from dotenv import load_dotenv


load_dotenv()


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    print("\nReceived shutdown signal, stopping mail monitor...")
    if 'mail_monitor' in globals():
        mail_monitor.stop()
    sys.exit(0)


if __name__=="__main__":
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    host=os.getenv("PRNTI_MAIL_HOST")
    sender=os.getenv("WNTI_SENDER")
    password=os.getenv("PRNTI_MAIL_PASS")
    username=os.getenv("PRNTI_MAIL_USER")
    #ic(host,sender,password,username)
    
    # Create and start the mail monitor with 2-minute watchdog timeout
    mail_monitor = MailMonitor(
        sender=sender,
        host=host,
        username=username,
        password=password,
        mail_timeout=300,  # 5 minutes for individual mail operations
        watchdog_timeout=120  # 2 minutes watchdog timeout
    )
    
    print("Starting mail monitoring system...")
    mail_monitor.start()
    
    try:
        while True:
            # Wait for an email and extract the article URL
            print("Waiting for email...")
            msg = mail_monitor.get_message(timeout=None)  # Block indefinitely
            
            if msg is None:
                print("No message received (this shouldn't happen with timeout=None)")
                continue
                
            # Extract the article URL
            article_url = extract_article_url(msg)
            print("Article URL:", article_url)
            
            if article_url:
                # Visit the URL in mobile mode, take a screenshot of the full page, and print it
                print("Visiting article URL and printing screenshot...")
                screenshot_file = full_page_screenshot(article_url)
                if screenshot_file:
                    print(f"Screenshot saved to {screenshot_file} and printed successfully")
                    print_image(screenshot_file, cut=False)
                    print_image("whitespace.jpg", cut=False)
                    os.remove(screenshot_file)
                else:
                    print("Failed to take or print screenshot")
            else:
                print("No article URL found in the email")
                
            # Log restart count for monitoring
            restart_count = mail_monitor.get_restart_count()
            if restart_count > 0:
                print(f"Mail monitor has restarted {restart_count} times")
                
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Unexpected error in main loop: {e}")
    finally:
        print("Stopping mail monitor...")
        mail_monitor.stop()
        print("Mail monitor stopped")
