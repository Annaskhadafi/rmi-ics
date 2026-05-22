import sys
import os
import pandas as pd
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# Add src to sys.path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from tedata.scraper import TE_Scraper
from tedata.utils import send_to_api

def extract_from_soup(soup, start_date, end_date):
    """Extracted logic from our previous successful script to parse Highcharts SVG."""
    # ... (historical extraction logic remains for potential other uses, but we won't save to Excel)
    pass

def main():
    url = "https://tradingeconomics.com/commodity/hrc-steel"
    print(f"Scraping HRC Steel from {url}...")
    
    with TE_Scraper(headless=True) as scraper:
        try:
            scraper.load_page(url)
            import time
            time.sleep(5)
            
            html = scraper.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # --- PART 1: Live Data (Table) ---
            # Try HRC:COM row
            hrc_row = soup.find('tr', {'data-symbol': 'HRC:COM'})
            
            price, date_str = "N/A", "N/A"
            
            if hrc_row:
                price_td = hrc_row.find('td', id='p')
                price = price_td.get_text(strip=True) if price_td else "N/A"
                date_td = hrc_row.find('td', id='date')
                date_str = date_td.get_text(strip=True) if date_td else datetime.now().strftime('%Y-%m-%d')
            else:
                # Fallback to item_definition table
                table = soup.select_one('#item_definition table')
                if table:
                    rows = table.find_all('tr')
                    if len(rows) >= 2:
                        cols = rows[1].find_all('td')
                        if len(cols) >= 2:
                            actual = cols[1].get_text(strip=True).replace(',', '')
                            price = actual
                            date_str = cols[5].get_text(strip=True) # Dates column
            
            if price != "N/A":
                print(f"Found HRC Steel Live: Price={price}")
                # Send to API
                # HRC Steel is typically USD/T
                result = send_to_api(
                    material_name="HRC Steel",
                    material_type="Material",
                    material_price=price,
                    material_unit="T",
                    material_currency="USD",
                    price_date=datetime.now().strftime('%Y-%m-%d')
                )
                print(f"API Result: {result}")
            else:
                print("Could not find HRC Steel live data.")

            # --- PART 2: Historical Data (Chart) ---
            # (Excel saving removed)
                
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
