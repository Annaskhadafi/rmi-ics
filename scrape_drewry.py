import sys
import os
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup

# Add src to sys.path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from tedata.scraper import TE_Scraper
from tedata.utils import send_to_api

def main():
    url = "https://www.drewry.co.uk/supply-chain-advisors/supply-chain-expertise/world-container-index-assessed-by-drewry"
    print(f"Scraping latest Drewry World Container Index from {url}...")
    
    with TE_Scraper(headless=True) as scraper:
        try:
            scraper.driver.get(url)
            # Short wait for basic page load
            time.sleep(5)
            
            html = scraper.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find the latest value in the meta description or article intro text
            # This is the most efficient way to get the single latest point
            meta_desc = soup.find('meta', {'name': 'description'})
            text_to_search = meta_desc['content'] if meta_desc else ""
            
            intro_div = soup.select_one('.aos-Article-IntroText')
            if intro_div:
                text_to_search += " " + intro_div.get_text()
            
            # If still nothing, check the specific section for Thursday's assessment
            assessment_section = soup.find(string=re.compile("Our detailed assessment for Thursday"))
            if assessment_section:
                parent_div = assessment_section.find_parent('div')
                if parent_div:
                    text_to_search += " " + parent_div.get_text()

            # Regex for price like $3,549
            price_match = re.search(r'\$(\d{1,3}(?:,\d{3})*)', text_to_search)
            price = price_match.group(1).replace(',', '') if price_match else "N/A"
            
            # Regex for date like 11 Jun 2026 or 11 Jun
            date_match = re.search(r'(\d{1,2}\s+[A-Za-z]{3}\s*\d{0,4})', text_to_search)
            date_str = date_match.group(1).strip() if date_match else "N/A"
            
            # If year is missing in date_str, append current year
            if date_str != "N/A" and not re.search(r'\d{4}', date_str):
                date_str += f" {datetime.now().year}"
                
            # Try to parse date
            try:
                price_date = datetime.strptime(date_str, '%d %b %Y').strftime('%Y-%m-%d')
            except:
                try:
                    price_date = datetime.strptime(date_str, '%d %B %Y').strftime('%Y-%m-%d')
                except:
                    price_date = datetime.now().strftime('%Y-%m-%d')
            
            if price != "N/A":
                print(f"Found latest Drewry WCI: Price={price}, Date={price_date}")
                
                # Send to API
                result = send_to_api(
                    material_name="Drewry World Container Index",
                    material_type="Freight",
                    material_price=price,
                    material_unit="40ft",
                    material_currency="USD",
                    price_date=price_date,
                    source=url
                )
                print(f"API Result: {result}")
            else:
                print("Could not find current Drewry WCI data in the page text.")
                
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
