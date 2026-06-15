import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import time
import requests
from bs4 import BeautifulSoup
import re

# Add src to sys.path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from tedata.scraper import TE_Scraper
from tedata.utils import send_to_api

def scrape_te_history(url, material_name, material_type, material_unit, material_currency):
    """Scrape historical data from Trading Economics using TE_Scraper."""
    print(f"Scraping history for {material_name} from {url}...")
    
    with TE_Scraper(headless=True) as scraper:
        try:
            if scraper.load_page(url):
                # Set custom date span from July 2022 to today
                start_date = "2022-07-01"
                end_date = datetime.now().strftime('%Y-%m-%d')
                
                print(f"Setting date span from {start_date} to {end_date}...")
                if scraper.custom_date_span_js(start_date=start_date, end_date=end_date):
                    time.sleep(5) # Wait for chart to update
                    
                    # Try to get series data from Highcharts API (most reliable for history)
                    series = scraper.series_from_highcharts()
                    
                    if series is not None and not series.empty:
                        # Filter for dates from 2022-07-01 onwards
                        series = series[series.index >= pd.to_datetime(start_date)]
                        
                        # Resample to daily to ensure we have all days
                        # TE might only have trading days, but user asked for "per harinya"
                        # We'll forward fill missing days to have a value for every day
                        daily_series = series.resample('D').ffill()
                        
                        print(f"Found {len(daily_series)} daily data points for {material_name}.")
                        
                        for date, price in daily_series.items():
                            date_str = date.strftime('%Y-%m-%d')
                            # Send to API
                            send_to_api(
                                material_name=material_name,
                                material_type=material_type,
                                material_price=str(price),
                                material_unit=material_unit,
                                material_currency=material_currency,
                                price_date=date_str,
                                source=url
                            )
                        return True
                    else:
                        print(f"Could not extract series data for {material_name}.")
            else:
                print(f"Failed to load page for {url}")
        except Exception as e:
            print(f"Error scraping {material_name}: {e}")
    return False

def scrape_imarc_latest_as_history(url, material_base_name, regions):
    """
    Scrape latest IMARC data and replicate it daily for the current month.
    Since we can't get history from 2022 from the landing page, 
    we'll at least do the daily replication for the month we have.
    """
    print(f"Scraping IMARC data for {material_base_name} from {url}...")
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        
        tables = soup.find_all('table')
        pricing_table = None
        for table in tables:
            headers = [h.get_text(strip=True).lower() for h in table.find_all(['th', 'td'])]
            if 'region' in headers and ('price' in str(headers) or 'usd' in str(headers)):
                pricing_table = table
                break
        
        if pricing_table:
            rows = pricing_table.find_all('tr')
            headers = [h.get_text(strip=True).lower() for h in rows[0].find_all(['th', 'td'])]
            region_idx = headers.index('region') if 'region' in headers else 0
            price_idx = 1
            for i, h in enumerate(headers):
                if 'price' in h or 'usd' in h:
                    price_idx = i
                    break
            
            # Use current month's start and today
            today = datetime.now()
            month_start = today.replace(day=1)
            
            for row in rows[1:]:
                cols = row.find_all('td')
                if len(cols) > max(region_idx, price_idx):
                    region = cols[region_idx].get_text(strip=True).replace('\xa0', ' ').strip()
                    if region not in regions:
                        continue
                    
                    price_raw = cols[price_idx].get_text(strip=True)
                    price_match = re.search(r'(\d+\.?\d*)', price_raw)
                    price = price_match.group(1) if price_match else None
                    
                    if price:
                        material_name = f"{material_base_name} ({region})"
                        print(f"Replicating {material_name} daily for {month_start.strftime('%B %Y')}...")
                        
                        # Loop from month start to today
                        current_date = month_start
                        while current_date <= today:
                            send_to_api(
                                material_name=material_name,
                                material_type="Material",
                                material_price=price,
                                material_unit="Kg",
                                material_currency="USD",
                                price_date=current_date.strftime('%Y-%m-%d'),
                                source=url
                            )
                            current_date += timedelta(days=1)
            return True
    except Exception as e:
        print(f"Error scraping IMARC {material_base_name}: {e}")
    return False

def main():
    # 1. Trading Economics History (July 2022 - Present)
    te_commodities = [
        {
            "url": "https://tradingeconomics.com/commodity/rubber",
            "name": "Rubber",
            "unit": "Kg",
            "currency": "USD Cents"
        },
        {
            "url": "https://tradingeconomics.com/commodity/hrc-steel",
            "name": "HRC Steel",
            "unit": "T",
            "currency": "USD"
        },
        {
            "url": "https://tradingeconomics.com/commodity/synthetic-rubber",
            "name": "Synthetic Rubber",
            "unit": "T",
            "currency": "CNY"
        }
    ]
    
    for item in te_commodities:
        scrape_te_history(item["url"], item["name"], "Material", item["unit"], item["currency"])
    
    # 2. IMARC Data (Daily replication for latest month available)
    # Note: Historical data back to 2022 is not available on the free landing page.
    imarc_regions = ["North America", "Europe"]
    scrape_imarc_latest_as_history("https://www.imarcgroup.com/carbon-black-pricing-report", "Carbon Black", imarc_regions)
    scrape_imarc_latest_as_history("https://www.imarcgroup.com/sulphur-pricing-report", "Sulphur", imarc_regions)

if __name__ == "__main__":
    main()
