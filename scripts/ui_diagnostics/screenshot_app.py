import subprocess
import time
import os
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCREENSHOT_DIR = PROJECT_ROOT / "artifacts" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("Starting Streamlit...")
    port = 8501
    streamlit_cmd = [
        sys.executable,
        '-m',
        'streamlit',
        'run',
        'apps/streamlit/Home.py',
        '--server.port',
        str(port),
        '--server.headless',
        'true',
    ]
    streamlit_process = subprocess.Popen(
        streamlit_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=PROJECT_ROOT,
    )
    
    time.sleep(15)
    
    try:
        print("Setting up Selenium...")
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.binary_location = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        url = 'http://localhost:' + str(port) + '/Match_Details'
        print('Navigating to ' + url + '...')
        driver.get(url)
        
        time.sleep(20)
        
        screenshot_path = SCREENSHOT_DIR / 'match_details_screenshot.png'
        driver.save_screenshot(screenshot_path)
        print('Screenshot saved to ' + str(screenshot_path.resolve()))
        print('Page title: ' + driver.title)
        
        driver.quit()
    except Exception as e:
        print('Error during Selenium execution: ' + str(e))
        import traceback
        traceback.print_exc()
    finally:
        streamlit_process.terminate()
        try:
            streamlit_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            streamlit_process.kill()
        print('Streamlit process terminated.')

if __name__ == '__main__':
    main()
