# Member Directory Scraper

A Selenium-based web scraper that captures network requests to extract member data from the Waterloo Region Law Association directory.

## Features

- Captures network requests using selenium-wire
- Extracts member names, emails, phone numbers, and practice areas
- Handles pagination automatically
- Saves results to JSON format
- Runs in headless mode

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the scraper:
```bash
python scraper.py
```

## Output

The script will create a `members.json` file containing all scraped member data.

## How It Works

1. Uses selenium-wire to intercept network traffic
2. Loads the member directory page
3. Captures API requests to `/Sys/MemberDirectory/LoadMembers`
4. Parses JSON responses to extract member data
5. Clicks through pagination to get all pages
6. Saves extracted data to JSON file

## Requirements

- Python 3.7+
- Chrome/Chromium browser
- Internet connection
