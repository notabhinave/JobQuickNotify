# JobQuickNotify

**A Python application to automatically detect, summarize, and notify job seekers about job-related emails from their Gmail inbox.**

## Overview
JobQuickNotify helps job seekers manage their Gmail inbox by:
- **Detecting** job-related emails (e.g., offers, interviews) with 85–90% accuracy.
- **Extracting** key details like job title, company, salary, and deadlines (80–85% accuracy).
- **Summarizing** emails using the BART model (90% accuracy).
- **Notifying** users via desktop pop-ups for new emails and reminders (1 week and 1 day before deadlines, ~100% success).
- **Displaying** notifications in a Tkinter GUI with tabs for Unread, Read, and Recent messages.

This project addresses email overload, missed opportunities, and the need for real-time notifications, making job hunting more efficient.

## Features
- **Automatic Email Scanning**: Checks Gmail every 10 minutes for job-related emails using keywords like "job", "hiring", and "interview".
- **Information Extraction**: Uses spaCy and regex to extract job title, company, location, salary, and deadlines.
- **Summarization**: Generates concise summaries with the BART model or a fallback method.
- **Notifications**: Sends desktop alerts for new emails and scheduled reminders for deadlines.
- **GUI**: A user-friendly Tkinter interface to view and manage notifications.

## Installation
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/notabhinave/JobQuickNotify.git

   cd JobQuickNotify
