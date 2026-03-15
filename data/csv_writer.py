# data/csv_writer.py  -  CSV initialisation and lead appending

import csv
import os

import config
from core.scraper import Lead
from utils.logger import log

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
    "Score (0-100)",
    "Score Breakdown",
    "Priority",
    "Keyword Matched",
    "Scraped Date",
]


def init_csv(path: str = config.OUTPUT_CSV):
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow(HEADERS)
        log(f"Output file created: {path}", "OK")


def save_lead(lead: Lead, path: str = config.OUTPUT_CSV):
    with open(path, "a", newline="", encoding="utf-8") as file:
        csv.writer(file).writerow(
            [
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
            ]
        )
