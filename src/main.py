import schedule
import time
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from auth import get_gmail_service
from utils import (get_email_body, is_job_related, summarize_email, send_notification, 
                  load_notification_schedule, save_notification_schedule)
from gui import start_viewer
import threading
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

service = None

def process_emails():
    """Process new emails, ensuring no duplicates are reprocessed."""
    global service
    try:
        if service is None:
            service = get_gmail_service()
        logging.info("Gmail service initialized.")
        
        try:
            with open('last_run.txt', 'r') as f:
                last_run = f.read().strip()
            if not last_run.isdigit():
                raise ValueError("Invalid last_run.txt content")
        except (FileNotFoundError, ValueError):
            last_run = str(int(time.time() - 86400))  # Default to last 24 hours
            logging.info("Reset last_run to 24 hours ago.")
        
        query = f'after:{last_run}'
        logging.info(f"Fetching emails with query: {query}")
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        logging.info(f"Found {len(messages)} new emails.")
        
        # Load existing email IDs
        try:
            with open('notifications.json', 'r') as f:
                existing_notifications = json.load(f)
            existing_ids = {n.get('email_id') for n in existing_notifications if n.get('email_id')}
            logging.info(f"Loaded {len(existing_ids)} existing email IDs.")
        except FileNotFoundError:
            existing_ids = set()
            logging.info("No notifications.json found, starting fresh.")

        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
            subject = next((header['value'] for header in msg_data['payload']['headers'] if header['name'] == 'Subject'), 'No Subject')
            email_body = get_email_body(msg_data['payload'])
            full_text = f"Subject: {subject}\n\n{email_body}"
            logging.info(f"Processing email ID {msg['id']}: {full_text[:50]}...")
            
            if msg['id'] not in existing_ids and is_job_related(full_text):
                summary, key_date = summarize_email(full_text)
                logging.info(f"New job-related email detected: {msg['id']}")
                send_notification('New Job Email', summary, msg['id'])
                existing_ids.add(msg['id'])  # Add to in-memory set immediately
                if key_date:
                    schedule_key_date_notifications(key_date, summary)
            else:
                logging.info(f"Skipping email ID {msg['id']}: Already processed or not job-related.")
        
        with open('last_run.txt', 'w') as f:
            f.write(str(int(time.time())))
        logging.info("Updated last_run.txt with current timestamp.")
        
    except Exception as e:
        logging.error(f"Error processing emails: {e}")

def schedule_key_date_notifications(key_date, summary):
    today = datetime.now().date()
    week_before = (key_date - timedelta(days=7)).date()
    day_before = (key_date - timedelta(days=1)).date()
    week_message = f"Reminder: Joining date for job is in one week.\n{summary}"
    day_message = f"Reminder: Joining date for job is tomorrow.\n{summary}"
    schedule_list = load_notification_schedule()
    if week_before >= today:
        schedule_list.append({"date": week_before.strftime('%Y-%m-%d'), "message": week_message})
    if day_before >= today:
        schedule_list.append({"date": day_before.strftime('%Y-%m-%d'), "message": day_message})
    save_notification_schedule(schedule_list)

def check_deadline_notifications():
    try:
        today = datetime.now().date()
        schedule_list = load_notification_schedule()
        new_schedule = []
        for entry in schedule_list:
            notification_date = datetime.strptime(entry["date"], '%Y-%m-%d').date()
            if notification_date <= today:
                send_notification("Joining Date Reminder", entry["message"])
            else:
                new_schedule.append(entry)
        save_notification_schedule(new_schedule)
    except Exception as e:
        logging.error(f"Error checking deadline notifications: {e}")

def run_tasks():
    schedule.every(10).minutes.do(process_emails)
    schedule.every(10).minutes.do(check_deadline_notifications)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    process_emails()
    task_thread = threading.Thread(target=run_tasks)
    task_thread.daemon = True
    task_thread.start()
    start_viewer(process_emails)