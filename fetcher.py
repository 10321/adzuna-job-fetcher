"""
Adzuna Job Fetcher
==================
Fetches job listings from the Adzuna API and saves them to a CSV file.

Unlike a scraper, this uses an official, permitted API — no anti-bot issues,
no Terms-of-Service problems. It returns clean JSON.

For each job it extracts:
    - Job title
    - Company name
    - Location
    - Salary (min / max, when available)
    - Job URL
    - Date posted

Setup:
    1. Sign up (free) at https://developer.adzuna.com/ to get an app_id and app_key.
    2. Set them as environment variables before running:
         export ADZUNA_APP_ID="your_app_id"
         export ADZUNA_APP_KEY="your_app_key"

Usage:
    python fetcher.py --what "data scientist" --where "Berlin" --country de --pages 2
"""

import argparse
import csv
import os
import sys

import requests

BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
OUTPUT_FILE = "adzuna_jobs.csv"
RESULTS_PER_PAGE = 50  # Adzuna's maximum per page


def get_credentials():
    """Read the Adzuna API credentials from environment variables."""
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        print(
            "Missing credentials. Set them first:\n"
            '  export ADZUNA_APP_ID="your_app_id"\n'
            '  export ADZUNA_APP_KEY="your_app_key"\n'
            "Get free keys at https://developer.adzuna.com/"
        )
        sys.exit(1)
    return app_id, app_key


def fetch_page(country, page, params):
    """Fetch a single page of results from the Adzuna API and return the JSON."""
    url = BASE_URL.format(country=country, page=page)
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()  # raise on bad status codes (401, 404, 500, ...)
    return response.json()


def format_salary(value):
    """Return a salary as a clean integer string, or '' if it's missing."""
    return str(int(value)) if value else ""


def parse_jobs(results):
    """Turn a list of raw API results into clean job dictionaries."""
    jobs = []
    for item in results:
        # .get() with defaults safely handles any missing fields
        company = item.get("company", {}).get("display_name", "")
        location = item.get("location", {}).get("display_name", "")
        jobs.append(
            {
                "title": item.get("title", ""),
                "company": company,
                "location": location,
                "salary_min": format_salary(item.get("salary_min")),
                "salary_max": format_salary(item.get("salary_max")),
                "url": item.get("redirect_url", ""),
                "created": item.get("created", ""),
            }
        )
    return jobs


def save_to_csv(jobs, filename):
    """Write the list of job dictionaries to a CSV file."""
    fieldnames = ["title", "company", "location", "salary_min", "salary_max", "url", "created"]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(jobs)


def main():
    parser = argparse.ArgumentParser(description="Fetch jobs from the Adzuna API into a CSV.")
    parser.add_argument("--what", default="python developer", help="Job title / keywords to search for")
    parser.add_argument("--where", default="", help="Location (e.g. Berlin)")
    parser.add_argument("--country", default="de", help="Country code (e.g. de, gb, us)")
    parser.add_argument("--pages", type=int, default=1, help="Number of result pages to fetch")
    args = parser.parse_args()

    app_id, app_key = get_credentials()

    all_jobs = []
    for page in range(1, args.pages + 1):
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": RESULTS_PER_PAGE,
            "what": args.what,
            "where": args.where,
            "content-type": "application/json",
        }
        try:
            data = fetch_page(args.country, page, params)
        except requests.RequestException as error:
            print(f"Failed to fetch page {page}: {error}")
            break

        results = data.get("results", [])
        if not results:
            break  # no more jobs — stop paging

        all_jobs.extend(parse_jobs(results))
        print(f"Fetched page {page} ({len(results)} jobs)")

    if not all_jobs:
        print("No jobs found. Try different --what / --where / --country values.")
        sys.exit(1)

    save_to_csv(all_jobs, OUTPUT_FILE)
    print(f"\nSaved {len(all_jobs)} jobs to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
