import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import time
import logging

# Add src to sys.path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from tedata.scraper import TE_Scraper
from tedata.utils import send_to_api

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_history_daily(url, material_name, material_type, material_unit, material_currency, source_type="TE"):
    """
    Scrape historical data and ensure daily frequency from July 2022.
    """
    logger.info(f"Scraping history for {material_name} from {url}...")
    
    start_date_str = "2022-07-01"
    start_date_dt = pd.to_datetime(start_date_str)
    
    with TE_Scraper(headless=True) as scraper:
        try:
            if not scraper.load_page(url):
                # Fallback for non-TE pages or if load_page fails
                scraper.driver.get(url)
                time.sleep(5)
            
            # Use Highcharts extraction as it's the most reliable for historical series
            # This works for both TE and IMARC if they use Highcharts
            series = scraper.series_from_highcharts()
            
            if series is not None and not series.empty:
                # Handle cases where multiple series might be returned (for IMARC)
                # series_from_highcharts returns a single series based on first series usually.
                # If we need specific series from IMARC, we might need a more custom call.
                
                # Ensure index is datetime
                series.index = pd.to_datetime(series.index)
                
                # Filter from July 2022
                series = series[series.index >= start_date_dt]
                
                if series.empty:
                    logger.warning(f"No data found from {start_date_str} for {material_name}")
                    return False
                
                # Resample to daily frequency and forward fill
                # This ensures "data per harinya di bulan yang sama maka pricenya akan sama"
                daily_series = series.resample('D').ffill()
                
                # If the first date is after July 1st 2022, we might want to backfill if possible,
                # but usually we just start from what's available.
                
                logger.info(f"Found {len(daily_series)} daily data points for {material_name}.")
                
                success_count = 0
                for date, price in daily_series.items():
                    date_str = date.strftime('%Y-%m-%d')
                    # Send to API
                    result = send_to_api(
                        material_name=material_name,
                        material_type=material_type,
                        material_price=str(price),
                        material_unit=material_unit,
                        material_currency=material_currency,
                        price_date=date_str
                    )
                    if result.get("status") != "error":
                        success_count += 1
                
                logger.info(f"Successfully processed {success_count}/{len(daily_series)} points for {material_name}.")
                return True
            else:
                logger.error(f"Could not extract series data for {material_name}.")
        except Exception as e:
            logger.error(f"Error scraping {material_name}: {e}")
    return False

def main():
    # 1. Trading Economics Commodities
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
    
    # 2. IMARC Commodities (using chart data)
    imarc_commodities = [
        {
            "url": "https://www.imarcgroup.com/carbon-black-pricing-report",
            "name": "Carbon Black (North America)",
            "unit": "Kg",
            "currency": "USD"
        },
        {
            "url": "https://www.imarcgroup.com/carbon-black-pricing-report",
            "name": "Carbon Black (Europe)",
            "unit": "Kg",
            "currency": "USD"
        },
        {
            "url": "https://www.imarcgroup.com/sulphur-pricing-report",
            "name": "Sulphur (North America)",
            "unit": "Kg",
            "currency": "USD"
        },
        {
            "url": "https://www.imarcgroup.com/sulphur-pricing-report",
            "name": "Sulphur (Europe)",
            "unit": "Kg",
            "currency": "USD"
        }
    ]
    
    # Scrape TE commodities
    for item in te_commodities:
        scrape_history_daily(item["url"], item["name"], "Material", item["unit"], item["currency"])
    
    # Scrape IMARC commodities
    # Note: IMARC charts often have multiple series. 
    # The simple scrape_history_daily might need adjustment to select the right series index.
    # For now, let's try to handle them specifically if needed.
    
    for item in imarc_commodities:
        # We might need to pass the series index if they are in the same chart
        # But for now, let's see if we can just get them.
        # If IMARC charts have multiple series, scraper.series_from_highcharts() 
        # normally only returns the first one unless modified.
        
        # Custom logic for IMARC multiple series
        logger.info(f"Scraping IMARC history for {item['name']}...")
        with TE_Scraper(headless=True) as scraper:
            try:
                scraper.driver.get(item["url"])
                time.sleep(5)
                
                # Run the JS directly to get all series
                js_file_path = os.path.join(os.getcwd(), 'src', 'tedata', 'check_highcharts.js')
                with open(js_file_path, 'r') as f:
                    script = f.read()
                
                result = scraper.driver.execute_async_script(script)
                if result and result.get("success") and result.get("seriesData"):
                    series_data = result["seriesData"]
                    
                    # Find the series that matches the region
                    target_series = None
                    region = "North America" if "North America" in item["name"] else "Europe"
                    
                    for s in series_data:
                        if region.lower() in s["name"].lower():
                            target_series = s
                            break
                    
                    if not target_series and series_data:
                        # Fallback to first series if region not found in names
                        target_series = series_data[0]
                    
                    if target_series:
                        data = [(p['x'], p['y']) for p in target_series['points']]
                        df = pd.DataFrame(data, columns=['timestamp', 'value'])
                        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                        df = df.set_index('date')
                        series = df['value']
                        
                        # Filter and resample
                        series = series[series.index >= pd.to_datetime("2022-07-01")]
                        daily_series = series.resample('D').ffill()
                        
                        logger.info(f"Found {len(daily_series)} daily points for {item['name']}")
                        
                        for date, price in daily_series.items():
                            send_to_api(
                                material_name=item["name"],
                                material_type="Material",
                                material_price=str(price),
                                material_unit=item["unit"],
                                material_currency=item["currency"],
                                price_date=date.strftime('%Y-%m-%d')
                            )
                else:
                    logger.error(f"Could not extract IMARC chart data for {item['name']}")
            except Exception as e:
                logger.error(f"Error scraping IMARC {item['name']}: {e}")

if __name__ == "__main__":
    main()
