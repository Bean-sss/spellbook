#!/usr/bin/env python3
"""
Simple requests-based scraper that directly calls the member directory API.
No browser automation needed - much more reliable and faster.
"""

import json
import requests
from typing import List, Dict, Any
import time


class MemberDirectoryScraper:
    """Scrapes member directory data by directly calling the API."""

    def __init__(self, base_url: str):
        """Initialize the scraper with base URL."""
        self.base_url = base_url
        self.api_url = "https://waterloolaw.wildapricot.org/Sys/MemberDirectory/LoadMembers"
        self.all_members = []
        self.session = requests.Session()

        # Set up headers to mimic a browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': base_url,
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://waterloolaw.wildapricot.org'
        })

    def fetch_members_page(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """Fetch a page of members from the API."""

        # FormId extracted from the page source
        form_id = '5324963'

        # Common parameters for WildApricot member directories
        params = {
            'formId': form_id,
            'pageIndex': page - 1,  # Usually 0-indexed
            'pageSize': page_size,
            'orderBy': 'Name',
            'orderByAscending': 'true'
        }

        # Try with different parameter formats
        param_combinations = [
            params,
            {
                'formId': form_id,
                'page': page,
                'pageSize': page_size,
                'sort': 'Name'
            },
            {
                'formId': form_id,
                'pageNumber': page,
                'resultsPerPage': page_size
            },
            # Try without pagination first to see what we get
            {'formId': form_id}
        ]

        for params_attempt in param_combinations:
            try:
                print(f"Trying API call with params: {params_attempt}")
                response = self.session.post(self.api_url, json=params_attempt, timeout=30)

                if response.status_code == 200 and response.text:
                    # Strip the "while(1);" prefix that WildApricot uses for security
                    response_text = response.text
                    if response_text.startswith('while(1);'):
                        response_text = response_text[9:].strip()

                    data = json.loads(response_text)
                    print(f"✓ API call successful! Response keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
                    print(f"Total count: {data.get('TotalCount', 'unknown')}")
                    return data
                else:
                    print(f"Response not successful or empty")

            except Exception as e:
                print(f"Error with params {params_attempt}: {e}")
                continue

        # Try GET request as well
        try:
            print("Trying GET request...")
            response = self.session.get(self.api_url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ GET request successful! Response keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
                return data
        except Exception as e:
            print(f"GET request error: {e}")

        return {}

    def extract_members_from_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract member list from API response."""
        members = []

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            # WildApricot stores data in a JsonStructure field that's a JS-like string
            if 'JsonStructure' in data:
                import re
                js_structure = data['JsonStructure']

                # Extract all member objects using regex
                # Pattern: {c1:[...], c2:[...], c3:[...], c4:[...]}
                # c1 = name, c2 = phone, c3 = email, c4 = other
                member_pattern = r'\{c1:\[(.*?)\],c2:\[(.*?)\],c3:\[(.*?)\],c4:\[(.*?)\]\}'
                matches = re.findall(member_pattern, js_structure)

                print(f"✓ Found {len(matches)} member entries in JsonStructure")

                for match in matches:
                    c1, c2, c3, c4 = match
                    member = {}

                    # Extract name from c1 (contains sft:11, v:'Name')
                    name_match = re.search(r"sft:11,\s*v:'([^']*)'", c1)
                    if name_match:
                        member['Name'] = name_match.group(1).replace("\\'", "'")

                    # Extract phone from c2 (contains fft:23, v:'Phone')
                    phone_match = re.search(r"fft:23,\s*v:'([^']*)'", c2)
                    if phone_match:
                        phone = phone_match.group(1).replace("\\'", "'")
                        if phone:
                            member['Phone'] = phone

                    # Extract email from c3 (contains fft:5, v:'Email')
                    email_match = re.search(r"fft:5,\s*v:'([^']*)'", c3)
                    if email_match:
                        email = email_match.group(1).replace("\\'", "'")
                        if email:
                            member['Email'] = email

                    # Extract practice areas from c4 (contains multiple fft:11 entries)
                    practice_areas = []
                    practice_matches = re.findall(r"fft:11,\s*v:'([^']*)'", c4)
                    for practice in practice_matches:
                        practice_clean = practice.replace("\\'", "'").replace("&amp;", "&").strip()
                        if practice_clean:  # Only add non-empty values
                            practice_areas.append(practice_clean)

                    if practice_areas:
                        member['PracticeAreas'] = practice_areas

                    members.append(member)

                return members

            # Try common keys where member data might be stored
            for key in ['Members', 'members', 'Results', 'results', 'Data', 'data',
                       'Items', 'items', 'Contacts', 'contacts', 'Records', 'records']:
                if key in data and isinstance(data[key], list):
                    print(f"✓ Found members in '{key}' field: {len(data[key])} members")
                    return data[key]

        return members

    def extract_member_info(self, members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract relevant fields from member data."""
        extracted = []

        for i, member in enumerate(members):
            # Print first member structure for debugging
            if i == 0:
                print(f"\nFirst member structure:")
                print(json.dumps(member, indent=2)[:1000])
                print("...")

            info = {}

            # Extract name
            if 'FirstName' in member and 'LastName' in member:
                info['name'] = f"{member.get('FirstName', '')} {member.get('LastName', '')}".strip()
            else:
                for field in ['Name', 'name', 'FullName', 'fullName', 'DisplayName', 'displayName']:
                    if field in member:
                        info['name'] = member[field]
                        break

            # Extract email
            for field in ['Email', 'email', 'EmailAddress', 'emailAddress', 'E-mail', 'e-mail']:
                if field in member and member[field]:
                    info['email'] = member[field]
                    break

            # Extract phone
            for field in ['Phone', 'phone', 'PhoneNumber', 'phoneNumber', 'Tel', 'tel',
                         'WorkPhone', 'workPhone', 'CellPhone', 'cellPhone']:
                if field in member and member[field]:
                    info['phone'] = member[field]
                    break

            # Extract practice areas
            for field in ['PracticeAreas', 'practiceAreas', 'PracticeArea', 'practiceArea',
                         'Areas', 'areas', 'Specialties', 'specialties', 'FieldsOfPractice']:
                if field in member and member[field]:
                    info['practice_areas'] = member[field]
                    break

            # Keep all original data for reference
            info['raw_data'] = member

            extracted.append(info)

        return extracted

    def scrape_all_pages(self, max_pages: int = 100):
        """Scrape data from all pages."""
        # First, visit the page to establish a session
        print("Establishing session by visiting the page...")
        try:
            response = self.session.get(self.base_url, timeout=30)
            print(f"✓ Page visited, status: {response.status_code}")
        except Exception as e:
            print(f"Warning: Could not visit page: {e}")

        page_num = 1
        total_count = None

        while page_num <= max_pages:
            print(f"\n--- Page {page_num} ---")

            # Fetch data from API
            data = self.fetch_members_page(page=page_num)

            if not data:
                print("✗ No data received from API")
                break

            # Track total count
            if 'TotalCount' in data:
                total_count = data['TotalCount']

            # Extract members
            members = self.extract_members_from_response(data)

            if not members:
                print("✗ No members found in response")
                # Check if we've reached the end
                if page_num > 1:
                    print("✓ Reached end of results")
                    break

            # Extract relevant info
            extracted = self.extract_member_info(members)

            # Remove duplicates
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

            # Check if we should continue
            if len(members) == 0:
                print("✓ No more members to fetch")
                break

            # If we got no new unique members, we're done
            if len(new_members) == 0:
                print("✓ No new unique members found - all data collected!")
                break

            # If the API returned all members (TotalCount), we're done
            if total_count and len(self.all_members) >= total_count:
                print(f"✓ Collected all {total_count} members!")
                break

            page_num += 1
            time.sleep(1)  # Be nice to the server

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
            print("\nSample member data (first 3):")
            for i, member in enumerate(self.all_members[:3], 1):
                print(f"\nMember {i}:")
                print(f"  Name: {member.get('name', 'N/A')}")
                print(f"  Email: {member.get('email', 'N/A')}")
                print(f"  Phone: {member.get('phone', 'N/A')}")
                print(f"  Practice Areas: {member.get('practice_areas', 'N/A')}")


def main():
    """Main entry point."""
    url = "https://waterloolaw.wildapricot.org/page-18139"

    print("Starting Member Directory Scraper (API Direct)")
    print("="*50)

    scraper = MemberDirectoryScraper(url)
    scraper.scrape_all_pages()
    scraper.save_results('members.json')
    scraper.print_summary()

    print("\n✓ Scraping complete!")


if __name__ == "__main__":
    main()
