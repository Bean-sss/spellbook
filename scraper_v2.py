#!/usr/bin/env python3
"""
Selenium-based web scraper using Chrome DevTools Protocol for network capture.
More stable than selenium-wire approach.
"""

import json
import time
from typing import List, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class MemberDirectoryScraper:
    """Scrapes member directory data by capturing network requests using DevTools."""

    def __init__(self, url: str):
        """Initialize the scraper with target URL."""
        self.url = url
        self.driver = None
        self.all_members = []
        self.network_log = []

    def setup_driver(self):
        """Set up Chrome driver with performance logging."""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--window-size=1920,1080')
        options.binary_location = '/opt/chrome/chrome'

        # Enable performance logging to capture network traffic
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

        service = Service('/usr/local/bin/chromedriver')
        self.driver = webdriver.Chrome(
            service=service,
            options=options
        )
        print("✓ Chrome driver initialized")

    def load_page(self):
        """Load the target page and wait for it to be ready."""
        print(f"Loading page: {self.url}")
        self.driver.get(self.url)

        # Wait for the directory to load
        time.sleep(5)
        print("✓ Page loaded")

    def capture_network_requests(self) -> List[Dict[str, Any]]:
        """Capture and parse network requests from performance logs."""
        members = []

        # Get performance logs
        logs = self.driver.get_log('performance')

        for entry in logs:
            try:
                log = json.loads(entry['message'])['message']

                # Look for network response received events
                if log.get('method') == 'Network.responseReceived':
                    response = log['params']['response']
                    url = response['url']

                    # Check if this is the member directory API call
                    if 'LoadMembers' in url:
                        print(f"✓ Found API request: {url}")
                        request_id = log['params']['requestId']

                        # Try to get the response body
                        try:
                            response_body = self.driver.execute_cdp_cmd(
                                'Network.getResponseBody',
                                {'requestId': request_id}
                            )

                            if 'body' in response_body:
                                data = json.loads(response_body['body'])

                                # Print structure for debugging
                                print(f"Response structure keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")

                                # Extract members - try different common keys
                                if isinstance(data, dict):
                                    for key in ['Members', 'members', 'Results', 'results',
                                               'Data', 'data', 'Items', 'items', 'Contacts', 'contacts']:
                                        if key in data and isinstance(data[key], list):
                                            members.extend(data[key])
                                            print(f"✓ Found {len(data[key])} members in '{key}' field")
                                            break
                                    else:
                                        # Data itself might be a list
                                        if isinstance(data, list):
                                            members = data
                                elif isinstance(data, list):
                                    members = data
                                    print(f"✓ Found {len(members)} members (data is a list)")

                        except Exception as e:
                            # Response body might not be available
                            pass

            except Exception as e:
                continue

        return members

    def extract_member_info(self, members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract relevant fields from member data."""
        extracted = []

        for member in members:
            # Extract fields - adjust based on actual field names
            info = {}

            # Print first member structure for debugging
            if not extracted:
                print(f"\nFirst member structure: {json.dumps(member, indent=2)[:500]}...")

            # Common field names to try for each data type
            name_fields = ['Name', 'name', 'FullName', 'fullName', 'DisplayName',
                          'displayName', 'FirstName', 'firstName', 'LastName', 'lastName']
            email_fields = ['Email', 'email', 'EmailAddress', 'emailAddress', 'E-mail', 'e-mail']
            phone_fields = ['Phone', 'phone', 'PhoneNumber', 'phoneNumber', 'Tel', 'tel',
                           'WorkPhone', 'workPhone', 'CellPhone', 'cellPhone']
            practice_fields = ['PracticeAreas', 'practiceAreas', 'PracticeArea', 'practiceArea',
                              'Areas', 'areas', 'Specialties', 'specialties']

            # Try to build full name from first/last
            first_name = None
            last_name = None
            for field in ['FirstName', 'firstName', 'First', 'first']:
                if field in member:
                    first_name = member[field]
                    break
            for field in ['LastName', 'lastName', 'Last', 'last']:
                if field in member:
                    last_name = member[field]
                    break

            if first_name and last_name:
                info['name'] = f"{first_name} {last_name}"
            else:
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
                "//a[@aria-label='Next']",
                "//a[contains(@class, 'pagination')]//span[text()='>']/..",
                "//button[contains(@aria-label, 'next')]"
            ]

            for selector in next_selectors:
                try:
                    next_button = self.driver.find_element(By.XPATH, selector)
                    if next_button.is_displayed() and next_button.is_enabled():
                        # Check if button is not disabled
                        classes = next_button.get_attribute('class') or ''
                        if 'disabled' not in classes.lower():
                            print(f"✓ Found next button, clicking...")
                            next_button.click()
                            time.sleep(5)  # Wait for new data to load
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

                    # Remove duplicates based on raw data
                    new_members = []
                    for member in extracted:
                        is_duplicate = False
                        for existing in self.all_members:
                            if existing.get('raw_data') == member.get('raw_data'):
                                is_duplicate = True
                                break
                        if not is_duplicate:
                            new_members.append(member)

                    self.all_members.extend(new_members)
                    print(f"✓ Extracted {len(new_members)} new members from page {page_num}")
                    print(f"✓ Total unique members so far: {len(self.all_members)}")
                else:
                    print(f"✗ No members found on page {page_num}")

                # Try to go to next page
                if not self.click_next_page():
                    print("\n✓ No more pages to scrape")
                    break

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

    print("Starting Member Directory Scraper v2 (DevTools Protocol)")
    print("="*50)

    scraper = MemberDirectoryScraper(url)
    scraper.scrape_all_pages()
    scraper.save_results('members.json')
    scraper.print_summary()

    print("\n✓ Scraping complete!")


if __name__ == "__main__":
    main()
