
# Put your username and password here
username = "richard.akenhead@chelseafc.com"
password = "test"

# Select Team
selected_team = "Chelsea"

### Load packages
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager

from fake_useragent import UserAgent
from bs4 import BeautifulSoup

import pandas as pd
import time
from datetime import datetime

################## INITIALISE CHROME DRIVER
ua = UserAgent()
user_agent = ua.random
chrome_options = Options()
chrome_options.add_argument("--incognito")  # Open Chrome in incognito mode

driver_service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=driver_service, options=chrome_options)

driver.maximize_window()
webpage = 'https://v2.noisefeed.com/login'
driver.get(webpage)

######### 1. LOGIN DETAILS
username_field = driver.find_element(By.ID, 'username')
password_field = driver.find_element(By.ID, 'password')

username_field.send_keys(username)
password_field.send_keys(password)

print('Username and password fields populated.')

login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in')]")
login_button.click()
time.sleep(5)
print("Logged into website")


######## 1.5 LOOP THROUGH ALL TEAMS (For new code to scrape all teams)

driver.get("https://v2.noisefeed.com/explore/cp_8/competition_injuries")
time.sleep(2)

teams_div = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "div.sc-carGAA.dpbdIG")))

team_a_tags = teams_div.find_elements(By.TAG_NAME, 'a')
teams_dict = {}

for tag in team_a_tags:
    team_name = tag.find_element(By.CSS_SELECTOR, 'div.sc-ciSmjq.fHUEUz').text
    team_href = tag.get_attribute('href')
    teams_dict[team_name] = team_href
    
for team in teams_dict.keys():
    teams_dict[team] += "/roster"

team_urls_list = list(teams_dict.values())
team_df = pd.DataFrame(list(teams_dict.items()), columns=['Team', 'Roster URL'])

####### 2.  ADD TEAM TO SEARCH BAR

driver.get("https://v2.noisefeed.com/search")
time.sleep(2)
search_input = driver.find_element(By.CSS_SELECTOR, 'input[type="search"]')
search_input.send_keys(selected_team)
submit_button = driver.find_element(By.CSS_SELECTOR, '.MainSearch__Submit-sc-5xzt58-5')
submit_button.click()
time.sleep(5)

####### 3. ROSTER PAGE - MAKE ROSTER TABLE AND GET LIST OF PLAYER NAMES

element = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.SearchResults__Result-sc-15bvwkv-3.kwWNPx')))

element.click()
time.sleep(10)

all_rows_data = []
headers = [
    "Player","Position","Matches Played","Matches On Bench","Matches Injured",
    "Minutes Played","Goals","Yellow / Red Cards","Match Sharpness"
]

table = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CLASS_NAME, "sc-gIvpCV"))
)
time.sleep(2)
html_content = table.get_attribute('outerHTML')
soup = BeautifulSoup(html_content, 'html.parser')
rows = soup.find_all('tr')

for row in rows:
    cells = row.find_all('td')
    row_data = [cell.text.strip() for cell in cells if cell.text.strip() != '']
    if row_data:
        all_rows_data.append(row_data)

roster_table = pd.DataFrame(all_rows_data, columns=headers)
print(roster_table)

player_names = roster_table.iloc[:, 0].tolist()

div_xpath = "//div[@class='sc-carGAA dpbdIG']"
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, div_xpath)))

player_links = driver.find_elements(By.XPATH, f"{div_xpath}//a")
player_ids = [link.get_attribute('id') for link in player_links]

url_template = "https://v2.noisefeed.com/explore/{}/injuries"
player_urls = [url_template.format(player_id) for player_id in player_ids]

###### 4. Now loop through all players!

all_data = pd.DataFrame()

for url in player_urls:
    data = []
    try:
        driver.get(url)
        time.sleep(2)
        
        print("Current URL:", driver.current_url)
        player_name_element = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.sc-iwaifL.gSkynp > span')))

        player_name = player_name_element.text
        print("Player's Name:", player_name)
        
        table_element = WebDriverWait(driver, 2).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "table.sc-gIvpCV.ioymRU")))
        html_content = table_element.get_attribute('outerHTML')
        soup = BeautifulSoup(html_content, 'html.parser')
        headers = [th.text for th in soup.find_all('th')][1:]
        headers.insert(0, 'Player Name')

        for row in soup.find_all('tr')[1:]:
            cols = row.find_all('td')
            row_data = [col.text.strip() for col in cols][1:]
            row_data.insert(0, player_name)
            data.append(row_data)
    
    except TimeoutException:
        print(f"{player_name} has not been injured")
        headers = ['Player Name', 'Injury', 'Body part', 'Side', 'Contact', 'Injured', 'Return', 'Recovery (days)', 'Missed matches']
        data = [[player_name] + ["No Injuries"] * (len(headers) - 1)]

    df = pd.DataFrame(data, columns=headers)
    print(df)
    all_data = pd.concat([all_data, df], ignore_index=True)
     
#### 5. Tidy up tables, save to csv

print("Player injury scrape finished")
now = datetime.now()
date_time_str = now.strftime("%d-%m-%Y %H:%M:%S")

# Add the 'Scrape Date' and 'Team' columns to the DataFrame
all_data.insert(0, 'Scrape Date', date_time_str)
all_data.insert(1, 'Team', selected_team)

all_data.to_csv("all_injury_data.csv", index = False, encoding='utf-16')
roster_table.to_csv('roster_table.csv', index=False, encoding='utf-16')
team_df.to_csv('teams_urls.csv', index=False, encoding='utf-16')

driver.quit()



