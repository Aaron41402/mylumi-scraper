# MyLumi Event Scraper

A web scraper for extracting event information from the MyLumi platform.

## Features

- Scrapes archived events from MyLumi
- Extracts event details, team information, agenda items, and awards
- Saves data to CSV files for easy analysis

## Requirements

- Python 3.7+
- Chrome browser
- Required Python packages (see requirements.txt)

## Installation

1. Clone this repository
2. Install required packages: `pip install -r requirements.txt`
3. Create a `.env` file with your credentials:
   ```
   MYLUMI_USERNAME=your_username
   MYLUMI_PASSWORD=your_password
   ```

## Usage

Run the scraper with:
python mylumi_scraper.py


By default, it will scrape 6 archived events. To scrape all events, modify the `limit_events` parameter to `None`.

## Output

Data is saved to the `mylumi_data` directory with the following structure:
- `archived_events.csv`: List of all archived events
- `all_teams.csv`: Combined list of all teams from all events
- `all_awards.csv`: Combined list of all awards from all events
- `event_[ID]/`: Directory for each event containing:
  - `event_details.csv`: Event information
  - `teams.csv`: Teams participating in the event
  - `agenda.csv`: Event agenda items
  - `awards.csv`: Awards given at the event