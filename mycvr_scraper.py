import time
import pandas as pd
import os
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import dotenv
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class CVRScraper:
    def __init__(self, output_dir="cvr_data"):
        """Initialize the scraper with output directory."""
        self.driver = None
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
    def setup_driver(self):
        """Set up the Chrome WebDriver."""
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=options)
        
    def navigate_to_events(self, archived=True):
        """Navigate to the events page."""
        try:
            # For CVR, we directly go to the archive page
            self.driver.get("https://my.cvrobotics.org/event/archive/")
                
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
            )
            print(f"Navigated to archived events page")
            return True
        except Exception as e:
            print(f"Failed to navigate to events page: {str(e)}")
            return False
    
    def navigate_to_specific_event(self, event_id):
        """Navigate to a specific event page."""
        try:
            self.driver.get(f"https://my.cvrobotics.org/event/{event_id}/")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
            )
            print(f"Navigated to event {event_id}")
            return True
        except Exception as e:
            print(f"Failed to navigate to event {event_id}: {str(e)}")
            return False
    
    def scrape_events_list(self):
        """Scrape the list of events from the events page."""
        try:
            # Navigate to events page
            if not self.navigate_to_events():
                return []
            
            # Wait for the page to fully load
            time.sleep(2)
            
            # Get the page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find the events table
            event_table = None
            tables = soup.find_all('table')
            
            for table in tables:
                headers = table.find_all('th')
                header_texts = [header.get_text().strip() for header in headers]
                
                # Look for the table with event information
                if 'Name' in header_texts and 'Date' in header_texts:
                    event_table = table
                    break
            
            if not event_table:
                print("Events table not found")
                return []
            
            # Extract event data
            events = []
            rows = event_table.find_all('tr')[1:]  # Skip header row
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:  # Ensure we have enough cells
                    # Look for links to event pages
                    links = row.find_all('a')
                    for link in links:
                        href = link.get('href')
                        if href and '/event/' in href:
                            # Extract event ID from URL
                            event_id = href.split('/')[-2]
                            if event_id.isdigit():
                                event_data = {
                                    'event_id': event_id,
                                    'name': cells[0].get_text().strip(),
                                    'date': cells[1].get_text().strip()
                                }
                                events.append(event_data)
                                break
            
            print(f"Found {len(events)} archived events")
            
            # Save events to CSV
            if events:
                df = pd.DataFrame(events)
                filename = os.path.join(self.output_dir, "archived_events.csv")
                df.to_csv(filename, index=False)
                print(f"Saved events list to {filename}")
            
            return events
            
        except Exception as e:
            print(f"Error scraping events list: {str(e)}")
            return []
    
    def scrape_event_details(self, event_id, event_basic_info):
        """Scrape detailed information about a specific event."""
        try:
            if not self.navigate_to_specific_event(event_id):
                return None
            
            # Wait for the page to fully load
            time.sleep(2)
            
            # Get the page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract event details
            event_details = {
                'event_id': event_id,
                'name': event_basic_info['name'],
                'date': event_basic_info['date'],
                'location': '',
                'statistics': '',
                'robot_game_tables': '',
                'judging_pods': ''
            }
            
            # Try to find location and other details
            content_divs = soup.find_all('div', class_='content')
            for div in content_divs:
                text = div.get_text().strip()
                
                # Extract location
                if 'Location:' in text:
                    location_match = re.search(r'Location:\s*(.*?)(?:\n|$)', text)
                    if location_match:
                        event_details['location'] = location_match.group(1).strip()
                
                # Extract statistics
                if 'Statistics:' in text or 'Teams:' in text:
                    stats_match = re.search(r'(?:Statistics:|Teams:)\s*(.*?)(?:\n|$)', text)
                    if stats_match:
                        event_details['statistics'] = stats_match.group(1).strip()
                
                # Extract Robot Game Tables
                if 'Robot Game Tables:' in text:
                    tables_match = re.search(r'Robot Game Tables:\s*(.*?)(?:\n|$)', text)
                    if tables_match:
                        event_details['robot_game_tables'] = tables_match.group(1).strip()
                
                # Extract Judging Pods
                if 'Judging Pods:' in text:
                    pods_match = re.search(r'Judging Pods:\s*(.*?)(?:\n|$)', text)
                    if pods_match:
                        event_details['judging_pods'] = pods_match.group(1).strip()
            
            print(f"Scraped details for event {event_id}")
            return event_details
            
        except Exception as e:
            print(f"Error scraping event details: {str(e)}")
            return None
    
    def scrape_event_agenda(self, event_id):
        """Scrape the agenda for a specific event."""
        try:
            # We're already on the event page, so no need to navigate
            
            # Get the page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            agenda_items = []
            
            # Find the agenda container with id="agenda-card"
            agenda_container = soup.find(id='agenda-card')
            
            if agenda_container:
                # Find all li elements within the agenda container (directly or in ul elements)
                list_items = agenda_container.find_all('li')
                
                # If no li elements found directly, look for ul elements and then find li elements
                if not list_items:
                    agenda_lists = agenda_container.find_all('ul')
                    for ul in agenda_lists:
                        list_items.extend(ul.find_all('li'))
                
                # Process each list item
                for item in list_items:
                    # Look for span (time) and h6 (description) elements
                    span_element = item.find('span')
                    h6_element = item.find('h6')
                    
                    if span_element and h6_element:
                        # Extract time from span and description from h6
                        time = span_element.get_text().strip()
                        description = h6_element.get_text().strip()
                        
                        # Look for additional info in small element
                        additional = ""
                        small_element = item.find('small')
                        if small_element:
                            additional = small_element.get_text().strip()
                    else:
                        # If the expected structure isn't found, try to parse the whole text
                        item_text = item.get_text().strip()
                        
                        # Try to split the item into time and description
                        # Common formats: "9:00 AM - Registration" or "9:00 AM: Registration"
                        time_match = re.search(r'^([\d:]+\s*(?:AM|PM|am|pm)?(?:\s*-\s*[\d:]+\s*(?:AM|PM|am|pm)?)?)\s*[:-]\s*(.*)', item_text)
                        
                        if time_match:
                            time = time_match.group(1).strip()
                            description = time_match.group(2).strip()
                        else:
                            # If we can't parse the format, just use the whole text as description
                            time = ""
                            description = item_text
                        
                        # No additional info in this case
                        additional = ""
                    
                    agenda_item = {
                        'event_id': event_id,
                        'time': time,
                        'description': description,
                        'additional': additional
                    }
                    agenda_items.append(agenda_item)
            
            # If no agenda items found yet, try alternative approaches
            if not agenda_items:
                # Look for headings that might indicate an agenda section
                agenda_headers = [h for h in soup.find_all(['h2', 'h3', 'h4']) 
                                 if 'agenda' in h.get_text().lower() or 'schedule' in h.get_text().lower()]
                
                if agenda_headers:
                    # Find all ul elements after an agenda heading
                    for header in agenda_headers:
                        next_element = header.find_next()
                        while next_element and next_element.name != 'h2' and next_element.name != 'h3' and next_element.name != 'h4':
                            if next_element.name == 'ul':
                                list_items = next_element.find_all('li')
                                
                                for item in list_items:
                                    # Look for span (time) and h6 (description) elements
                                    span_element = item.find('span')
                                    h6_element = item.find('h6')
                                    
                                    if span_element and h6_element:
                                        # Extract time from span and description from h6
                                        time = span_element.get_text().strip()
                                        description = h6_element.get_text().strip()
                                        
                                        # Look for additional info in small element
                                        additional = ""
                                        small_element = item.find('small')
                                        if small_element:
                                            additional = small_element.get_text().strip()
                                    else:
                                        # If the expected structure isn't found, try to parse the whole text
                                        item_text = item.get_text().strip()
                                        
                                        # Try to split the item into time and description
                                        time_match = re.search(r'^([\d:]+\s*(?:AM|PM|am|pm)?(?:\s*-\s*[\d:]+\s*(?:AM|PM|am|pm)?)?)\s*[:-]\s*(.*)', item_text)
                                        
                                        if time_match:
                                            time = time_match.group(1).strip()
                                            description = time_match.group(2).strip()
                                        else:
                                            time = ""
                                            description = item_text
                                        
                                        # No additional info in this case
                                        additional = ""
                                    
                                    agenda_item = {
                                        'event_id': event_id,
                                        'time': time,
                                        'description': description,
                                        'additional': additional
                                    }
                                    agenda_items.append(agenda_item)
                            
                            next_element = next_element.find_next()
            
            # As a last resort, try to find tables that might contain agenda information
            if not agenda_items:
                tables = soup.find_all('table')
                
                for table in tables:
                    headers = table.find_all('th')
                    header_texts = [header.get_text().strip() for header in headers]
                    
                    # Look for the table with agenda information
                    if 'Time' in header_texts and len(header_texts) <= 3:
                        rows = table.find_all('tr')[1:]  # Skip header row
                        
                        for row in rows:
                            cells = row.find_all('td')
                            if len(cells) >= 2:
                                # Try to extract additional info if there's a third column
                                additional = ""
                                if len(cells) >= 3:
                                    additional = cells[2].get_text().strip()
                                
                                agenda_item = {
                                    'event_id': event_id,
                                    'time': cells[0].get_text().strip(),
                                    'description': cells[1].get_text().strip(),
                                    'additional': additional
                                }
                                agenda_items.append(agenda_item)
                        
                        break
            
            print(f"Scraped {len(agenda_items)} agenda items for event {event_id}")
            return agenda_items
            
        except Exception as e:
            print(f"Error scraping event agenda: {str(e)}")
            return []
    
    def scrape_team_information(self, event_id):
        """Scrape team information from the event page."""
        try:
            # We're already on the event page, so no need to navigate
            
            # Get the page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find the team information table
            team_table = None
            tables = soup.find_all('table')
            
            for table in tables:
                headers = table.find_all('th')
                header_texts = [header.get_text().strip() for header in headers]
                
                # Look for the table with team information
                if 'Name' in header_texts and 'City' in header_texts:
                    team_table = table
                    break
            
            if not team_table:
                print(f"Team information table not found for event {event_id}")
                return []
            
            # Extract header positions to correctly map data
            headers = team_table.find_all('th')
            header_texts = [header.get_text().strip() for header in headers]
            
            # Find indices for each column
            team_number_idx = header_texts.index('#') if '#' in header_texts else 0
            name_idx = header_texts.index('Name') if 'Name' in header_texts else 1
            city_idx = header_texts.index('City') if 'City' in header_texts else 2
            org_idx = header_texts.index('Organization') if 'Organization' in header_texts else 3
            
            # Extract team data
            teams = []
            rows = team_table.find_all('tr')[1:]  # Skip header row
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= max(team_number_idx, name_idx, city_idx) + 1:
                    team = {
                        'event_id': event_id,
                        'team_number': cells[team_number_idx].get_text().strip(),
                        'name': cells[name_idx].get_text().strip(),
                        'city': cells[city_idx].get_text().strip(),
                    }
                    
                    # Only add organization if it exists in the table
                    if 'Organization' in header_texts and len(cells) > org_idx:
                        team['organization'] = cells[org_idx].get_text().strip()
                    else:
                        team['organization'] = ""  # Set empty string if not found
                    
                    teams.append(team)
            
            print(f"Scraped information for {len(teams)} teams in event {event_id}")
            return teams
            
        except Exception as e:
            print(f"Error scraping team information: {str(e)}")
            return []
    
    def scrape_awards(self, event_id):
        """Scrape award information from the event page."""
        try:
            # We're already on the event page, so no need to navigate
            
            # Get the page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            awards = []
            
            # Look for Champions Award container
            champions_container = soup.find(id='awards-champions-container')
            if champions_container:
                # Skip the container title and only process the actual awards
                # Find all h2 elements for champions awards
                h2_elements = champions_container.find_all('h2')
                
                # Check if this is a category header or individual awards
                if len(h2_elements) == 1 and ('1st Place' not in h2_elements[0].get_text() and 
                                             '2nd Place' not in h2_elements[0].get_text() and
                                             '3rd Place' not in h2_elements[0].get_text()):
                    # This is likely just a category header, look for the actual awards in p elements
                    p_elements = champions_container.find_all('p')
                    for p in p_elements:
                        p_text = p.get_text().strip()
                        # Look for place indicators
                        if any(place in p_text for place in ['1st Place', '2nd Place', '3rd Place']):
                            # Extract award name and team info
                            parts = p_text.split('-', 1)
                            if len(parts) >= 2:
                                award_name = parts[0].strip()
                                team_info = parts[1].strip()
                                
                                # Look for organization in small element
                                organization = ""
                                small_element = p.find_next('small')
                                if small_element:
                                    organization = small_element.get_text().strip()
                                
                                # Create award entry
                                award = {
                                    'event_id': event_id,
                                    'award_category': 'Champions Award',
                                    'award_name': award_name,
                                    'team_info': team_info,
                                    'organization': organization
                                }
                                awards.append(award)
                else:
                    # Process each h2 element as an individual award
                    for h2 in h2_elements:
                        award_name = h2.get_text().strip()
                        
                        # Skip if this is just the category header without place information
                        if 'Champions Award' == award_name and not any(place in award_name for place in ['1st Place', '2nd Place', '3rd Place']):
                            continue
                        
                        # Find the next p element (team info)
                        team_element = h2.find_next('p')
                        if team_element:
                            team_info = team_element.get_text().strip()
                            
                            # Look for organization in small element
                            organization = ""
                            small_element = team_element.find_next('small')
                            if small_element:
                                organization = small_element.get_text().strip()
                            
                            # Create award entry
                            award = {
                                'event_id': event_id,
                                'award_category': 'Champions Award',
                                'award_name': award_name,
                                'team_info': team_info,
                                'organization': organization
                            }
                            awards.append(award)
            
            # Look for core awards container
            core_awards_container = soup.find(id='awards-core-container')
            if core_awards_container:
                # Find all h3 elements for core awards
                h3_elements = core_awards_container.find_all('h3')
                for h3 in h3_elements:
                    award_name = h3.get_text().strip()
                    
                    # Find the next p element (team info)
                    team_element = h3.find_next('p')
                    if team_element:
                        team_info = team_element.get_text().strip()
                        
                        # Look for organization in small element
                        organization = ""
                        small_element = team_element.find_next('small')
                        if small_element:
                            organization = small_element.get_text().strip()
                        
                        # Create award entry
                        award = {
                            'event_id': event_id,
                            'award_category': 'Core Awards',
                            'award_name': award_name,
                            'team_info': team_info,
                            'organization': organization
                        }
                        awards.append(award)
            
            # Look for other awards container
            other_awards_container = soup.find(id='awards-other-container')
            if other_awards_container:
                # Find all h4 elements for other awards
                h4_elements = other_awards_container.find_all('h4')
                for h4 in h4_elements:
                    award_name = h4.get_text().strip()
                    
                    # Find the next p element (team info)
                    team_element = h4.find_next('p')
                    if team_element:
                        team_info = team_element.get_text().strip()
                        
                        # Look for organization in small element
                        organization = ""
                        small_element = team_element.find_next('small')
                        if small_element:
                            organization = small_element.get_text().strip()
                        
                        # Create award entry
                        award = {
                            'event_id': event_id,
                            'award_category': 'Other Awards',
                            'award_name': award_name,
                            'team_info': team_info,
                            'organization': organization
                        }
                        awards.append(award)
            
            # If no awards found yet, try alternative approaches
            if not awards:
                # Try to find awards in the general awards container
                awards_container = soup.find(id='awards-container')
                if awards_container:
                    # Look for Champions Award heading
                    champions_headers = [h for h in awards_container.find_all(['h2', 'h3']) 
                                       if 'Champions' in h.get_text()]
                    
                    for header in champions_headers:
                        award_name = header.get_text().strip()
                        
                        # Find the next p element (team info)
                        team_element = header.find_next('p')
                        if team_element:
                            team_info = team_element.get_text().strip()
                            
                            # Look for organization in small element
                            organization = ""
                            small_element = team_element.find_next('small')
                            if small_element:
                                organization = small_element.get_text().strip()
                            
                            # Create award entry
                            award = {
                                'event_id': event_id,
                                'award_category': 'Champions Award',
                                'award_name': award_name,
                                'team_info': team_info,
                                'organization': organization
                            }
                            awards.append(award)
                    
                    # Look for h3 elements (core awards)
                    h3_elements = awards_container.find_all('h3')
                    for h3 in h3_elements:
                        if 'Award' in h3.get_text() and 'Champions' not in h3.get_text():
                            award_name = h3.get_text().strip()
                            
                            # Find the next p element (team info)
                            team_element = h3.find_next('p')
                            if team_element:
                                team_info = team_element.get_text().strip()
                                
                                # Look for organization in small element
                                organization = ""
                                small_element = team_element.find_next('small')
                                if small_element:
                                    organization = small_element.get_text().strip()
                                
                                # Create award entry
                                award = {
                                    'event_id': event_id,
                                    'award_category': 'Core Awards',
                                    'award_name': award_name,
                                    'team_info': team_info,
                                    'organization': organization
                                }
                                awards.append(award)
                    
                    # Look for h4 elements (other awards)
                    h4_elements = awards_container.find_all('h4')
                    for h4 in h4_elements:
                        if 'Award' in h4.get_text():
                            award_name = h4.get_text().strip()
                            
                            # Find the next p element (team info)
                            team_element = h4.find_next('p')
                            if team_element:
                                team_info = team_element.get_text().strip()
                                
                                # Look for organization in small element
                                organization = ""
                                small_element = team_element.find_next('small')
                                if small_element:
                                    organization = small_element.get_text().strip()
                                
                                # Create award entry
                                award = {
                                    'event_id': event_id,
                                    'award_category': 'Other Awards',
                                    'award_name': award_name,
                                    'team_info': team_info,
                                    'organization': organization
                                }
                                awards.append(award)
            
            # If still no awards found, try the fallback approaches with tables
            if not awards:
                # Look for award sections
                award_sections = soup.find_all('div', class_='award-section')
                
                if not award_sections:
                    # Try to find Champions Award in headings
                    champions_headers = [h for h in soup.find_all(['h2', 'h3']) 
                                       if 'Champions' in h.get_text()]
                    
                    for header in champions_headers:
                        # Try to find team info in the next paragraph or table
                        team_element = header.find_next('p')
                        if team_element:
                            team_info = team_element.get_text().strip()
                            
                            # Look for organization in small element
                            organization = ""
                            small_element = team_element.find_next('small')
                            if small_element:
                                organization = small_element.get_text().strip()
                            
                            award = {
                                'event_id': event_id,
                                'award_category': 'Champions Award',
                                'award_name': header.get_text().strip(),
                                'team_info': team_info,
                                'organization': organization
                            }
                            awards.append(award)
                    
                    # Try to find awards by looking for h3 headings with "Award" in the text
                    h3_elements = soup.find_all('h3')
                    for h3 in h3_elements:
                        if 'Award' in h3.get_text() and 'Champions' not in h3.get_text():
                            # Found an award section heading
                            award_category = 'Core Awards' if 'Core' in h3.get_text() else 'Other Awards'
                            
                            # Find the table that follows this heading
                            award_table = h3.find_next('table')
                            if award_table:
                                rows = award_table.find_all('tr')[1:]  # Skip header row
                                for row in rows:
                                    cells = row.find_all('td')
                                    if len(cells) >= 2:
                                        # Try to extract organization if there's a third column
                                        organization = ""
                                        if len(cells) >= 3:
                                            organization = cells[2].get_text().strip()
                                        
                                        award = {
                                            'event_id': event_id,
                                            'award_category': award_category,
                                            'award_name': cells[0].get_text().strip(),
                                            'team_info': cells[1].get_text().strip(),
                                            'organization': organization
                                        }
                                        awards.append(award)
                else:
                    # Process structured award sections
                    for section in award_sections:
                        section_title = section.find('h3')
                        if section_title:
                            title_text = section_title.get_text()
                            if 'Champions' in title_text:
                                award_category = 'Champions Award'
                            elif 'Core' in title_text:
                                award_category = 'Core Awards'
                            else:
                                award_category = 'Other Awards'
                            
                            award_table = section.find('table')
                            if award_table:
                                rows = award_table.find_all('tr')[1:]  # Skip header row
                                for row in rows:
                                    cells = row.find_all('td')
                                    if len(cells) >= 2:
                                        # Try to extract organization if there's a third column
                                        organization = ""
                                        if len(cells) >= 3:
                                            organization = cells[2].get_text().strip()
                                        
                                        award = {
                                            'event_id': event_id,
                                            'award_category': award_category,
                                            'award_name': cells[0].get_text().strip(),
                                            'team_info': cells[1].get_text().strip(),
                                            'organization': organization
                                        }
                                        awards.append(award)
            
            print(f"Scraped {len(awards)} awards for event {event_id}")
            return awards
            
        except Exception as e:
            print(f"Error scraping awards: {str(e)}")
            return []
    
    def save_to_csv(self, data, filename):
        """Save data to a CSV file."""
        if not data:
            print(f"No data to save to {filename}")
            return False
        
        try:
            df = pd.DataFrame(data)
            full_path = os.path.join(self.output_dir, filename)
            df.to_csv(full_path, index=False)
            print(f"Data saved to {full_path}")
            return True
        except Exception as e:
            print(f"Error saving to CSV: {str(e)}")
            return False
    
    def process_event(self, event_basic_info):
        """Process a single event and save all related data to CSV files."""
        event_id = event_basic_info['event_id']
        print(f"\nProcessing event: {event_basic_info['name']} (ID: {event_id})")
        
        # Scrape detailed information
        event_details = self.scrape_event_details(event_id, event_basic_info)
        if not event_details:
            print(f"Skipping event {event_id} due to missing details")
            return False
        
        # Create event directory
        event_dir = os.path.join(self.output_dir, f"event_{event_id}")
        if not os.path.exists(event_dir):
            os.makedirs(event_dir)
        
        # Save event details
        self.save_to_csv([event_details], os.path.join(f"event_{event_id}", "event_details.csv"))
        
        # Scrape teams, agenda, and awards
        teams = self.scrape_team_information(event_id)
        agenda_items = self.scrape_event_agenda(event_id)
        awards = self.scrape_awards(event_id)
        
        # Save to CSV files
        self.save_to_csv(teams, os.path.join(f"event_{event_id}", "teams.csv"))
        self.save_to_csv(agenda_items, os.path.join(f"event_{event_id}", "agenda.csv"))
        self.save_to_csv(awards, os.path.join(f"event_{event_id}", "awards.csv"))
        
        # Also save to combined files
        if teams:
            all_teams_file = "all_teams.csv"
            if os.path.exists(os.path.join(self.output_dir, all_teams_file)):
                existing_df = pd.read_csv(os.path.join(self.output_dir, all_teams_file))
                teams_df = pd.DataFrame(teams)
                combined_df = pd.concat([existing_df, teams_df], ignore_index=True)
                combined_df.to_csv(os.path.join(self.output_dir, all_teams_file), index=False)
            else:
                self.save_to_csv(teams, all_teams_file)
        
        if awards:
            all_awards_file = "all_awards.csv"
            if os.path.exists(os.path.join(self.output_dir, all_awards_file)):
                existing_df = pd.read_csv(os.path.join(self.output_dir, all_awards_file))
                awards_df = pd.DataFrame(awards)
                combined_df = pd.concat([existing_df, awards_df], ignore_index=True)
                combined_df.to_csv(os.path.join(self.output_dir, all_awards_file), index=False)
            else:
                self.save_to_csv(awards, all_awards_file)
        
        return True
    
    def run(self, limit_events=None):
        """Run the complete scraping process."""
        try:
            self.setup_driver()
            
            # Scrape archived events
            print("Scraping archived events...")
            archived_events = self.scrape_events_list()
            
            # Limit the number of events if specified
            if limit_events and isinstance(limit_events, int) and limit_events > 0:
                archived_events = archived_events[:limit_events]
                print(f"Limiting to {limit_events} archived events")
            
            # Process each event
            for event_basic_info in archived_events:
                self.process_event(event_basic_info)
            
            print("\nScraping process completed successfully!")
            return True
            
        except Exception as e:
            print(f"Error in scraping process: {str(e)}")
            return False
        finally:
            # Always close the browser
            if self.driver:
                self.driver.quit()
                print("Browser closed")

if __name__ == "__main__":
    # Create scraper with output directory
    scraper = CVRScraper(output_dir="cvr_data")
    
    # Run the scraper - only scrape archived events
    # Set limit_events to a small number for testing (e.g., 5)
    # or set to None to scrape all archived events
    scraper.run(limit_events=5)
