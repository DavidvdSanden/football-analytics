import subprocess
import time
import os
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCREENSHOT_DIR = PROJECT_ROOT / "artifacts" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

def run_streamlit():
    # Start Streamlit in the background
    print('Starting Streamlit...')
    streamlit_exe = PROJECT_ROOT / '.venv' / 'Scripts' / 'streamlit.exe'
    cmd = [str(streamlit_exe), 'run', 'apps/streamlit/Home.py', '--server.headless', 'true']
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=PROJECT_ROOT,
    )
    time.sleep(10)  # Wait for Streamlit to start up
    return process

def capture_screenshot():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f'Error starting Chrome: {e}')
        return

    try:
        url = 'http://localhost:8501/statsbomb-match-details'
        print(f'Navigating to {url}...')
        driver.get(url)
        
        # Wait for the main content to load
        WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'stApp'))
        )
        
        # Give it extra time for elements to render
        print('Waiting for page elements to render...')
        time.sleep(15)
        
        screenshot_path = SCREENSHOT_DIR / 'match_details_screenshot.png'
        driver.save_screenshot(screenshot_path)
        print(f'Screenshot saved to: {screenshot_path.resolve()}')
    except Exception as e:
        print(f'Error during screenshot capture: {e}')
    finally:
        driver.quit()

if __name__ == "__main__":
    streamlit_proc = run_streamlit()
    try:
        capture_screenshot()
    finally:
        print('Terminating Streamlit...')
        streamlit_proc.terminate()
