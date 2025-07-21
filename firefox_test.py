from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
import time

print("Starting Firefox test...")

try:
    driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()))
    print("Navigating to Google.com...")
    driver.get("https://www.google.com")
    time.sleep(5)
    print("Test successful! Closing browser.")

except Exception as e:
    print(f"An error occurred during the Firefox test: {e}")

finally:
    if 'driver' in locals():
        driver.quit()