import sys
import os
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# Add src to sys.path to prioritize local version
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from tedata.utils import send_to_api

try:
    from tedata.scraper import TE_Scraper
    HAS_TE_SCRAPER = True
except ImportError:
    HAS_TE_SCRAPER = False

def extract_coal_data_from_soup(soup):
    """
    Ekstraksi harga dan tanggal coal dari BeautifulSoup object.
    Mendukung beberapa selector fallback:
    1. Row data-symbol='XAL1:COM' (Newcastle Coal di Trading Economics)
    2. Link bertuliskan 'Batubara' atau 'Coal'
    3. Tabel summary di #item_definition
    """
    price, date_str = None, None

    # 1. Primary: data-symbol XAL1:COM
    coal_row = soup.find('tr', {'data-symbol': 'XAL1:COM'})

    # 2. Secondary fallback: link teks Batubara / Coal
    if not coal_row:
        link = soup.find('a', string=lambda t: t and ('coal' in t.lower() or 'batubara' in t.lower()))
        if link:
            coal_row = link.find_parent('tr')

    if coal_row:
        price_td = coal_row.find('td', id='p')
        if price_td:
            price = price_td.get_text(strip=True)
        date_td = coal_row.find('td', id='date')
        if date_td:
            date_str = date_td.get_text(strip=True)

    # 3. Tertiary fallback: #item_definition table
    if not price:
        item_table = soup.select_one('#item_definition table')
        if item_table:
            rows = item_table.find_all('tr')
            if len(rows) >= 2:
                cols = rows[1].find_all('td')
                if len(cols) >= 2:
                    price = cols[1].get_text(strip=True)
                if len(cols) >= 6:
                    date_str = cols[5].get_text(strip=True)

    return price, date_str

def scrape_with_requests(url):
    """Scrape data menggunakan requests (cepat dan ringan seperti scrape_carbon_black.py)."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    return extract_coal_data_from_soup(soup)

def scrape_with_selenium(url):
    """Fallback scrape menggunakan Selenium TE_Scraper jika requests terhambat."""
    if not HAS_TE_SCRAPER:
        return None, None
    
    with TE_Scraper(headless=True) as scraper:
        scraper.load_page(url)
        import time
        time.sleep(3)
        soup = BeautifulSoup(scraper.driver.page_source, 'html.parser')
        return extract_coal_data_from_soup(soup)

def main():
    url = "https://id.tradingeconomics.com/commodity/coal"
    print(f"Scraping Coal data from {url}...")
    
    # Konfigurasi data komoditas
    material_name = "Batubara"      # Nama material (dapat disesuaikan jika ingin "Batubara")
    material_type = "Mineral"  # Tipe material (atau "Mineral" seperti di Minerba)
    material_unit = "T"         # Batubara Newcastle diperdagangkan dalam USD/ton (T)
    material_currency = "USD"
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    price_raw, date_str = None, None

    # Coba dengan requests terlebih dahulu (lebih cepat & efisien)
    try:
        print("Mencoba scraping menggunakan requests...")
        price_raw, date_str = scrape_with_requests(url)
        if price_raw:
            print("Berhasil mengambil data via requests.")
    except Exception as req_err:
        print(f"Gagal via requests ({req_err}), mencoba fallback dengan Selenium TE_Scraper...")

    # Jika requests gagal atau data belum ditemukan, coba via TE_Scraper
    if not price_raw and HAS_TE_SCRAPER:
        try:
            print("Mencoba scraping menggunakan Selenium TE_Scraper...")
            price_raw, date_str = scrape_with_selenium(url)
        except Exception as sel_err:
            print(f"Gagal via Selenium: {sel_err}")

    if not price_raw or price_raw == "N/A":
        print("Gagal menemukan harga Coal dari halaman Trading Economics.")
        return

    # Bersihkan harga (hilangkan koma dan karakter non-angka)
    clean_price = re.sub(r'[^\d,.]', '', price_raw).replace(',', '')
    
    print(f"Found Coal data: Price={clean_price}, Date={date_str or today_date}")

    # Kirim ke API
    result = send_to_api(
        material_name=material_name,
        material_type=material_type,
        material_price=clean_price,
        material_unit=material_unit,
        material_currency=material_currency,
        price_date=today_date,
        source=url
    )
    print(f"API Result: {result}")

if __name__ == "__main__":
    main()
