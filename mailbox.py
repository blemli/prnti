#!/usr/bin/env python

from imap_tools import MailBox, AND, OR, NOT
import re
import time
import threading
import queue
from typing import Optional

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


class MailMonitor:
    """
    Threaded mail monitor with automatic restart capability to prevent hanging.
    """
    
    def __init__(self, sender: str, host: str, username: str, password: str, 
                 folder: str = 'INBOX', mail_timeout: int = 300, watchdog_timeout: int = 120):
        self.sender = sender
        self.host = host
        self.username = username
        self.password = password
        self.folder = folder
        self.mail_timeout = mail_timeout
        self.watchdog_timeout = watchdog_timeout
        
        self.mail_queue = queue.Queue()
        self.mail_thread = None
        self.watchdog_thread = None
        self.stop_event = threading.Event()
        self.last_activity = time.time()
        self.restart_count = 0
        
    def _mail_worker(self):
        """Worker thread that monitors for new mail."""
        thread_id = threading.current_thread().ident
        print(f"Mail worker thread {thread_id} started")
        
        try:
            while not self.stop_event.is_set():
                try:
                    # Update activity timestamp
                    self.last_activity = time.time()
                    
                    # Wait for mail with the configured timeout
                    msg = wait_for_mail(self.sender, self.host, self.username, 
                                      self.password, self.folder, self.mail_timeout)
                    
                    # Update activity timestamp after operation
                    self.last_activity = time.time()
                    
                    if msg is not None:
                        # Put the message in the queue for the main thread
                        self.mail_queue.put(msg)
                        print(f"Mail worker thread {thread_id} found message: {msg.subject}")
                    else:
                        # Timeout reached, continue loop
                        print(f"Mail worker thread {thread_id} timeout reached, continuing...")
                        
                except Exception as e:
                    print(f"Error in mail worker thread {thread_id}: {e}")
                    # Update activity to prevent watchdog from restarting due to exceptions
                    self.last_activity = time.time()
                    # Wait a bit before retrying
                    time.sleep(10)
                    
        except Exception as e:
            print(f"Fatal error in mail worker thread {thread_id}: {e}")
        finally:
            print(f"Mail worker thread {thread_id} exiting")
    
    def _watchdog_worker(self):
        """Watchdog thread that monitors the mail thread and restarts it if it hangs."""
        print("Watchdog thread started")
        
        while not self.stop_event.is_set():
            try:
                # Check if mail thread is still alive and active
                current_time = time.time()
                time_since_activity = current_time - self.last_activity
                
                if (self.mail_thread is None or 
                    not self.mail_thread.is_alive() or 
                    time_since_activity > self.watchdog_timeout):
                    
                    if time_since_activity > self.watchdog_timeout:
                        print(f"Mail thread appears to be hanging (no activity for {time_since_activity:.1f}s)")
                    elif self.mail_thread is None:
                        print("Mail thread is None, starting new thread")
                    else:
                        print("Mail thread has died, restarting")
                    
                    self._restart_mail_thread()
                
                # Sleep for a short interval before checking again
                self.stop_event.wait(10)  # Check every 10 seconds
                
            except Exception as e:
                print(f"Error in watchdog thread: {e}")
                time.sleep(10)
        
        print("Watchdog thread exiting")
    
    def _restart_mail_thread(self):
        """Restart the mail monitoring thread."""
        self.restart_count += 1
        print(f"Restarting mail thread (restart #{self.restart_count})")
        
        # Stop the old thread if it exists
        if self.mail_thread is not None and self.mail_thread.is_alive():
            print("Attempting to stop existing mail thread...")
            # Note: We can't forcefully kill threads in Python, but the thread should
            # exit naturally when it hits the next timeout or exception
        
        # Start a new mail thread
        self.mail_thread = threading.Thread(target=self._mail_worker, daemon=True)
        self.mail_thread.start()
        self.last_activity = time.time()
        print(f"New mail thread started with ID: {self.mail_thread.ident}")
    
    def start(self):
        """Start the mail monitoring system."""
        print("Starting MailMonitor...")
        self.stop_event.clear()
        self.last_activity = time.time()
        
        # Start the mail worker thread
        self.mail_thread = threading.Thread(target=self._mail_worker, daemon=True)
        self.mail_thread.start()
        
        # Start the watchdog thread
        self.watchdog_thread = threading.Thread(target=self._watchdog_worker, daemon=True)
        self.watchdog_thread.start()
        
        print("MailMonitor started successfully")
    
    def stop(self):
        """Stop the mail monitoring system."""
        print("Stopping MailMonitor...")
        self.stop_event.set()
        
        # Wait for threads to finish (with timeout)
        if self.watchdog_thread and self.watchdog_thread.is_alive():
            self.watchdog_thread.join(timeout=5)
        
        if self.mail_thread and self.mail_thread.is_alive():
            self.mail_thread.join(timeout=5)
        
        print("MailMonitor stopped")
    
    def get_message(self, timeout: Optional[float] = None) -> Optional[object]:
        """
        Get a message from the mail queue.
        
        Args:
            timeout: Maximum time to wait for a message (None = block indefinitely)
            
        Returns:
            MailMessage object or None if timeout reached
        """
        try:
            return self.mail_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_restart_count(self) -> int:
        """Get the number of times the mail thread has been restarted."""
        return self.restart_count


def extract_article_url(msg):
    """
    Extract the first Mailchimp article URL from the given MailMessage.
    Returns the URL string or None if not found.
    """
    if msg is None:
        print("Cannot extract URL from None message")
        return None
        
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
