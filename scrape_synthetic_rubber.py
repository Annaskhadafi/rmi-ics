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
    url = "https://tradingeconomics.com/commodity/synthetic-rubber"
    print(f"Scraping Synthetic Rubber from {url}...")
    
    with TE_Scraper(headless=True) as scraper:
        try:
            scraper.load_page(url)
            import time
            time.sleep(5) # Give it more time to render Highcharts
            
            html = scraper.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # --- PART 1: Live Data (Table) ---
            # Synthetic Rubber symbol is SYNTHETICRUBBER:COM
            sr_row = soup.find('tr', {'data-symbol': 'SYNTHETICRUBBER:COM'})
            if not sr_row:
                # Fallback to text search
                sr_link = soup.find('a', string=lambda t: t and 'Synthetic Rubber' in t)
                if sr_link:
                    sr_row = sr_link.find_parent('tr')
            
            if sr_row:
                price_td = sr_row.find('td', id='p')
                price = price_td.get_text(strip=True) if price_td else "N/A"
                date_td = sr_row.find('td', id='date')
                date_str = date_td.get_text(strip=True) if date_td else datetime.now().strftime('%Y-%m-%d')
                
                print(f"Found Synthetic Rubber Live: Price={price}")
                
                if price != "N/A":
                    # Send to API
                    # Synthetic Rubber is typically CNY/T
                    result = send_to_api(
                        material_name="Synthetic Rubber",
                        material_type="Material",
                        material_price=price,
                        material_unit="T",
                        material_currency="CNY",
                        price_date=datetime.now().strftime('%Y-%m-%d')
                    )
                    print(f"API Result: {result}")
            else:
                print("Could not find Synthetic Rubber live data.")

            # --- PART 2: Historical Data (Chart) ---
            # (Excel saving removed)
                
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
