# data/csv_writer.py  —  CSV initialisation and lead appending

import csv
import os
from scraper import Lead
from config import OUTPUT_CSV
from logger import log

HEADERS = [
    "Name",
    "Current Title",
    "Company",
    "Location",
    "LinkedIn URL",
    "Website",
    "Has Website",
    "Connections",
    "Headline",
    "Role Start Date",
    "Days Since Role Start",
    "Role Recency",
    "About (Preview)",
    "Skills",
    "Education",
    "Score (0–100)",
    "Score Breakdown",
    "Priority",
    "Keyword Matched",
    "Scraped Date",
]


def init_csv(path: str = OUTPUT_CSV):
    """Create the CSV file with headers if it doesn't exist yet."""
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS)
        log(f"Output file created: {path}", "OK")


def save_lead(lead: Lead, path: str = OUTPUT_CSV):
    """Append a single Lead row to the CSV."""
    with open(path, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            lead.name,
            lead.current_title,
            lead.company,
            lead.location,
            lead.linkedin_url,
            lead.website,
            lead.has_website,
            lead.connections,
            lead.headline,
            lead.role_start_date,
            lead.role_start_days,
            lead.role_recency_label,
            lead.about,
            lead.skills,
            lead.education,
            lead.score,
            lead.score_breakdown,
            lead.priority,
            lead.keyword_matched,
            lead.scraped_date,
        ])
