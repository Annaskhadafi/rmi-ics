import sys
import os
import pandas as pd
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import re

# Add src to sys.path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from tedata.utils import send_to_api

def main():
    url = "https://www.imarcgroup.com/sulphur-pricing-report"
    print(f"Scraping Sulphur data from {url}...")
    
    try:
        # Use requests for IMARC Group as it is much faster and reliable
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Find all tables
        tables = soup.find_all('table')
        
        pricing_table = None
        for table in tables:
            # Check if this table has 'Region' in the headers or first row
            headers = table.find_all(['th', 'td'])
            header_texts = [h.get_text(strip=True).lower() for h in headers]
            
            if 'region' in header_texts and ('price' in str(header_texts) or 'usd' in str(header_texts)):
                pricing_table = table
                break
        
        if pricing_table:
            print("Found Sulphur pricing table.")
            rows = pricing_table.find_all('tr')
            
            # Find the index of columns
            headers = [h.get_text(strip=True).lower() for h in rows[0].find_all(['th', 'td'])]
            try:
                region_idx = headers.index('region')
            except ValueError:
                region_idx = 0
            
            # Find price index (it could be "price (usd/kg)" or similar)
            price_idx = 1
            for i, h in enumerate(headers):
                if 'price' in h or 'usd' in h:
                    price_idx = i
                    break
            
            # Skip header row
            for row in rows[1:]:
                cols = row.find_all('td')
                if len(cols) > max(region_idx, price_idx):
                    region = cols[region_idx].get_text(strip=True)
                    price_raw = cols[price_idx].get_text(strip=True)
                    
                    # Extract numeric price
                    price_match = re.search(r'(\d+\.?\d*)', price_raw)
                    price = price_match.group(1) if price_match else "N/A"
                    
                    if price != "N/A":
                        # Format region to be cleaner
                        region_clean = region.replace('\xa0', ' ').strip()
                        
                        # Filter for specific regions: North America and Europe
                        if region_clean not in ["North America", "Europe"]:
                            continue
                            
                        material_name = f"Sulphur ({region_clean})"
                        print(f"Found {material_name}: Price={price}")
                        
                        # Send to API
                        result = send_to_api(
                            material_name=material_name,
                            material_type="Material",
                            material_price=price,
                            material_unit="Kg",
                            material_currency="USD",
                            price_date=datetime.now().strftime('%Y-%m-%d')
                        )
                        print(f"API Result: {result}")
        else:
            print("Could not find the Sulphur pricing table on the page.")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
