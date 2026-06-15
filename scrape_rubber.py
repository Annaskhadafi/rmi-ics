import sys
import os
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup

# Add src to sys.path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from tedata.scraper import TE_Scraper
from tedata.utils import send_to_api

def main():
    url = "https://tradingeconomics.com/commodity/rubber"
    print(f"Scraping live data from {url}...")
    
    # Initialize scraper
    with TE_Scraper(headless=True) as scraper:
        try:
            scraper.load_page(url)
            # Wait a bit for the table to load completely if needed
            import time
            time.sleep(3)
            
            # Get the page source and parse with BeautifulSoup
            soup = BeautifulSoup(scraper.driver.page_source, 'html.parser')
            
            # Find the Rubber row in the table
            # Row usually has data-symbol="JN1:COM"
            rubber_row = soup.find('tr', {'data-symbol': 'JN1:COM'})
            
            if not rubber_row:
                # Fallback: search by text "Rubber" in links
                rubber_link = soup.find('a', string=lambda t: t and 'Rubber' in t)
                if rubber_link:
                    rubber_row = rubber_link.find_parent('tr')
            
            if rubber_row:
                # Extract data from the row
                # <td id="p"> is the price
                price_td = rubber_row.find('td', id='p')
                price = price_td.get_text(strip=True) if price_td else "N/A"
                
                # <td id="date"> is the date/time
                date_td = rubber_row.find('td', id='date')
                date_str = date_td.get_text(strip=True) if date_td else datetime.now().strftime('%Y-%m-%d')
                
                print(f"Found Rubber: Price={price}, Date={date_str}")
                
                if price != "N/A":
                    # Send to API
                    # Rubber (JN1:COM) is typically JPY/kg
                    result = send_to_api(
                        material_name="Rubber",
                        material_type="Material",
                        material_price=price,
                        material_unit="Kg",
                        material_currency="USD Cents",
                        price_date=datetime.now().strftime('%Y-%m-%d'), # Using today's date for consistent format
                        source=url
                    )
                    print(f"API Result: {result}")
                else:
                    print("Price not found.")
            else:
                print("Could not find the Rubber data row in the table.")
                
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
