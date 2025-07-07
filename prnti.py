#!/usr/bin/env python

from tsp800 import print_image
from mailbox import wait_for_mail, extract_article_url
from browser import full_page_screenshot
from icecream import ic
import os
from dotenv import load_dotenv


load_dotenv()


if __name__=="__main__":
    host=os.getenv("PRNTI_MAIL_HOST")
    sender=os.getenv("WNTI_SENDER")
    password=os.getenv("PRNTI_MAIL_PASS")
    username=os.getenv("PRNTI_MAIL_USER")
    #ic(host,sender,password,username)
    while True:
        # Wait for an email and extract the article URL
        print("Waiting for email...")
        msg=wait_for_mail(sender,host,username,password)
        if msg is None:
            continue
        # Extract the article URL
        article_url=extract_article_url(msg)
        print("Article URL:", article_url)
        if article_url:
            # Visit the URL in mobile mode, take a screenshot of the full page, and print it
            print("Visiting article URL and printing screenshot...")
            screenshot_file=full_page_screenshot(article_url)
            if screenshot_file:
                print(f"Screenshot saved to {screenshot_file} and printed successfully")
                print_image(screenshot_file,cut=False)
                print_image("whitespace.jpg",cut=False)
                os.remove(screenshot_file)
            else:
                print("Failed to take or print screenshot")
        else:
            print("No article URL found in the email")
