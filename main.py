#!/usr/bin/env python3
import csv
import os
import re
import sys
from datetime import datetime
from typing import List, Set
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def parse_date(date_str: str) -> datetime:
    """Parse date string like 'December 03, 2025' to datetime."""
    return datetime.strptime(date_str.strip(), "%B %d, %Y")


def extract_content_links(html: str, base_url: str) -> List[tuple[str, datetime]]:
    """Extract content page links and their dates from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    
    # Find all search-result rows (they have "search-result" in class list)
    for row in soup.find_all("div", class_=lambda x: x and "search-result" in x):
        # Find the link to content page (pattern: /recent-actions/YYYYMMDD)
        link_elem = row.find("a", href=re.compile(r"/recent-actions/\d{8}"))
        if not link_elem:
            continue
        
        href = link_elem.get("href")
        if not href:
            continue
        
        # Find the date in the second div with margin-top-1 class
        date_divs = row.find_all("div", class_=lambda x: x and "margin-top-1" in x)
        if not date_divs:
            continue
        
        # The date is in the text of the div, format: "December 03, 2025 -"
        date_text = date_divs[-1].get_text()
        # Extract date string like "December 03, 2025"
        date_match = re.search(r"([A-Za-z]+ \d{1,2}, \d{4})", date_text)
        if not date_match:
            continue
        
        try:
            date = parse_date(date_match.group(1))
            full_url = urljoin(base_url, href)
            links.append((full_url, date))
        except ValueError:
            continue
    
    return links


def clean_name(name: str) -> str:
    """Remove parentheses and everything after them from a name."""
    if "(" in name:
        name = name.split("(")[0]
    return name.strip()


def extract_content_data(url: str) -> tuple[List[str], List[str], List[str]]:
    """Extract individuals added, entities added, and deletions from a content page.
    
    Returns:
        tuple: (individuals_added, entities_added, deletions)
    """
    individuals_added = []
    entities_added = []
    deletions = []
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return individuals_added, entities_added, deletions
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find the main content div
    field_item = soup.find("div", class_="field__item") or soup.select_one("div.field__item")
    if not field_item:
        return individuals_added, entities_added, deletions
    
    # Find all headers (h3 and h4)
    headers = field_item.find_all(["h3", "h4"])
    if not headers:
        headers = soup.find_all(["h3", "h4"])
    
    for header in headers:
        header_text = header.get_text().lower().strip()
        
        # Check for individuals added (handle both "individual" and "individuals")
        if ("individual" in header_text or "individuals" in header_text) and "added" in header_text:
            next_p = header.find_next("p")
            if next_p:
                # Try to find <a> tags first, if none exist, parse text directly
                a_tags = next_p.find_all("a")
                if a_tags:
                    for a_tag in a_tags:
                        text = a_tag.get_text().strip()
                        if not text:
                            continue
                        parts = [p.strip() for p in text.split(",")]
                        if len(parts) >= 2:
                            name = clean_name(f"{parts[0]}, {parts[1]}")
                            individuals_added.append(name)
                else:
                    # No <a> tags, parse the paragraph text directly
                    # Extract name from the beginning: "LAST, First (additional info)"
                    text = next_p.get_text().strip()
                    if text:
                        # Extract name before first opening parenthesis or semicolon
                        # Format: "LAST, First (info)" or "LAST, First; address"
                        name_match = re.match(r'^([^\(;]+?)(?:\s*\(|;|$)', text)
                        if name_match:
                            name_text = name_match.group(1).strip()
                            # Remove trailing commas and clean up
                            name_text = name_text.rstrip(',').strip()
                            parts = [p.strip() for p in name_text.split(",")]
                            if len(parts) >= 2:
                                name = clean_name(f"{parts[0]}, {parts[1]}")
                                if name:
                                    individuals_added.append(name)
        
        # Check for entities added (handle both "entity" and "entities")
        elif ("entity" in header_text or "entities" in header_text) and "added" in header_text:
            next_p = header.find_next("p")
            if next_p:
                # Try to find <a> tags first, if none exist, parse text directly
                a_tags = next_p.find_all("a")
                if a_tags:
                    for a_tag in a_tags:
                        text = a_tag.get_text().strip()
                        if not text:
                            continue
                        parts = [p.strip() for p in text.split(",")]
                        if len(parts) >= 1:
                            name = clean_name(parts[0])
                            entities_added.append(name)
                else:
                    # No <a> tags, parse the paragraph text directly
                    text = next_p.get_text().strip()
                    if text:
                        # Extract entity name before first opening parenthesis or semicolon
                        name_match = re.match(r'^([^\(;]+?)(?:\s*\(|;|$)', text)
                        if name_match:
                            name_text = name_match.group(1).strip()
                            # Remove trailing commas and clean up
                            name_text = name_text.rstrip(',').strip()
                            parts = [p.strip() for p in name_text.split(",")]
                            if len(parts) >= 1:
                                name = clean_name(parts[0])
                                if name:
                                    entities_added.append(name)
        
        # Check for deletions
        elif "deletions" in header_text or "deletion" in header_text:
            next_p = header.find_next("p")
            if next_p:
                # Try to find <a> tags first, if none exist, parse text directly
                a_tags = next_p.find_all("a")
                if a_tags:
                    for a_tag in a_tags:
                        text = a_tag.get_text().strip()
                        if not text:
                            continue
                        parts = [p.strip() for p in text.split(",")]
                        if len(parts) >= 2:
                            name = clean_name(f"{parts[0]}, {parts[1]}")
                            deletions.append(name)
                else:
                    # No <a> tags, parse the paragraph text directly
                    text = next_p.get_text().strip()
                    if text:
                        # Extract name before first opening parenthesis or semicolon
                        name_match = re.match(r'^([^\(;]+?)(?:\s*\(|;|$)', text)
                        if name_match:
                            name_text = name_match.group(1).strip()
                            # Remove trailing commas and clean up
                            name_text = name_text.rstrip(',').strip()
                            parts = [p.strip() for p in name_text.split(",")]
                            if len(parts) >= 2:
                                name = clean_name(f"{parts[0]}, {parts[1]}")
                                if name:
                                    deletions.append(name)
    
    return individuals_added, entities_added, deletions


def query_ofac_search(name: str) -> List[dict]:
    """Query OFAC sanctions search page for a name and return results.
    
    Returns:
        List of dicts with keys: name, address, type, program, list_type, score, detail_url
    """
    search_url = "https://sanctionssearch.ofac.treas.gov/"
    results = []
    
    with requests.Session() as session:
        try:
            print(f"    GET {search_url}", file=sys.stderr)
            response = session.get(search_url, timeout=30)
            response.raise_for_status()
            print(f"    Got search page (status {response.status_code})", file=sys.stderr)
        except requests.RequestException as e:
            print(f"Error fetching search page: {e}", file=sys.stderr)
            return results
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract ViewState and other hidden form fields
        form_data = {}
        
        # Get all hidden inputs
        for hidden_input in soup.find_all("input", type="hidden"):
            input_name = hidden_input.get("name")
            input_value = hidden_input.get("value", "")
            if input_name:
                form_data[input_name] = input_value

        # Set the name field
        form_data["ctl00$MainContent$txtLastName"] = name
        
        # Set other required fields to defaults
        form_data["ctl00$MainContent$ddlType"] = ""  # All
        form_data["ctl00$MainContent$txtID"] = ""
        form_data["ctl00$MainContent$txtAddress"] = ""
        form_data["ctl00$MainContent$txtCity"] = ""
        form_data["ctl00$MainContent$txtState"] = ""
        form_data["ctl00$MainContent$ddlCountry"] = ""
        form_data["ctl00$MainContent$ddlList"] = ""
        form_data["ctl00$MainContent$Slider1"] = "100"
        form_data["ctl00$MainContent$Slider1_Boundcontrol"] = "100"
        
        # IMPORTANT: Include the search button to trigger the search
        form_data["ctl00$MainContent$btnSearch"] = "Search"
        
        try:
            print(f"    POST {search_url} (searching for: {name})", file=sys.stderr)
            response = session.post(search_url, data=form_data, timeout=30)
            response.raise_for_status()
            print(f"    Got search results (status {response.status_code}, size {len(response.text)} bytes)", file=sys.stderr)
        except requests.RequestException as e:
            print(f"    Error posting search: {e}", file=sys.stderr)
            return results
        
        # Parse results
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Debug: Check if results section exists
        results_label = soup.find("span", id="ctl00_MainContent_lblResults")
        
        # Find the results table
        results_table = soup.find("table", id="gvSearchResults")
        
        if not results_table:
            # Check if results div exists
            results_div = soup.find("div", id="scrollResults")
            if results_div:
                # Check what's inside the div
                results_table = results_div.find("table", id="gvSearchResults")
        
        if not results_table:
            # Try finding any table with gvSearchResults
            all_tables = soup.find_all("table")
            for table in all_tables:
                if table.get("id") == "gvSearchResults":
                    results_table = table
                    break
            
            if not results_table:
                return results
        


        rows = results_table.find_all("tr")
        
        if not rows:
            return results
        
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 6:
                name_cell = cells[0]
                name_link = name_cell.find("a")
                name_text = name_link.get_text().strip() if name_link else name_cell.get_text().strip()
                detail_url = ""
                if name_link and name_link.get("href"):
                    detail_url = urljoin(search_url, name_link.get("href"))
                
                address = cells[1].get_text().strip()
                entity_type = cells[2].get_text().strip()
                program = cells[3].get_text().strip()
                list_type = cells[4].get_text().strip()
                score = cells[5].get_text().strip()
                
                results.append({
                    "name": name_text,
                    "address": address,
                    "type": entity_type,
                    "program": program,
                    "list_type": list_type,
                    "score": score,
                    "detail_url": detail_url
                })
    
    return results


def get_identification_details(detail_url: str) -> List[dict]:
    """Fetch detail page and extract identification information.
    
    Returns:
        List of dicts with keys: type, id_number
    """
    identifications = []
    
    try:
        print(f"    GET {detail_url}", file=sys.stderr)
        response = requests.get(detail_url, timeout=30)
        response.raise_for_status()
        print(f"    Got detail page (status {response.status_code}, size {len(response.text)} bytes)", file=sys.stderr)
    except requests.RequestException as e:
        print(f"Error fetching detail page {detail_url}: {e}", file=sys.stderr)
        return identifications
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find the identification panel
    ident_panel = soup.find("div", id="ctl00_MainContent_pnlIdentification")
    if not ident_panel:
        return identifications
    
    # Find the identification table
    ident_table = ident_panel.find("table", id="ctl00_MainContent_gvIdentification")
    if not ident_table:
        return identifications
    
    # Extract rows - try tbody first, then direct children
    tbody = ident_table.find("tbody")
    if tbody:
        all_rows = tbody.find_all("tr")
    else:
        # No tbody, rows are direct children of table
        all_rows = ident_table.find_all("tr")
    
    # Skip header row (first row)
    rows = all_rows[1:] if len(all_rows) > 1 else []
    
    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 2:
            id_type = cells[0].get_text().strip()
            id_number = cells[1].get_text().strip()
            
            # Skip empty rows
            if not id_type and not id_number:
                continue
            
            identifications.append({
                "type": id_type,
                "id_number": id_number
            })
    
    return identifications


def extract_eth_address(identifications: List[dict]) -> List[str]:
    """Extract Ethereum address from identifications if present.
    
    Returns:
        List of Ethereum addresses
    """
    addresses = []
    for ident in identifications:
        if ident["type"] == "Digital Currency Address - ETH":
            addresses.append(ident["id_number"].strip().lower())
    return addresses


def load_existing_names(csv_path: str = "data.csv") -> Set[str]:
    """Load names from data.csv into a set.
    
    Returns:
        Set of names from the CSV file
    """
    names = set()
    
    if not os.path.exists(csv_path):
        print(f"Warning: {csv_path} not found, starting with empty set", file=sys.stderr)
        return names
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('name', '').strip()
                if name:
                    names.add(name)
        print(f"Loaded {len(names)} names from {csv_path}", file=sys.stderr)
    except Exception as e:
        print(f"Error reading {csv_path}: {e}", file=sys.stderr)
    
    return names


def get_last_processed_date(log_path: str = "log.txt", csv_path: str = "data.csv") -> datetime:
    """Get the last processed date from log.txt or data.csv.
    
    Returns:
        datetime object representing the last processed date, or None if not found
    """
    # First, try to read from log.txt
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                date_str = f.read().strip()
                if date_str:
                    return datetime.strptime(date_str, "%Y-%m-%d")
        except Exception as e:
            print(f"Warning: Error reading {log_path}: {e}", file=sys.stderr)
    
    # If log.txt doesn't exist or is empty, try data.csv
    if os.path.exists(csv_path):
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                last_date = None
                for row in reader:
                    date_str = row.get('date_added', '').strip()
                    if date_str:
                        try:
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                            if last_date is None or date_obj > last_date:
                                last_date = date_obj
                        except ValueError:
                            continue
                if last_date:
                    print(f"Using last date from {csv_path}: {last_date.date()}", file=sys.stderr)
                    return last_date
        except Exception as e:
            print(f"Warning: Error reading {csv_path}: {e}", file=sys.stderr)
    
    return None


def save_last_processed_date(date: datetime, log_path: str = "log.txt"):
    """Save the last processed date to log.txt.
    
    Args:
        date: datetime object to save
        log_path: Path to the log file
    """
    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(date.strftime("%Y-%m-%d"))
        print(f"Saved last processed date to {log_path}: {date.date()}", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Error saving to {log_path}: {e}", file=sys.stderr)


def update_data_csv(changes: List[tuple], csv_path: str = "data.csv"):
    """Update data.csv file based on changes, processing them in chronological order.
    
    Args:
        changes: List of changes in chronological order, where each change is either:
            - (date, name) for deletions
            - (date, name, address) for additions
        csv_path: Path to the CSV file
    """
    # Read existing data
    rows = []
    if os.path.exists(csv_path):
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(row)
        except Exception as e:
            print(f"Warning: Error reading {csv_path}: {e}", file=sys.stderr)
            return
    
    # Process changes one by one in chronological order
    deletions_count = 0
    additions_count = 0
    
    for change in changes:
        if len(change) == 2:
            # Deletion: (date, name) - remove all rows with this name
            name_to_delete = change[1].strip().lower()
            original_count = len(rows)
            rows = [row for row in rows if row.get('name', '').strip().lower() != name_to_delete]
            removed = original_count - len(rows)
            if removed > 0:
                deletions_count += removed
                print(f"Removed {removed} row(s) for deletion: {change[1]}", file=sys.stderr)
        else:
            # Addition: (date, name, address) - add new row only if it doesn't already exist
            date_str = change[0].strftime("%Y-%m-%d")
            address = change[2].lower().strip()
            name = change[1].strip()
            
            # Check if this exact entry already exists (same date, address, and name)
            already_exists = False
            for row in rows:
                existing_date = row.get('date_added', '').strip()
                existing_address = row.get('address', '').lower().strip()
                existing_name = row.get('name', '').strip()
                
                if (existing_date == date_str and 
                    existing_address == address and 
                    existing_name == name):
                    already_exists = True
                    break
            
            if not already_exists:
                rows.append({
                    'date_added': date_str,
                    'address': change[2],
                    'name': change[1]
                })
                additions_count += 1
                print(f"Added row: {change[1]} - {change[2]}", file=sys.stderr)
            else:
                print(f"Skipped duplicate: {change[1]} - {change[2]}", file=sys.stderr)
    
    # Write back to CSV with all names quoted (to match original format)
    try:
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            # Write header
            f.write('date_added,address,name\n')
            for row in rows:
                date_added = row.get('date_added', '')
                address = row.get('address', '')
                name = row.get('name', '')
                # Escape quotes in name by doubling them (CSV standard)
                escaped_name = name.replace('"', '""')
                # Always quote the name field
                f.write(f'{date_added},{address},"{escaped_name}"\n')
        
        print(f"Updated {csv_path}: {deletions_count} deletion(s), {additions_count} addition(s)", file=sys.stderr)
    except Exception as e:
        print(f"Error writing to {csv_path}: {e}", file=sys.stderr)


def collect_content_pages(start_date: datetime, end_date: datetime) -> List[tuple[str, datetime]]:
    """Collect all content page URLs and dates within the date range."""
    base_url = "https://ofac.treasury.gov"
    list_url = f"{base_url}/recent-actions/sanctions-list-updates"
    content_pages = []
    page = 0
    
    with requests.Session() as session:
        while True:
            url = f"{list_url}?page={page}"
            print(f"Fetching page {page}...", file=sys.stderr)
            
            try:
                response = session.get(url, timeout=30)
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"Error fetching {url}: {e}", file=sys.stderr)
                break
            
            links = extract_content_links(response.text, base_url)
            
            if not links:
                print("No more links found", file=sys.stderr)
                break
            
            # Filter links within date range
            for link_url, link_date in links:
                if start_date <= link_date <= end_date:
                    content_pages.append((link_url, link_date))
                elif link_date < start_date:
                    # We've gone past the start date, stop
                    print(f"Reached start date {start_date.date()}", file=sys.stderr)
                    return content_pages
            
            page += 1
    
    return content_pages


def test_entity_eth_address():
    """Test function to verify entity ETH address extraction works."""
    test_name = "FUNNULL TECHNOLOGY INC"
    expected_address = "0xd5ED34b52AC4ab84d8FA8A231a3218bbF01Ed510"
    
    print(f"Testing entity: {test_name}", file=sys.stderr)
    print(f"Expected ETH address: {expected_address}", file=sys.stderr)
    
    search_results = query_ofac_search(test_name)
    
    if not search_results:
        print("ERROR: No search results found", file=sys.stderr)
        return False
    
    print(f"Found {len(search_results)} search result(s)", file=sys.stderr)
    
    found_addresses = []
    for result in search_results:
        print(f"  - {result['name']} ({result['type']})", file=sys.stderr)
        if result['detail_url']:
            print(f"  Fetching detail URL: {result['detail_url']}", file=sys.stderr)
            identifications = get_identification_details(result['detail_url'])
            print(f"  Found {len(identifications)} identifications", file=sys.stderr)
            for ident in identifications:
                print(f"    - {ident['type']}: {ident['id_number']}", file=sys.stderr)
            eth_addresses = extract_eth_address(identifications)
            if eth_addresses:
                found_addresses.extend(eth_addresses)
                print(f"Found ETH addresses: {eth_addresses}", file=sys.stderr)
        else:
            print(f"  ERROR: No detail_url found for result", file=sys.stderr)
    
    if found_addresses:
        expected_lower = expected_address.lower()
        if expected_lower in found_addresses:
            print("SUCCESS: Found correct ETH address!", file=sys.stderr)
            return True
        else:
            print(f"WARNING: Found ETH addresses {found_addresses} but expected {expected_address} not found", file=sys.stderr)
            return False
    else:
        print("ERROR: No ETH address found", file=sys.stderr)
        return False


def main():
    # Check if running test
    if len(sys.argv) == 2 and sys.argv[1] == "--test":
        success = test_entity_eth_address()
        sys.exit(0 if success else 1)
    
    # Check argument count
    if len(sys.argv) == 1:
        # No arguments: use last processed date from log.txt or data.csv
        last_date = get_last_processed_date()
        if last_date is None:
            print(f"Error: No previous date found. Please specify a start date.", file=sys.stderr)
            print(f"\nUsage:", file=sys.stderr)
            print(f"  {sys.argv[0]}                    # Continue from last processed date", file=sys.stderr)
            print(f"  {sys.argv[0]} START_DATE        # Parse from START_DATE to now", file=sys.stderr)
            print(f"  {sys.argv[0]} START_DATE END_DATE  # Parse from START_DATE to END_DATE", file=sys.stderr)
            print(f"  {sys.argv[0]} --test            # Run test", file=sys.stderr)
            sys.exit(1)
        
        start_date = last_date
        end_date = datetime.now()
        print(f"Continuing from last processed date: {start_date.date()}", file=sys.stderr)
    elif len(sys.argv) == 2:
        # Single date: parse from that date to now
        try:
            start_date = datetime.strptime(sys.argv[1], "%Y-%m-%d")
            end_date = datetime.now()
            if start_date > end_date:
                print(f"Error: Date cannot be in the future", file=sys.stderr)
                sys.exit(1)
        except ValueError:
            print(f"Invalid date format. Use YYYY-MM-DD", file=sys.stderr)
            print(f"\nUsage:", file=sys.stderr)
            print(f"  {sys.argv[0]}                    # Continue from last processed date", file=sys.stderr)
            print(f"  {sys.argv[0]} START_DATE        # Parse from START_DATE to now", file=sys.stderr)
            print(f"  {sys.argv[0]} START_DATE END_DATE  # Parse from START_DATE to END_DATE", file=sys.stderr)
            print(f"  {sys.argv[0]} --test            # Run test", file=sys.stderr)
            sys.exit(1)
    elif len(sys.argv) == 3:
        # Two dates: start and end
        try:
            start_date = datetime.strptime(sys.argv[1], "%Y-%m-%d")
            end_date = datetime.strptime(sys.argv[2], "%Y-%m-%d")
        except ValueError:
            print(f"Invalid date format. Use YYYY-MM-DD", file=sys.stderr)
            print(f"\nUsage:", file=sys.stderr)
            print(f"  {sys.argv[0]}                    # Continue from last processed date", file=sys.stderr)
            print(f"  {sys.argv[0]} START_DATE        # Parse from START_DATE to now", file=sys.stderr)
            print(f"  {sys.argv[0]} START_DATE END_DATE  # Parse from START_DATE to END_DATE", file=sys.stderr)
            print(f"  {sys.argv[0]} --test            # Run test", file=sys.stderr)
            sys.exit(1)
        
        if start_date > end_date:
            print(f"Error: Start date must be before end date", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Usage:", file=sys.stderr)
        print(f"  {sys.argv[0]}                    # Continue from last processed date", file=sys.stderr)
        print(f"  {sys.argv[0]} START_DATE        # Parse from START_DATE to now", file=sys.stderr)
        print(f"  {sys.argv[0]} START_DATE END_DATE  # Parse from START_DATE to END_DATE", file=sys.stderr)
        print(f"  {sys.argv[0]} --test            # Run test", file=sys.stderr)
        print(f"\nDates should be in format: YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)
    
    # Load existing names from data.csv
    existing_names = load_existing_names()
    
    content_pages = collect_content_pages(start_date, end_date)
    
    changes = []
    
    # Process content pages in reverse order (oldest to newest)
    for content_url, content_date in reversed(content_pages):
        print(f"\nProcessing: {content_url}", file=sys.stderr)
        individuals_added, entities_added, deletions = extract_content_data(content_url)
        
        # Process individuals added
        for name in individuals_added:
            print(f"  Querying search for individual: {name}", file=sys.stderr)
            search_results = query_ofac_search(name)
            print(f"  Found {len(search_results)} search result(s) for {name}", file=sys.stderr)
            for result in search_results:
                # Only process if the found name contains the query name (case-insensitive)
                found_name = result.get('name', '').strip().lower()
                query_name = name.strip().lower()
                if query_name not in found_name:
                    continue
                
                if result['detail_url']:
                    print(f"  Fetching detail page: {result['detail_url']}", file=sys.stderr)
                    identifications = get_identification_details(result['detail_url'])
                    print(f"  Found {len(identifications)} identification(s)", file=sys.stderr)
                    # should be eth addresses
                    eth_addresses = extract_eth_address(identifications)
                    if eth_addresses:
                        existing_names.add(name)
                        for eth_address in eth_addresses:
                            changes.append((content_date, name, eth_address))
                            print(f"Found individual addition: {name} - {eth_address}", file=sys.stderr)
        
        # Process entities added
        for name in entities_added:
            print(f"  Querying search for entity: {name}", file=sys.stderr)
            search_results = query_ofac_search(name)
            print(f"  Found {len(search_results)} search result(s) for {name}", file=sys.stderr)
            for result in search_results:
                # Only process if the found name contains the query name (case-insensitive)
                found_name = result.get('name', '').strip().lower()
                query_name = name.strip().lower()
                if query_name not in found_name:
                    continue
                
                if result['detail_url']:
                    print(f"  Fetching detail page: {result['detail_url']}", file=sys.stderr)
                    identifications = get_identification_details(result['detail_url'])
                    print(f"  Found {len(identifications)} identification(s)", file=sys.stderr)
                    eth_addresses = extract_eth_address(identifications)
                    if eth_addresses:
                        existing_names.add(name)
                        for eth_address in eth_addresses:
                            changes.append((content_date, name, eth_address))
                            print(f"Found entity addition: {name} - {eth_address}", file=sys.stderr)
        
        # Process deletions - only add if name exists in data.csv
        for name in deletions:
            if name in existing_names:
                changes.append((content_date, name))
                print(f"Found deletion: {name}", file=sys.stderr)
    
    # Output results to stdout
    for change in changes:
        if len(change) == 2:
            # Deletion: (date, name)
            print(f"Deletion: {change[0]} - {change[1]}")
        else:
            # Addition: (date, name, address)
            print(f"Addition: {change[0]} - {change[1]} - {change[2]}")
    
    # Update data.csv with changes (processed in chronological order)
    update_data_csv(changes)
    
    # Save the end_date (last processed date) to log.txt for next run
    save_last_processed_date(end_date)

if __name__ == "__main__":
    main()