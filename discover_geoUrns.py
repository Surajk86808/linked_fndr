# discover_geoUrns.py  -  One-time LinkedIn city geoUrn discovery tool
#
# HOW TO USE:
# 1. Run the main scraper once so linkedin_cookies.json is created
# 2. Run: python discover_geoUrns.py
# 3. Wait for it to finish — takes about 3-5 minutes
# 4. geoUrns.json is created in the project root
# 5. Run python main.py — it will now use city-level geoUrns
#    automatically for far more results per search

import json
import os
import random
import re
import sys
import time

import requests

# ── Cookie file path ──────────────────────────────────────────────────────────
COOKIES_FILE = "linkedin_cookies.json"
OUTPUT_FILE  = "geoUrns.json"

# ── Cities to discover ────────────────────────────────────────────────────────
CITIES_TO_DISCOVER = {
    "India": [
        "Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Pune",
        "Chennai", "Kolkata", "Ahmedabad", "Jaipur", "Noida",
        "Gurugram", "Kochi", "Chandigarh", "Indore", "Surat",
        "Nagpur", "Bhopal", "Lucknow", "Patna", "Coimbatore",
    ],
    "United States": [
        "San Francisco", "New York", "Los Angeles", "Seattle",
        "Austin", "Boston", "Chicago", "Miami", "Denver",
        "Atlanta", "Dallas", "Washington DC", "San Jose",
        "Palo Alto", "Mountain View",
    ],
    "United Kingdom": [
        "London", "Manchester", "Birmingham", "Edinburgh",
        "Bristol", "Leeds", "Cambridge", "Oxford",
    ],
    "Germany": [
        "Berlin", "Munich", "Hamburg", "Frankfurt",
        "Cologne", "Stuttgart", "Dusseldorf",
    ],
    "Singapore": ["Singapore"],
    "UAE": ["Dubai", "Abu Dhabi", "Sharjah"],
    "Australia": ["Sydney", "Melbourne", "Brisbane", "Perth"],
    "Canada": ["Toronto", "Vancouver", "Montreal", "Calgary"],
    "Japan": ["Tokyo", "Osaka", "Yokohama", "Kyoto"],
    "Brazil": ["Sao Paulo", "Rio de Janeiro", "Brasilia", "Belo Horizonte"],
}

API_URL = "https://www.linkedin.com/voyager/api/typeahead/hitsV2"

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_cookie_jar(path: str) -> dict:
    """Load cookies from JSON file into a flat name→value dict."""
    with open(path, encoding="utf-8") as f:
        cookies = json.load(f)
    return {c["name"]: c["value"] for c in cookies}


def get_csrf_token(cookie_dict: dict) -> str:
    """Extract CSRF token from JSESSIONID cookie value (strip surrounding quotes)."""
    raw = cookie_dict.get("JSESSIONID", "")
    return raw.strip('"').strip("'")


def build_session(cookie_dict: dict, csrf_token: str) -> requests.Session:
    """Build a requests session with LinkedIn auth headers and cookies."""
    session = requests.Session()
    session.cookies.update(cookie_dict)
    session.headers.update({
        "accept":                      "application/vnd.linkedin.normalized+json+2.1",
        "accept-language":             "en-US,en;q=0.9",
        "x-li-lang":                   "en_US",
        "x-restli-protocol-version":   "2.0.0",
        "x-li-page-instance":          "urn:li:page:d_flagship3_search_srp_people",
        "csrf-token":                  csrf_token,
        "user-agent":                  (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "referer": "https://www.linkedin.com/search/results/people/",
    })
    return session


def extract_geo_urn(urn_str: str) -> str:
    """Pull the numeric ID from 'urn:li:geo:105214831' → '105214831'."""
    if not urn_str:
        return ""
    m = re.search(r":(\d+)$", urn_str)
    return m.group(1) if m else urn_str


def parse_elements(data: dict) -> list:
    """
    Parse the LinkedIn typeahead response and return a list of
    {"name": ..., "geoUrn": ...} dicts.
    Handles multiple known response shapes.
    """
    results = []
    elements = data.get("elements", [])

    for el in elements:
        name = ""
        urn  = ""

        # Primary path
        hit_info = el.get("hitInfo", {})
        for key, val in hit_info.items():
            if isinstance(val, dict):
                name = val.get("displayName", "")
                urn  = val.get("objectUrn", "")
                break

        # Fallback paths
        if not name:
            name = el.get("displayName", "")
        if not urn:
            urn = el.get("objectUrn", el.get("urn", ""))

        geo_id = extract_geo_urn(urn)
        if name and geo_id:
            results.append({"name": name, "geoUrn": geo_id})

    return results


def query_city(session: requests.Session, city: str) -> list:
    """Call the typeahead API for a city and return parsed results."""
    params = {
        "keywords": city,
        "origin":   "OTHER",
        "q":        "type",
        "type":     "GEO",
        "useCase":  "PEOPLE_SEARCH",
    }
    resp = session.get(API_URL, params=params, timeout=15)

    if resp.status_code in (401, 403):
        print(
            "\nSession expired or unauthorised — "
            "run the main scraper again to refresh cookies\n"
        )
        sys.exit(1)

    resp.raise_for_status()
    return parse_elements(resp.json())


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Guard: cookies must exist
    if not os.path.exists(COOKIES_FILE):
        print(
            f"\nError: '{COOKIES_FILE}' not found.\n"
            "Run the main scraper first to generate linkedin_cookies.json\n"
        )
        sys.exit(1)

    print("\nLoading session cookies...")
    cookie_dict = load_cookie_jar(COOKIES_FILE)
    csrf        = get_csrf_token(cookie_dict)

    if not csrf:
        print("Warning: JSESSIONID not found in cookies — requests may fail auth.\n")

    session = build_session(cookie_dict, csrf)

    # ── Discovery loop ────────────────────────────────────────────────────────
    results        = {}
    total_urns     = 0
    total_cities   = 0
    failed_cities  = []

    for country, cities in CITIES_TO_DISCOVER.items():
        results[country] = {}

        for city in cities:
            try:
                locations = query_city(session, city)
                results[country][city] = locations
                count = len(locations)
                total_urns   += count
                total_cities += 1

                status = f"{count} location{'s' if count != 1 else ''} found"
                if count == 0:
                    status = "⚠ 0 results — check spelling or try again"
                print(f"  [{country}] {city:<22} → {status}")

            except Exception as exc:
                print(f"  [{country}] {city:<22} → ERROR: {exc}")
                results[country][city] = []
                failed_cities.append(f"{country} / {city}")

            # Polite delay between calls
            time.sleep(random.uniform(1.5, 3.0))

    # ── Save JSON ─────────────────────────────────────────────────────────────
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # ── Summary ───────────────────────────────────────────────────────────────
    sep = "━" * 44
    print(f"\n{sep}")
    print("DISCOVERY COMPLETE")
    print(f"Total countries : {len(CITIES_TO_DISCOVER)}")
    print(f"Total cities    : {total_cities}")
    print(f"Total geoUrns   : {total_urns}")
    print(f"Saved to        : {OUTPUT_FILE}")
    if failed_cities:
        print(f"Failed cities   : {len(failed_cities)}")
        for fc in failed_cities:
            print(f"  - {fc}")
    print(f"{sep}\n")

    # ── Flat copy-paste block for config.py ───────────────────────────────────
    print("# Ready to paste into config.py:")
    print("GEO_LOCATIONS = {")
    for country, cities in results.items():
        print(f'    "{country}": {{')
        for city, locs in cities.items():
            print(f'        "{city}": {{')
            for loc in locs:
                print(f'            "{loc["name"]}": "{loc["geoUrn"]}",')
            print("        },")
        print("    },")
    print("}")


if __name__ == "__main__":
    main()
