#https://www.dukascopy.com/swiss/english/fx-market-tools/charts/
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Initialize the Chrome browser using WebDriver manager
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # Run in headless mode (no browser UI)
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Open the web page that contains the JavaScript application
url = 'https://www.dukascopy.com/swiss/english/fx-market-tools/charts/'  # Replace with your actual URL
driver.get(url)

# Wait for the specific div to load (with a maximum wait time of 10 seconds)
try:
    iframe = driver.find_element(By.XPATH, '//iframe')  # Locate the iframe (replace with correct locator)
    driver.switch_to.frame(iframe)

    # Initialize previous data as an empty string
    prev_data = ""
    element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//strong[contains(text(), "EUR/USD, 1M, BID")]/span'))
    )
    print("Page loaded")

    element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'a-W-sh-gb'))
    )
    element.click()
    print("Clicked on dropdown")

    print(driver.page_source)

    # element = WebDriverWait(driver, 10).until(
    #     EC.presence_of_element_located((By.XPATH, '//span[contains(@class, "a-W-Mh-Nh-Kg-Ph-Sh-U") and contains(text(), "USA500.IDX/USD")]'))
    # )
    # print("USA500IDX Selected!")

    driver.quit()

    # Infinite loop to continuously check for updates
    while True:
        # Try to locate the element inside the iframe
        #element = driver.find_element(By.XPATH, '//strong[contains(text(), "EUR/USD, 1M, BID")]/span')
        
        # Get the text content of the div
        current_data = element.text

        # Print data only if it has changed since the last check
        if current_data != prev_data:
            print(current_data)
            prev_data = current_data  # Update the previous data to the current

        time.sleep(0.5)

except Exception as e:
    print(f"An error occurred: {e}")
