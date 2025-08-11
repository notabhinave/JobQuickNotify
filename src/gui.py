import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import json
from datetime import datetime, timedelta
import threading
import time

def load_notifications():
    """Load notifications from the JSON file."""
    try:
        with open('notifications.json', 'r') as f:
            notifications = json.load(f)
        return notifications
    except FileNotFoundError:
        return []

def get_unread_notifications(notifications):
    """Filter notifications that are unread."""
    return [n for n in notifications if n['status'] == 'unread']

def get_read_notifications(notifications):
    """Filter notifications that are read."""
    return [n for n in notifications if n['status'] == 'read']

def get_recent_notifications(notifications, days=7):
    """Filter notifications from the last specified number of days."""
    recent_date = datetime.now() - timedelta(days=days)
    return [n for n in notifications if datetime.fromisoformat(n['timestamp']) >= recent_date]

def display_notifications(text_widget, notifications):
    """Display notifications in the text widget with separators and styling."""
    text_widget.delete('1.0', tk.END)
    for n in notifications:
        text_widget.insert(tk.END, f"[{n['timestamp']}] {n['title']}\n", ('timestamp',))
        text_widget.insert(tk.END, n['message'] + '\n', ('unread' if n['status'] == 'unread' else 'read'))
        text_widget.insert(tk.END, '-'*50 + '\n', ('separator',))

def configure_tags(text_widget):
    """Configure text widget tags for styling."""
    text_widget.tag_configure('timestamp', foreground='gray')
    text_widget.tag_configure('unread', foreground='blue', font=('Courier', 10, 'bold'))
    text_widget.tag_configure('read', foreground='black', font=('Courier', 10))
    text_widget.tag_configure('separator', foreground='lightgray')

def mark_all_as_read(unread_text, read_text, recent_text, process_emails_func):
    """Mark all unread notifications as read and refresh the display."""
    notifications = load_notifications()
    for n in notifications:
        if n['status'] == 'unread':
            n['status'] = 'read'
    with open('notifications.json', 'w') as f:
        json.dump(notifications, f, indent=4)
    refresh_all(unread_text, read_text, recent_text, process_emails_func)

def refresh_all(unread_text, read_text, recent_text, process_emails_func):
    """Refresh all tabs with the latest notifications after processing emails."""
    threading.Thread(target=process_emails_func, daemon=True).start()
    time.sleep(1)  # Wait briefly for processing to finish
    notifications = load_notifications()
    display_notifications(unread_text, get_unread_notifications(notifications))
    display_notifications(read_text, get_read_notifications(notifications))
    display_notifications(recent_text, get_recent_notifications(notifications))

def start_viewer(process_emails_func):
    """Start the GUI with a tabbed interface, accepting process_emails function."""
    root = tk.Tk()
    root.title("JobQuickNotify")
    root.geometry("800x600")

    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True)

    unread_frame = ttk.Frame(notebook)
    read_frame = ttk.Frame(notebook)
    recent_frame = ttk.Frame(notebook)

    notebook.add(unread_frame, text='Unread')
    notebook.add(read_frame, text='Read')
    notebook.add(recent_frame, text='Recent')

    unread_text = scrolledtext.ScrolledText(unread_frame, wrap=tk.WORD, font=('Courier', 10))
    unread_text.pack(fill='both', expand=True)
    read_text = scrolledtext.ScrolledText(read_frame, wrap=tk.WORD, font=('Courier', 10))
    read_text.pack(fill='both', expand=True)
    recent_text = scrolledtext.ScrolledText(recent_frame, wrap=tk.WORD, font=('Courier', 10))
    recent_text.pack(fill='both', expand=True)

    for text_widget in [unread_text, read_text, recent_text]:
        configure_tags(text_widget)

    mark_read_button = tk.Button(unread_frame, text="Mark All as Read", 
                                 command=lambda: mark_all_as_read(unread_text, read_text, recent_text, process_emails_func))
    mark_read_button.pack(pady=5)

    refresh_button = tk.Button(root, text="Refresh", 
                               command=lambda: refresh_all(unread_text, read_text, recent_text, process_emails_func))
    refresh_button.pack(pady=5)

    refresh_all(unread_text, read_text, recent_text, process_emails_func)
    root.mainloop()

if __name__ == "__main__":
    def dummy_process_emails():
        print("Dummy email processing")
    start_viewer(dummy_process_emails)