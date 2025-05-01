#!/usr/bin/env python

from imap_tools import MailBox, AND, OR, NOT
import re
import time

def wait_for_mail(sender: str, host: str, username: str, password: str, folder: str = 'INBOX', timeout: int = 300):
    """
    Block until a new unseen email arrives from the specified sender.
    Returns the first unseen MailMessage instance from that sender and marks it as seen.
    This ensures each email is only handled once.
    
    Args:
        sender: Email address of the sender to filter by
        host: IMAP server hostname
        username: Email account username
        password: Email account password
        folder: Mailbox folder to check (default: INBOX)
        timeout: Maximum time to wait in seconds (default: 300 seconds / 5 minutes)
    
    Returns:
        The first unseen MailMessage from the sender or None if timeout is reached
    """
    start_time = time.time()
    end_time = start_time + timeout
    
    print(f"Connecting to mailbox at {host} as {username}")
    
    with MailBox(host).login(username, password, initial_folder=folder) as mailbox:
        # First check if there are any existing unseen messages from the sender
        print(f"Checking for existing unseen messages from {sender}...")
        
        # Try different search criteria to find unseen messages
        search_criteria = AND(from_=sender, seen=False)
        existing_msgs = list(mailbox.fetch(search_criteria, limit=1))
        
        if existing_msgs:
            msg = existing_msgs[0]
            print(f"Found unseen message: '{msg.subject}' from {msg.from_}")
            
            # Mark the message as seen to prevent processing it again
            print(f"Marking message as seen (UID: {msg.uid})")
            try:
                mailbox.flag(msg.uid, '\\Seen', True)
                print("Message marked as seen successfully")
            except Exception as e:
                print(f"Error marking message as seen: {e}")
            
            return msg
        
        # If no unseen messages found, try checking for any messages from the sender
        # This is a fallback in case the UNSEEN flag is not working correctly
        print("No unseen messages found, checking for any messages from sender...")
        all_msgs = list(mailbox.fetch(f'FROM "{sender}"', limit=10))
        
        if all_msgs:
            print(f"Found {len(all_msgs)} total messages from {sender}")
            print("Message flags:")
            for i, msg in enumerate(all_msgs[:3]):  # Show up to 3
                print(f"  {i+1}. Subject: {msg.subject} | Flags: {msg.flags}")
        
        print(f"No existing unseen messages from {sender}, waiting for new ones...")
        print(f"Will wait up to {timeout} seconds for new messages")
        
        # Try both IDLE mode and regular polling
        try:
            # Start IDLE mode
            print("Starting IDLE mode...")
            mailbox.idle.start()
            
            while time.time() < end_time:
                # Calculate remaining time
                remaining = end_time - time.time()
                if remaining <= 0:
                    print("Timeout reached, no new messages received")
                    return None
                
                # Poll for server responses with a shorter timeout
                poll_timeout = min(10, remaining)
                print(f"Polling for new messages (timeout: {poll_timeout:.1f}s)...")
                
                responses = mailbox.idle.poll(timeout=poll_timeout)
                
                if responses:
                    print(f"Received responses: {responses}")
                    
                    # Stop IDLE mode temporarily to perform operations
                    mailbox.idle.stop()
                    
                    # Check for new messages from the sender
                    print("Checking for new messages after receiving notification...")
                    
                    # First try with UNSEEN flag
                    unseen_msgs = list(mailbox.fetch(AND(from_=sender, seen=False), limit=1))
                    
                    if unseen_msgs:
                        msg = unseen_msgs[0]
                        print(f"Found unseen message: '{msg.subject}' from {msg.from_}")
                        
                        # Mark the message as seen
                        print(f"Marking message as seen (UID: {msg.uid})")
                        try:
                            mailbox.flag(msg.uid, '\\Seen', True)
                            print("Message marked as seen successfully")
                        except Exception as e:
                            print(f"Error marking message as seen: {e}")
                        
                        return msg
                    
                    # If no unseen messages found, try checking for any recent messages
                    recent_msgs = list(mailbox.fetch('RECENT', limit=5))
                    if recent_msgs:
                        print(f"Found {len(recent_msgs)} recent messages")
                        for i, msg in enumerate(recent_msgs):
                            print(f"  {i+1}. From: {msg.from_} | Subject: {msg.subject}")
                            
                            # If from the sender, return it
                            if sender.lower() in msg.from_.lower():
                                print(f"Found recent message from sender: '{msg.subject}'")
                                
                                # Mark the message as seen
                                print(f"Marking message as seen (UID: {msg.uid})")
                                try:
                                    mailbox.flag(msg.uid, '\\Seen', True)
                                    print("Message marked as seen successfully")
                                except Exception as e:
                                    print(f"Error marking message as seen: {e}")
                                
                                return msg
                    
                    print("No matching messages found despite receiving notifications")
                    
                    # Restart IDLE mode
                    mailbox.idle.start()
                else:
                    # No new messages, continue waiting
                    print("No new messages, continuing to wait...")
                    
                    # Periodically check for messages even without IDLE notification
                    # This helps in case IDLE notifications are not working properly
                    if time.time() - start_time > 0 and (time.time() - start_time) % 30 < 1:
                        # Stop IDLE mode temporarily
                        mailbox.idle.stop()
                        
                        print("Performing periodic check for new messages...")
                        unseen_msgs = list(mailbox.fetch(AND(from_=sender, seen=False), limit=1))
                        
                        if unseen_msgs:
                            msg = unseen_msgs[0]
                            print(f"Found unseen message during periodic check: '{msg.subject}' from {msg.from_}")
                            
                            # Mark the message as seen
                            print(f"Marking message as seen (UID: {msg.uid})")
                            try:
                                mailbox.flag(msg.uid, '\\Seen', True)
                                print("Message marked as seen successfully")
                            except Exception as e:
                                print(f"Error marking message as seen: {e}")
                            
                            return msg
                        
                        # Restart IDLE mode
                        mailbox.idle.start()
            
            print("Timeout reached, no new messages received")
            return None
            
        finally:
            # Ensure IDLE is stopped cleanly
            print("Stopping IDLE mode")
            try:
                mailbox.idle.stop()
            except Exception as e:
                print(f"Error stopping IDLE mode: {e}")


def extract_article_url(msg):
    """
    Extract the first Mailchimp article URL from the given MailMessage.
    Returns the URL string or None if not found.
    """
    content = msg.text or msg.html or ''
    # Updated pattern to match the full URL including hyphens, query parameters, etc.
    # Exclude closing parenthesis from the URL
    pattern = r'https://mailchi\.mp/wnti/[A-Za-z0-9\-_]+(?:[?&][^"\s<>()]+)*'
    match = re.search(pattern, content)
    
    if match:
        url = match.group(0)
        print(f"Extracted URL: {url}")
        return url
    else:
        print("No Mailchimp URL found in the message")
        return None
