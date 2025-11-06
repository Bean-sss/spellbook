# Member Directory Scraper

A Python scraper that directly calls the WildApricot API to extract member data from the Waterloo Region Law Association directory.

## Features

- Direct API access (no browser automation needed - fast and reliable!)
- Extracts member names, emails, phone numbers, and practice areas
- Parses WildApricot's JavaScript-like JsonStructure format
- Handles HTML entities (&amp;, etc.)
- Saves results to JSON format
- Clean, well-documented code

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the scraper:
```bash
python scraper_simple.py
```

## Output

The script creates `members.json` with all scraped member data.

**Data Quality:**
- 575 total members
- 100% have names and emails
- 57% have phone numbers
- 76% have practice areas

## How It Works

1. Establishes a session by visiting the directory page
2. Calls the WildApricot LoadMembers API endpoint directly
3. Strips the `while(1);` security prefix from responses
4. Parses the custom JsonStructure format using regex
5. Extracts names, emails, phone numbers, and practice areas
6. Saves all data to a JSON file

## File Descriptions

- `scraper_simple.py` - **RECOMMENDED** - Fast, reliable requests-based scraper
- `scraper_v2.py` - Selenium with Chrome DevTools Protocol (for reference)
- `scraper.py` - Original selenium-wire approach (deprecated due to compatibility issues)

## Requirements

- Python 3.7+
- Internet connection
- No browser needed!
