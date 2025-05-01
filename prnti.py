#!/usr/bin/env python

from epsontm import  print_image

from imap_tools import MailBox, AND


def wait_for_mail(sender: str, host: str, username: str, password: str, folder: str = 'INBOX'):
    """
    Block until a new unseen email arrives from the specified sender.
    Returns the first MailMessage instance from that sender.
    """
    with MailBox(host).login(username, password, initial_folder=folder) as mailbox:
        # Start IDLE mode
        mailbox.idle.start()
        try:
            while True:
                # Poll for server responses (new messages, etc.)
                responses = mailbox.idle.poll(timeout=30)
                if responses:
                    # Fetch the first unseen message from the sender
                    msgs = list(mailbox.fetch(
                        AND(from_=sender, seen=False),
                        limit=1
                    ))
                    if msgs:
                        return msgs[0]
        finally:
            # Ensure IDLE is stopped cleanly
            mailbox.idle.stop()
