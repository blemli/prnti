#!/usr/bin/env python

from epsontm import  print_image, print_text
from mailbox import wait_for_mail, extract_article_url
import requests,os
from icecream import ic
from dotenv import load_dotenv


load_dotenv()


if __name__=="__main__":
    host=os.getenv("PRNTI_MAIL_HOST")
    sender=os.getenv("WNTI_SENDER")
    password=os.getenv("PRNTI_MAIL_PASS")
    username=os.getenv("PRNTI_MAIL_USER")
    ic(host,sender,password,username)
    msg=wait_for_mail(sender,host,username,password)
    print_text(msg.subject)
    article_url=extract_article_url(msg)
    print("Article URL:", article_url)
    # Download the article
    response = requests.get(article_url)
    if response.status_code == 200:
        with open("article.html", "wb") as f:
            f.write(response.content)
        print("Article downloaded successfully.")
    else:
        print("Failed to download article.")
