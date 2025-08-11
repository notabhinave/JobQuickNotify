import spacy
from transformers import pipeline
import re
import base64
from bs4 import BeautifulSoup
from plyer import notification
from dateutil import parser
import json
from datetime import datetime

nlp = spacy.load("en_core_web_sm")
try:
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
except RuntimeError as e:
    print(f"Error loading summarizer: {e}. Falling back to basic summarization.")
    summarizer = None

def get_email_body(payload):
    """Extract the email body from the payload."""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            elif part['mimeType'] == 'text/html' and 'data' in part['body']:
                html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                soup = BeautifulSoup(html, 'html.parser')
                return soup.get_text()
        return ''
    else:
        if 'body' in payload and 'data' in payload['body']:
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        return ''

def is_job_related(email_text):
    """Check if the email is job-related with simplified criteria."""
    job_keywords = ['job', 'career', 'position', 'hiring', 'apply', 'interview', 'opportunity']
    email_lower = email_text.lower()
    result = any(keyword in email_lower for keyword in job_keywords)
    print(f"Job-related check: {result} (Text: {email_lower[:100]}...)")
    return result

def extract_key_info(email_text):
    """Extract key job-related information with robust regex patterns."""
    patterns = {
        "job_title": r"(?i)(?:job\s*title|position|role|interview\s*for|offer\s*for)\s*[:-]?\s*([A-Za-z\s\/]+?)(?:\s*(?:at|with|for)\s*[A-Za-z\s]+)?(?:\n|$)",
        "company": r"(?i)(?:company|at|from|with)\s*[:-]?\s*([A-Za-z\s]+(?:Enterprises|Industries|Creative|Solutions|Inc|LLC)?)|(?:Greetings|Regards)\s*from\s*([A-Za-z\s]+(?:Enterprises|Industries|Creative|Solutions|Inc|LLC)?)",
        "location": r"(?i)location\s*[:-]?\s*(.*?)(?:\n|$)",
        "salary": r"(?i)salary\s*(?:range)?\s*[:-]?\s*((?:\$[\d,]+\s*(?:to\s*\$[\d,]+)?(?:\s*per\s*year)?(?:,|\s|-|\n)*(?:plus|with|and)?\s*.*?)(?=\n\s*-|\n\s*$))",
        "job_type": r"(?i)(?:employment\s*type|type)\s*[:-]?\s*(.*?)(?:\n|$)",
        "deadline": r"(?i)(?:application\s*deadline|deadline|by|date)\s*[:-]?\s*(.*?)(?:\s*to\s*be\s*considered)?(?:\n|$)",
        "apply_link": r"(?i)(?:how\s*to\s*apply|apply\s*(?:here)?)\s*[:-]?\s*visit\s*(https?://[^\s]+)"
    }
    
    key_info = {}
    
    # Extract from subject
    subject_match = re.search(r"Subject: (.*)\n", email_text, re.IGNORECASE)
    if subject_match:
        subject = subject_match.group(1)
        title_match = re.search(r"(?i)(?:opportunity|interview|offer|role|position)\s*[:-]?\s*([A-Za-z\s\/]+?)(?:\s*at|\s*$)", subject)
        company_match = re.search(r"at\s+([A-Za-z\s]+(?:Enterprises|Industries|Creative|Solutions|Inc|LLC)?)$", subject)
        if title_match:
            key_info["job_title"] = title_match.group(1).strip()
        if company_match:
            key_info["company"] = company_match.group(1).strip()
    
    # Extract from body, overriding subject if more specific
    for key, pattern in patterns.items():
        matches = re.findall(pattern, email_text, re.IGNORECASE | re.DOTALL)
        if matches:
            value = None
            if isinstance(matches[0], tuple):
                value = next((m for m in matches[0] if m.strip()), None)
            else:
                value = matches[0]
            if value:
                key_info[key] = value.strip().replace('\n', ' ')  # Normalize multi-line values
    
    # Fallback for title
    if "job_title" not in key_info or "at" in key_info.get("job_title", "").lower():
        title_match = re.search(r"(?i)(?:for\s*the\s*role\s*of|seeking|looking\s*for|to\s*hire)\s*([A-Za-z\s\/]+?)(?:\s*at|\s*with|\s*\.)", email_text)
        if title_match:
            key_info["job_title"] = title_match.group(1).strip()
    
    # Fallback to NER for company
    doc = nlp(email_text)
    if "company" not in key_info:
        orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG" and ent.text not in ["Microsoft", "Terraform", "Kubernetes", "AWS", "Azure"]]
        if orgs:
            key_info["company"] = orgs[0]
    
    # Parse and format deadline
    if "deadline" in key_info:
        try:
            parsed_date = parser.parse(key_info["deadline"], fuzzy=True, dayfirst=True)
            key_info["deadline"] = parsed_date.strftime('%Y-%m-%d')
        except Exception:
            key_info["deadline"] = "N/A"
    
    return key_info

def summarize_email(email_text):
    """Summarize the email with a structured format, excluding salutations and redundant data."""
    if not email_text.strip():
        return "No content to summarize.", None
    
    # Remove salutations and greetings
    cleaned_text = re.sub(
        r"(?i)^(?:Dear|Hello|Hi|Greetings)\s+[A-Za-z\s]+?,?\s*\n+|(?:Greetings|Regards)\s*from\s*[A-Za-z\s]+(?:Enterprises|Industries|Creative|Solutions|Inc|LLC)?\s*\n*",
        "",
        email_text,
        flags=re.MULTILINE
    )
    
    key_info = extract_key_info(cleaned_text)
    
    # Remove structured fields from summary input for "Details"
    summary_input = re.sub(
        r"(?i)(?:job\s*title|position|role|company|location|salary|employment\s*type|application\s*deadline|how\s*to\s*apply|apply\s*here|interview\s*for|offer\s*for|date)\s*[:-].*?(?:\n\s*-|\n\s*$)",
        "",
        cleaned_text,
        flags=re.DOTALL
    )
    summary_input = summary_input.strip()
    
    # Generate summary
    if summarizer:
        summary = summarizer(summary_input, max_length=150, min_length=50, do_sample=False)[0]['summary_text']
    else:
        summary = summary_input
        if len(summary) > 150:
            summary = summary[:150] + '...'
    
    # Construct structured summary
    structured_summary = "Job Opportunity Summary:\n"
    fields = [
        ("Title", "job_title"),
        ("Company", "company"),
        ("Location", "location"),
        ("Salary", "salary"),
        ("Type", "job_type"),
        ("Deadline", "deadline"),
        ("Apply Here", "apply_link")
    ]
    for label, key in fields:
        if key in key_info and key_info[key]:
            structured_summary += f"{label}: {key_info[key]}\n"
    
    structured_summary += f"\nDetails: {summary}"
    key_date = key_info.get("deadline")
    return structured_summary, key_date

def send_notification(title, full_message, email_id=None):
    """Send a desktop notification and save the full message with email ID."""
    MAX_MESSAGE_LENGTH = 256
    if len(full_message) > MAX_MESSAGE_LENGTH:
        truncated = ""
        for line in full_message.split('\n'):
            if any(x in line for x in ["Title:", "Company:", "Deadline:", "Apply Here:"]):
                truncated += line + "\n"
            if len(truncated) >= MAX_MESSAGE_LENGTH - 20:
                break
        message = truncated.strip() + "..." if truncated else full_message[:MAX_MESSAGE_LENGTH - 3] + "..."
    else:
        message = full_message
    
    notification.notify(
        title=title,
        message=message,
        app_name='JobQuickNotify',
        timeout=10
    )
    
    try:
        with open('notifications.json', 'r') as f:
            notifications = json.load(f)
    except FileNotFoundError:
        notifications = []
    
    timestamp = datetime.now().isoformat()
    notification_entry = {
        "title": title,
        "message": full_message,
        "timestamp": timestamp,
        "status": "unread",
        "email_id": email_id
    }
    notifications.append(notification_entry)
    
    with open('notifications.json', 'w') as f:
        json.dump(notifications, f, indent=4)
    print(f"Saved notification for email ID: {email_id}")

def load_notification_schedule():
    """Load the notification schedule from a JSON file."""
    try:
        with open('notification_schedule.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_notification_schedule(schedule):
    """Save the notification schedule to a JSON file."""
    with open('notification_schedule.json', 'w') as f:
        json.dump(schedule, f, indent=4)