import sys
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

# Add src to sys.path to prioritize local version
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from tedata.utils import send_to_api

def get_unit_abbreviation(unit_str):
    """Mengubah satuan lengkap menjadi singkatan."""
    unit_map = {
        'ton': 'T',
        'dmt': 'DMT',
        'kg': 'kg',
        'gr': 'g',
        'gram': 'g',
        'oz': 'OZ',
        'ounce': 'OZ',
        'troy ounce': 'OZ',
        'lb': 'LB',
        'pound': 'LB'
    }
    return unit_map.get(unit_str.lower(), unit_str)

def parse_commodity_column(text):
    """
    Memisahkan 'Batubara (USD/ton)' menjadi ('Batubara', 'USD', 'T')
    """
    # Regex untuk mengambil Nama, Currency, dan Unit
    match = re.search(r'^(.*?)\s*\((.*?)\/(.*?)\)$', text)
    if match:
        name = match.group(1).strip()
        currency = match.group(2).strip()
        raw_unit = match.group(3).strip()
        unit = get_unit_abbreviation(raw_unit)
        return name, currency, unit
    return text, "USD", "unit"

def main():
    url = "https://www.minerba.esdm.go.id/harga_acuan"
    today_date = datetime.now().strftime('%Y-%m-%d')
    print(f"Scraping Minerba data from {url}...")
    print(f"Using current date for insert: {today_date}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        
        if not table:
            print("Gagal menemukan tabel di halaman Minerba.")
            return

        rows = table.find_all('tr')[1:] # Lewati header
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 1:
                # Kolom 0: Komoditas (contoh: "Batubara (USD/ton)")
                raw_commodity = cols[0].get_text(strip=True)
                
                # Kolom terakhir (paling kanan): Harga terbaru
                raw_price = cols[-1].get_text(strip=True)
                
                # Parse Nama, Currency, Unit (dengan singkatan)
                mat_name, mat_curr, mat_unit = parse_commodity_column(raw_commodity)
                
                # Bersihkan harga (hapus koma/simbol lain)
                clean_price = re.sub(r'[^\d,.]', '', raw_price).replace(',', '')
                
                if mat_name and clean_price:
                    print(f"Sending JSON: {mat_name} | {clean_price} | {mat_unit} | {mat_curr} | {today_date}")
                    
                    # Kirim ke API
                    send_to_api(
                        material_name=mat_name,
                        material_type="Mineral",
                        material_price=clean_price,
                        material_unit=mat_unit,
                        material_currency=mat_curr,
                        price_date=today_date,
                        source=url
                    )
            
        print("Selesai memproses data Minerba.")

    except Exception as e:
        print(f"Terjadi kesalahan: {e}")

if __name__ == "__main__":
    main()
