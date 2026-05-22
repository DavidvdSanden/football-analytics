from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCREENSHOT_DIR = PROJECT_ROOT / "artifacts" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--window-size=1920,1080')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
try:
    url = 'http://localhost:8501/statsbomb-match-details'
    print(f'Navigating to {url}...')
    driver.get(url)
    
    # Wait for the main content to load
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'stApp'))
    )
    
    # Give it extra time for graphs and tables to render (they might be slow)
    print('Waiting for page elements to render...')
    time.sleep(15)
    
    screenshot_path = SCREENSHOT_DIR / 'match_details_screenshot.png'
    driver.save_screenshot(screenshot_path)
    print(f'Screenshot saved to: {screenshot_path.resolve()}')
finally:
    driver.quit()
