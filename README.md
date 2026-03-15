# NexviaTech — LinkedIn Founder Scraper v2.0

## Project Structure

```
nexvia_scraper/
│
├── main.py              ← Run this
├── config.py            ← ALL settings live here — edit only this
├── requirements.txt
│
├── core/
│   ├── browser.py       ← Chrome + stealth setup
│   ├── login.py         ← Login + verification handling
│   ├── search.py        ← Safe search + pagination
│   └── scraper.py       ← Profile field extraction
│
├── utils/
│   ├── human.py         ← All human-like timing + mouse + scroll
│   ├── date_parser.py   ← Role date parsing + 3-month filter
│   ├── scorer.py        ← Lead scoring 0–100
│   ├── checkpoint.py    ← Resume on crash
│   ├── seen_urls.py     ← All-time deduplication
│   └── logger.py        ← Coloured logs + live dashboard
│
└── data/
    └── csv_writer.py    ← CSV output
```

---

## Setup

```bash
pip install -r requirements.txt
```

---

## Configure

Open **config.py** and set:

```python
LINKEDIN_EMAIL    = "your_email@gmail.com"
LINKEDIN_PASSWORD = "your_password"
LOCATION_FILTER   = "Miami, Florida"   # or None
RECENCY_DAYS      = 90                 # 3 months
DAILY_CAP         = 80
```

---

## Run

```bash
python main.py
```

---

## Output Files

| File              | What it is                                    |
|-------------------|-----------------------------------------------|
| `leads.csv`       | All scraped leads with scores                 |
| `checkpoint.json` | Progress tracker — enables resume on crash    |
| `seen_urls.txt`   | All-time URL log — never scrapes same profile |
| `scraper.log`     | Full log file for debugging                   |

---

## Safety Limits (in config.py)

| Setting                   | Default      |
|---------------------------|--------------|
| Max profiles per keyword  | 20           |
| Daily cap                 | 80           |
| Delay between profiles    | 4.0 – 8.0s  |
| Delay between keywords    | 12 – 22s    |
| Typing speed              | 40 – 190ms/char |

> Use a **secondary LinkedIn account** for scraping to protect your main account.

---

## Lead Priority

| Score   | Priority | Action                            |
|---------|----------|-----------------------------------|
| 70–100  | HIGH     | Send to dev team for demo prep    |
| 45–69   | MEDIUM   | DM / email nurture sequence       |
| 0–44    | LOW      | Bulk email only                   |
