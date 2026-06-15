import subprocess
import os
import sys

# Tambahkan src ke path agar script yang dipanggil bisa menemukan module
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

scripts = [
    'scrape_rubber.py',
    'scrape_synthetic_rubber.py',
    'scrape_hrc_steel.py',
    'scrape_minerba.py',
    'scrape_carbon_black.py',
    'scrape_sulphur.py',
    'scrape_drewry.py'
]

def run_all():
    print("--- Starting All Scrapers ---")
    for script in scripts:
        print(f"\n>> Running: {script}")
        try:
            # Jalankan script menggunakan interpreter python yang sama
            result = subprocess.run([sys.executable, script], capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(f"Errors in {script}:\n{result.stderr}")
        except Exception as e:
            print(f"Failed to run {script}: {e}")
    print("\n--- All Scrapers Finished ---")

if __name__ == "__main__":
    run_all()
