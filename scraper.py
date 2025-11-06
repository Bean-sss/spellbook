#!/usr/bin/env python3
"""
Selenium-based web scraper for capturing network requests and extracting member data.
"""

import json
import time
from typing import List, Dict, Any
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


class MemberDirectoryScraper:
    """Scrapes member directory data by capturing network requests."""

    def __init__(self, url: str):
        """Initialize the scraper with target URL."""
        self.url = url
        self.driver = None
        self.all_members = []

    def setup_driver(self):
        """Set up Chrome driver with selenium-wire for network capture."""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run in headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')

        # Set up selenium-wire options
        seleniumwire_options = {
            'disable_encoding': True  # Disable encoding to get readable responses
        }

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(
            service=service,
            options=options,
            seleniumwire_options=seleniumwire_options
        )
        print("✓ Chrome driver initialized")

    def load_page(self):
        """Load the target page and wait for it to be ready."""
        print(f"Loading page: {self.url}")
        self.driver.get(self.url)

        # Wait for the page to load
        time.sleep(3)
        print("✓ Page loaded")

    def capture_network_requests(self) -> List[Dict[str, Any]]:
        """Capture and parse network requests for member data."""
        members = []

        # Look through all requests
        for request in self.driver.requests:
            # Check if this is the member directory API call
            if 'LoadMembers' in request.url and request.response:
                print(f"✓ Found API request: {request.url}")

                try:
                    # Get the response body
                    body = request.response.body.decode('utf-8')
                    data = json.loads(body)

                    # Print the structure for debugging
                    print(f"Response structure: {json.dumps(data, indent=2)[:500]}...")

                    # Extract members - adjust based on actual response structure
                    if isinstance(data, dict):
                        # Try common keys where member data might be stored
                        for key in ['Members', 'members', 'Results', 'results', 'Data', 'data', 'Items', 'items']:
                            if key in data and isinstance(data[key], list):
                                members.extend(data[key])
                                print(f"✓ Found {len(data[key])} members in '{key}' field")
                                break
                        else:
                            # If no known key found, might be the data itself
                            if isinstance(data, list):
                                members = data
                    elif isinstance(data, list):
                        members = data

                except Exception as e:
                    print(f"✗ Error parsing response: {e}")

        return members

    def extract_member_info(self, members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract relevant fields from member data."""
        extracted = []

        for member in members:
            # Extract fields - adjust based on actual field names
            info = {}

            # Common field names to try for each data type
            name_fields = ['Name', 'name', 'FullName', 'fullName', 'DisplayName', 'displayName']
            email_fields = ['Email', 'email', 'EmailAddress', 'emailAddress']
            phone_fields = ['Phone', 'phone', 'PhoneNumber', 'phoneNumber', 'Tel', 'tel']
            practice_fields = ['PracticeAreas', 'practiceAreas', 'PracticeArea', 'practiceArea', 'Areas', 'areas']

            # Extract name
            for field in name_fields:
                if field in member:
                    info['name'] = member[field]
                    break

            # Extract email
            for field in email_fields:
                if field in member:
                    info['email'] = member[field]
                    break

            # Extract phone
            for field in phone_fields:
                if field in member:
                    info['phone'] = member[field]
                    break

            # Extract practice areas
            for field in practice_fields:
                if field in member:
                    info['practice_areas'] = member[field]
                    break

            # Keep all original data for reference
            info['raw_data'] = member

            extracted.append(info)

        return extracted

    def click_next_page(self) -> bool:
        """Click the next page button if it exists."""
        try:
            # Wait a bit for any previous requests to complete
            time.sleep(2)

            # Common selectors for next page buttons
            next_selectors = [
                "//a[contains(text(), 'Next')]",
                "//button[contains(text(), 'Next')]",
                "//a[contains(@class, 'next')]",
                "//button[contains(@class, 'next')]",
                "//li[contains(@class, 'next')]/a",
                "//a[@aria-label='Next']"
            ]

            for selector in next_selectors:
                try:
                    next_button = self.driver.find_element(By.XPATH, selector)
                    if next_button.is_displayed() and next_button.is_enabled():
                        print(f"✓ Found next button, clicking...")
                        next_button.click()
                        time.sleep(3)  # Wait for new data to load
                        return True
                except NoSuchElementException:
                    continue

            print("✗ No next button found or it's disabled")
            return False

        except Exception as e:
            print(f"✗ Error clicking next: {e}")
            return False

    def scrape_all_pages(self):
        """Scrape data from all pages."""
        try:
            self.setup_driver()
            self.load_page()

            page_num = 1
            while True:
                print(f"\n--- Page {page_num} ---")

                # Capture network requests
                members = self.capture_network_requests()

                if members:
                    # Extract relevant info
                    extracted = self.extract_member_info(members)
                    self.all_members.extend(extracted)
                    print(f"✓ Extracted {len(extracted)} members from page {page_num}")
                else:
                    print(f"✗ No members found on page {page_num}")

                # Try to go to next page
                if not self.click_next_page():
                    print("\n✓ No more pages to scrape")
                    break

                # Clear old requests to avoid duplicates
                del self.driver.requests

                page_num += 1

                # Safety limit to prevent infinite loops
                if page_num > 50:
                    print("⚠ Reached safety limit of 50 pages")
                    break

        finally:
            if self.driver:
                self.driver.quit()
                print("\n✓ Driver closed")

    def save_results(self, filename: str = 'members.json'):
        """Save scraped data to JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.all_members, indent=2, fp=f)
        print(f"\n✓ Saved {len(self.all_members)} members to {filename}")

    def print_summary(self):
        """Print a summary of scraped data."""
        print("\n" + "="*50)
        print(f"SCRAPING SUMMARY")
        print("="*50)
        print(f"Total members scraped: {len(self.all_members)}")

        if self.all_members:
            print("\nSample member data:")
            for i, member in enumerate(self.all_members[:3], 1):
                print(f"\nMember {i}:")
                print(f"  Name: {member.get('name', 'N/A')}")
                print(f"  Email: {member.get('email', 'N/A')}")
                print(f"  Phone: {member.get('phone', 'N/A')}")
                print(f"  Practice Areas: {member.get('practice_areas', 'N/A')}")


def main():
    """Main entry point."""
    url = "https://waterloolaw.wildapricot.org/page-18139"

    print("Starting Member Directory Scraper")
    print("="*50)

    scraper = MemberDirectoryScraper(url)
    scraper.scrape_all_pages()
    scraper.save_results('members.json')
    scraper.print_summary()

    print("\n✓ Scraping complete!")


if __name__ == "__main__":
    main()
