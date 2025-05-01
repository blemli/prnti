#!/usr/bin/env python

from epsontm import print_image, print_text
from mailbox import wait_for_mail, extract_article_url
from browser import visit_and_print
import requests, os
from icecream import ic
from dotenv import load_dotenv


load_dotenv()


if __name__=="__main__":
    host=os.getenv("PRNTI_MAIL_HOST")
    sender=os.getenv("WNTI_SENDER")
    password=os.getenv("PRNTI_MAIL_PASS")
    username=os.getenv("PRNTI_MAIL_USER")
    ic(host,sender,password,username)
    
    # Wait for an email and extract the article URL
    print("Waiting for email...")
    msg=wait_for_mail(sender,host,username,password)
    
    # Print the email subject
    print("Printing email subject...")
    print_text(msg.subject)
    
    # Extract the article URL
    article_url=extract_article_url(msg)
    print("Article URL:", article_url)
    
    if article_url:
        # Visit the URL in mobile mode, take a screenshot of the full page, and print it
        print("Visiting article URL and printing screenshot...")
        screenshot_file = visit_and_print(
            url=article_url,
            output_file="article_screenshot.png",
            print_output=True,
            mobile_mode=True,
            width=384,  # Width suitable for thermal printer
            height=800,
            wait_time=10,  # Wait longer to ensure page loads fully
            full_page=True  # Capture the full page by scrolling
        )
        
        if screenshot_file:
            print(f"Screenshot saved to {screenshot_file} and printed successfully")
        else:
            print("Failed to take or print screenshot")
    else:
        print("No article URL found in the email")
