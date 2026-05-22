import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import time
import logging
import json

# Add src to sys.path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from tedata.scraper import TE_Scraper
from tedata.utils import send_to_api

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("history_scraping_july2022.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def extract_chartjs_data(driver):
    """
    Extracts data from Chart.js instances found on the page.
    Chart.js stores its data in Chart.instances or can be found via the canvas context.
    """
    js_extract = """
    var allSeries = [];
    try {
        // Method 1: Check for global Chart.instances (Chart.js v2/v3)
        var instances = [];
        if (typeof Chart !== 'undefined' && Chart.instances) {
            instances = Object.values(Chart.instances);
        } else {
            // Method 2: Search for Chart objects attached to canvas elements
            var canvases = document.getElementsByTagName('canvas');
            for (var i = 0; i < canvases.length; i++) {
                // Some implementations attach the chart object to the canvas
                for (var key in canvases[i]) {
                    if (key.toLowerCase().includes('chart') && canvases[i][key] && canvases[i][key].data) {
                        instances.push(canvases[i][key]);
                    }
                }
            }
        }

        instances.forEach(chart => {
            if (chart.data && chart.data.datasets) {
                var labels = chart.data.labels || [];
                chart.data.datasets.forEach(dataset => {
                    var points = [];
                    dataset.data.forEach((val, idx) => {
                        var label = labels[idx];
                        if (label && val !== undefined) {
                            points.push({ x: label, y: val });
                        }
                    });
                    if (points.length > 0) {
                        allSeries.push({ name: dataset.label || "Unnamed Series", points: points });
                    }
                });
            }
        });
    } catch (e) {
        return { success: false, message: e.toString() };
    }
    return { success: allSeries.length > 0, seriesData: allSeries };
    """
    return driver.execute_script(js_extract)

def scrape_imarc_commodity(scraper, url, base_name, regions):
    logger.info(f"--- Processing IMARC Commodity (Canvas/Chart.js): {base_name} ---")
    try:
        scraper.driver.get(url)
        logger.info(f"Page loaded. Waiting 20s for Canvas charts to render...")
        time.sleep(20)
        
        # Scroll to trigger rendering
        scraper.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
        time.sleep(5)
        
        result = extract_chartjs_data(scraper.driver)
        
        if not result or not result.get("success"):
            logger.error(f"Could not find Chart.js data for {base_name}. Message: {result.get('message', 'No instances found')}")
            # Log all script tags to see if data is embedded as JSON
            return False

        series_data = result["seriesData"]
        logger.info(f"Successfully found {len(series_data)} series from Canvas.")
        
        start_date_target = pd.to_datetime("2024-12-01")
        today = pd.to_datetime("2025-05-01")

        for region in regions:
            logger.info(f"Processing region: {region}")
            target_series = None
            for s in series_data:
                if region.lower() in s["name"].lower():
                    target_series = s
                    break
            
            if not target_series:
                idx = 0 if "North America" in region else 1 if len(series_data) > 1 else 0
                target_series = series_data[idx]
                logger.warning(f"Region '{region}' not matched, using index {idx} ({target_series['name']})")

            if target_series and target_series['points']:
                # Chart.js labels can be strings like "Jul-22" or full dates
                data = []
                for p in target_series['points']:
                    try:
                        # Attempt to parse common date formats used in Chart.js
                        dt = pd.to_datetime(p['x'])
                        data.append({'date': dt, 'value': p['y']})
                    except:
                        continue
                
                if not data:
                    logger.error(f"Could not parse dates from chart labels for {region}.")
                    continue

                df = pd.DataFrame(data).sort_values('date').drop_duplicates('date').set_index('date')
                series = df['value']
                
                logger.info(f"Data for {region} found from {series.index[0]} to {series.index[-1]}")
                
                # Filter, Resample (Monthly to Daily), and Forward Fill to Today
                series_filtered = series[series.index >= start_date_target]
                if series_filtered.empty:
                    series_filtered = series
                
                daily_series = series_filtered.resample('D').ffill()
                
                if daily_series.index[-1] < today:
                    new_idx = pd.date_range(start=daily_series.index[0], end=today, freq='D')
                    daily_series = daily_series.reindex(new_idx).ffill()

                logger.info(f"Prepared {len(daily_series)} daily points for {base_name} ({region}).")
                
                success_count = 0
                for date, price in daily_series.items():
                    res = send_to_api(
                        material_name=f"{base_name} ({region})",
                        material_type="Material",
                        material_price=str(price),
                        material_unit="Kg",
                        material_currency="USD",
                        price_date=date.strftime('%Y-%m-%d')
                    )
                    if res.get("status") != "error":
                        success_count += 1
                logger.info(f"Success: {success_count}/{len(daily_series)} points for {region}.")
        return True
    except Exception as e:
        logger.error(f"Error during IMARC Canvas scraping for {base_name}: {e}")
    return False

def main():
    imarc_commodities = [
        {"url": "https://www.imarcgroup.com/carbon-black-pricing-report", "base_name": "Carbon Black", "regions": ["North America", "Europe"]},
        {"url": "https://www.imarcgroup.com/sulphur-pricing-report", "base_name": "Sulphur", "regions": ["North America", "Europe"]}
    ]
    
    logger.info("Starting focused scrape for IMARC Canvas Charts (Carbon Black & Sulphur)...")
    
    with TE_Scraper(headless=True) as scraper:
        for item in imarc_commodities:
            scrape_imarc_commodity(scraper, item["url"], item["base_name"], item["regions"])
            time.sleep(5)

if __name__ == "__main__":
    main()
