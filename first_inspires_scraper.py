import time
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from bs4 import BeautifulSoup

class FIRSTInspiresScraper:
    def __init__(self, output_dir="first_inspires_data", page_limit=None):
        """Initialize the scraper with output directory and optional page limit."""
        self.driver = None
        self.output_dir = output_dir
        self.current_page = 1
        self.page_limit = page_limit
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
    def setup_driver(self):
        """Set up the Chrome WebDriver with improved options."""
        try:
            chrome_options = Options()
            # Add options to make browser more stable
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-features=NetworkService')
            chrome_options.add_argument('--window-size=1920x1080')
            chrome_options.add_argument('--disable-notifications')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-extensions')
            
            # Create Chrome WebDriver service using webdriver_manager
            service = Service(ChromeDriverManager().install())
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(10)  # Add implicit wait
            return True
            
        except Exception as e:
            print(f"Failed to setup Chrome WebDriver: {str(e)}")
            return False
            
    def wait_for_element(self, by, value, timeout=20):
        """Wait for an element to be present and visible."""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of(element)
            )
            return element
        except TimeoutException:
            print(f"Timeout waiting for element: {value}")
            return None
            
    def navigate_to_team_search(self):
        """Navigate to the FIRST Inspires team search page."""
        try:
            # First navigate to main page
            print("Navigating to main page...")
            self.driver.get("https://www.firstinspires.org/")
            time.sleep(5)  # Wait for initial page load
            
            # Then navigate to team search page
            print("Navigating to team search page...")
            self.driver.get("https://www.firstinspires.org/team-event-search#type=teams&sort=name&programs=FLL&year=2024")
            
            # Wait for the search results container
            print("Waiting for search results...")
            time.sleep(5)  # Wait for page transition
            
            # Wait for the results container
            results_container = self.wait_for_element(By.ID, "dTeamEventResults")
            if not results_container:
                return False
                
            # Wait for actual team results to appear
            team_results = self.wait_for_element(By.CLASS_NAME, "team-event-result")
            if not team_results:
                return False
            
            print("Successfully navigated to team search page")
            return True
            
        except Exception as e:
            print(f"Failed to navigate to team search page: {str(e)}")
            return False
            
    def extract_team_info(self, team_div):
        """Extract team information from a team result div."""
        try:
            # Find all dt (labels) and dd (values) elements
            dts = team_div.find_all('dt')
            dds = team_div.find_all('dd')
            
            # Create a dictionary to store the team info
            team_info = {}
            
            # Map the labels to their values
            for dt, dd in zip(dts, dds):
                label = dt.get_text().strip().rstrip(':')
                value = dd.get_text().strip()
                
                if label == 'Team Number':
                    team_info['team_number'] = value
                elif label == 'Team Nickname':
                    team_info['team_nickname'] = value
                elif label == 'Organization(s)':
                    team_info['organization'] = value
                elif label == 'Program':
                    team_info['program'] = value
                elif label == 'Location':
                    team_info['location'] = value
                elif label == 'Rookie Year':
                    team_info['rookie_year'] = value
            
            return team_info
            
        except Exception as e:
            print(f"Error extracting team info: {str(e)}")
            return None
            
    def click_next_page(self):
        """Click the next page button with proper waiting and retries."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Wait for the page links container
                page_links_div = self.wait_for_element(By.CLASS_NAME, "page-links")
                if not page_links_div:
                    return False
                
                # Find the next page number
                next_page = self.current_page + 1
                
                # Try to find the link for the next page number first
                try:
                    next_page_link = self.driver.find_element(By.CSS_SELECTOR, f"a.pagelink[title='{next_page}']")
                    if next_page_link and next_page_link.is_displayed():
                        # Scroll into view
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", next_page_link)
                        time.sleep(2)
                        
                        # Try JavaScript click first
                        self.driver.execute_script("arguments[0].click();", next_page_link)
                        time.sleep(5)
                        
                        self.current_page = next_page
                        return True
                except NoSuchElementException:
                    pass
                
                # If we couldn't find or click the page number, try the next button
                next_button = self.driver.find_element(By.CSS_SELECTOR, "a.next-btn")
                if not next_button or not next_button.is_displayed():
                    print("Next button not found or not visible")
                    return False
                
                # Scroll into view
                self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                time.sleep(2)
                
                # Try JavaScript click first
                self.driver.execute_script("arguments[0].click();", next_button)
                time.sleep(5)
                
                # Wait for new results to load
                self.wait_for_element(By.CLASS_NAME, "team-event-result")
                self.current_page += 1
                return True
                
            except ElementClickInterceptedException:
                print(f"Click intercepted, retrying... ({retry_count + 1}/{max_retries})")
                retry_count += 1
                time.sleep(2)
            except NoSuchElementException:
                print("No next button found - reached last page")
                return False
            except Exception as e:
                print(f"Error clicking next page: {str(e)}")
                return False
        
        return False
            
    def scrape_team_data(self):
        """Scrape team information from the search results."""
        try:
            teams = []
            has_more_pages = True
            
            while has_more_pages:
                print(f"\nProcessing page {self.current_page}...")
                # Wait for results to load
                time.sleep(5)  # Increased wait time
                
                # Wait for team results to be present
                results_container = self.wait_for_element(By.ID, "dTeamEventResults")
                if not results_container:
                    break
                
                # Parse the current page
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Find all team result divs
                team_divs = soup.find_all('div', class_='team-event-result')
                
                if not team_divs:
                    print("No team results found on current page")
                    break
                
                # Process each team div
                for team_div in team_divs:
                    team_info = self.extract_team_info(team_div)
                    if team_info:
                        teams.append(team_info)
                
                print(f"Scraped {len(teams)} teams so far...")
                
                # Check if we've reached the page limit
                if self.page_limit and self.current_page >= self.page_limit:
                    print(f"Reached specified page limit of {self.page_limit}")
                    break
                
                # Try to go to next page
                has_more_pages = self.click_next_page()
                if not has_more_pages:
                    print("No more pages to scrape")
            
            print(f"Finished scraping {len(teams)} teams across {self.current_page} pages")
            return teams
            
        except Exception as e:
            print(f"Error scraping team data: {str(e)}")
            return []
            
    def save_to_csv(self, data, filename="teams.csv"):
        """Save scraped data to a CSV file."""
        if not data:
            print("No data to save")
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
            
    def run(self):
        """Run the complete scraping process."""
        try:
            if not self.setup_driver():
                return False
            
            # Navigate to search page
            if not self.navigate_to_team_search():
                return False
            
            # Scrape team data
            teams = self.scrape_team_data()
            
            # Save results
            if teams:
                self.save_to_csv(teams)
                
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
    # Test run with first 5 pages
    print("Testing scraper with first 5 pages...")
    scraper = FIRSTInspiresScraper(page_limit=5)
    scraper.run()
    
    # If you want to scrape all pages, uncomment the following lines:
    # print("\nScraping all pages...")
    # scraper = FIRSTInspiresScraper()
    # scraper.run() 