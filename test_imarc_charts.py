import sys
import os
import pandas as pd
from datetime import datetime
import json

# Add src to sys.path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from tedata.scraper import TE_Scraper

def test_imarc_chart(url, name):
    print(f"Testing IMARC chart for {name} at {url}...")
    with TE_Scraper(headless=True) as scraper:
        try:
            scraper.driver.get(url)
            import time
            time.sleep(5) # Wait for chart to load
            
            # Use the highcharts extraction logic
            series = scraper.series_from_highcharts()
            if series is not None and not series.empty:
                print(f"Successfully extracted {len(series)} points for {name}.")
                print(f"First 5 points:\n{series.head()}")
                return True
            else:
                print(f"Failed to extract series for {name}.")
                # Check if Highcharts exists at all
                js_check = """
                return {
                    highcharts_defined: typeof Highcharts !== 'undefined',
                    charts_count: typeof Highcharts !== 'undefined' ? Highcharts.charts.filter(c => c).length : 0
                };
                """
                result = scraper.driver.execute_script(js_check)
                print(f"JS Check: {result}")
        except Exception as e:
            print(f"Error testing {name}: {e}")
    return False

if __name__ == "__main__":
    test_imarc_chart("https://www.imarcgroup.com/carbon-black-pricing-report", "Carbon Black")
    test_imarc_chart("https://www.imarcgroup.com/sulphur-pricing-report", "Sulphur")
