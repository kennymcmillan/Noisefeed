from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime

# Chrome driver setup
chrome_options = Options()
chrome_options.add_argument("--incognito")
chrome_options.add_experimental_option("prefs", {
    "profile.managed_default_content_settings.images": 2  # This line disables images.
})
driver_service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=driver_service, options=chrome_options)
driver.maximize_window()

def login(username, password):
    """Function to log in to the website."""
    driver.get('https://v2.noisefeed.com/login')
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'username'))).send_keys(username)
    driver.find_element(By.ID, 'password').send_keys(password)
    driver.find_element(By.XPATH, "//button[contains(text(), 'Log in')]").click()
    time.sleep(5)
            
def fetch_player_info(xpath):
    try:
        return driver.find_element(By.XPATH, xpath).text
    except NoSuchElementException:
        return "No info"

login('Richard.Akenhead@chelseafc.com', 'test')
print("Logged in!")

driver.get("https://v2.noisefeed.com/explore/cp_8/competition_injuries")
time.sleep(2)

# Collect all team URLs
teams_div = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.sc-carGAA.dpbdIG")))
team_links = {tag.find_element(By.CSS_SELECTOR, 'div.sc-ciSmjq.fHUEUz').text: tag.get_attribute('href') for tag in teams_div.find_elements(By.TAG_NAME, 'a')}

team_rosters = {}
team_player_urls = {}

for team_name, team_url in team_links.items():
    driver.get(team_url + "/roster")
    time.sleep(3)

    # Parse the roster table
    table_html = driver.execute_script('return document.querySelector(".sc-gIvpCV").outerHTML;')
    soup = BeautifulSoup(table_html, 'html.parser')
    roster_data = [[td.text.strip() for td in tr.find_all('td')] for tr in soup.find_all('tr') if tr.find('td')]
    roster_df = pd.DataFrame(roster_data, columns=["Player", "Position", "Matches Played", "Matches On Bench", "Matches Injured", "Minutes Played", "Goals", "Yellow / Red Cards", "Match Sharpness"])
    team_rosters[team_name] = roster_df
    print(f"Roster for {team_name} collected.")

    # Collect player URLs
    player_ids = [link.get_attribute('id') for link in driver.find_elements(By.XPATH, "//div[@class='sc-carGAA dpbdIG']//a")]
    player_urls = ["https://v2.noisefeed.com/explore/{}/injuries".format(pid) for pid in player_ids]
    team_player_urls[team_name] = player_urls
    
    
    #####################################################################################################################

total_players = sum(len(urls) for urls in team_player_urls.values())

# Initialize the counter
processed_players = 0

all_data = []

# Loop through each team and their player URLs
for team_name, urls in team_player_urls.items():
    for url in urls:
        processed_players += 1
        try:
            driver.get(url)
            time.sleep(2)
            print("Current URL:", driver.current_url)
            print(f"Processing player {processed_players} of {total_players}: {url}")

            # Check if any player information exists
            try:
                player_name_elements = WebDriverWait(driver, 3).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.sc-iwaifL.gSkynp > span'))
                )
                player_name = player_name_elements[0].text if player_name_elements else "Unknown Player"
            except TimeoutException:
                player_name = "Unknown Player"

            print(f"Player's Name: {player_name}")

            # Fetch player bio data once per player
            role = fetch_player_info("//div[contains(text(), 'Role')]/following-sibling::div")
            preferred_foot = fetch_player_info("//div[contains(text(), 'Preferred foot')]/following-sibling::div")
            body = fetch_player_info("//div[contains(text(), 'Body')]/following-sibling::div")
            born = fetch_player_info("//div[contains(text(), 'Born')]/following-sibling::div")

            # Fetch the injury table
            table_element = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.sc-gIvpCV.ioymRU"))
            )
            html_content = table_element.get_attribute('outerHTML')
            soup = BeautifulSoup(html_content, 'html.parser')
            headers = ['Team Name', 'Player Name'] + [th.text.strip() for th in soup.find_all('th')]
            headers += ['Role', 'Preferred Foot', 'Body', 'Born']

            rows = soup.find_all('tr')[1:]  # Skipping header row
            for row in rows:
                cols = [col.text.strip() for col in row.find_all('td')]
                data = [team_name, player_name] + cols + [role, preferred_foot, body, born]
                all_data.append(dict(zip(headers, data)))

        except TimeoutException:
            print(f"No injury data found for {player_name}")
            headers = ['Team Name', 'Player Name', 'Injury', 'Body part', 'Side', 'Contact', 'Injured', 'Return', 'Recovery (days)', 'Missed matches', 'Role', 'Preferred Foot', 'Body', 'Born']
            data = [team_name, player_name] + ["No data available"] * 8 + [role, preferred_foot, body, born]
            all_data.append(dict(zip(headers, data)))

# Convert list of dictionaries to DataFrame

all_data = pd.DataFrame(all_data)

#### Tidy up tables, save to csv

print("Player injury scrape finished")
now = datetime.now()
date_time_str = now.strftime("%d-%m-%Y %H:%M:%S")

# Add the 'Scrape Date' and 'Team' columns to the DataFrame
all_data.insert(0, 'Scrape Date', date_time_str)

all_data = all_data.loc[:, all_data.columns != ''] 

all_data['Body'] = all_data['Body'].apply(lambda x: "No info / No info" if x == "No info" else x)
all_data[['Height', 'Weight']] = all_data['Body'].str.split(' /', expand=True)
all_data['Height'] = all_data['Height'].str.replace('cm', '').str.strip()
all_data['Weight'] = all_data['Weight'].str.replace('kg', '').str.strip()
all_data['Weight'] = all_data['Weight'].fillna("No info")
all_data.drop('Body', axis=1, inplace=True)

all_data.to_csv("all_injury_data.csv", index = False, encoding='utf-16')


driver.quit()
