
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

search_input.send_keys(selected_team)   #*****************************

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
        player_name_elements = WebDriverWait(driver, 3).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.sc-iwaifL.gSkynp > span'))
        )
        player_name = player_name_elements[0].text if player_name_elements else "Unknown Player"
        print("Player's Name:", player_name)

        role = preferred_foot = body = born = "No info"

        try:
            role = driver.find_element(By.XPATH, "//div[contains(text(), 'Role')]/following-sibling::div").text
        except NoSuchElementException:
            print("Role info not found for", player_name)

        try:
            preferred_foot = driver.find_element(By.XPATH, "//div[contains(text(), 'Preferred foot')]/following-sibling::div").text
        except NoSuchElementException:
            print("Preferred foot info not found for", player_name)

        try:
            body = driver.find_element(By.XPATH, "//div[contains(text(), 'Body')]/following-sibling::div").text
        except NoSuchElementException:
            print("Body info not found for", player_name)

        try:
            born = driver.find_element(By.XPATH, "//div[contains(text(), 'Born')]/following-sibling::div").text
        except NoSuchElementException:
            print("Born info not found for", player_name)
        
        table_element = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.sc-gIvpCV.ioymRU"))
        )
        html_content = table_element.get_attribute('outerHTML')
        soup = BeautifulSoup(html_content, 'html.parser')
        
        headers = [th.text.strip() for th in soup.find_all('th')]
        headers.extend(['Role', 'Preferred Foot', 'Body', 'Born'])  # Extend headers with new attributes
        headers.insert(0, 'Player Name')  # Ensure Player Name is first
        
        for row in soup.find_all('tr')[1:]:
            cols = row.find_all('td')
            row_data = []
            for col in cols:
                text_content = ''
                for element in col.find_all(['span', 'div', 'a']):
                    text_content += element.text.strip() + ' | '
                text_content = text_content.rstrip(' |')
                if not text_content:
                    text_content = col.text.strip()
                row_data.append(text_content)
            row_data.extend([role, preferred_foot, body, born])  # Add new attributes to each row
            row_data.insert(0, player_name)
            data.append(row_data)
    
    except TimeoutException:
        print(f"{player_name} has not been injured")

# Define headers, including the additional information columns
        headers = ['Player Name', 'Injury', 'Body part', 'Side', 'Contact', 'Injured', 'Return', 'Recovery (days)', 'Missed matches', 'Role', 'Preferred Foot', 'Body', 'Born']

        
        data = [[player_name] + ["No injuries"] * 8 + [role, preferred_foot, body, born]]

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

all_data = all_data.loc[:, all_data.columns != ''] 

all_data['Body'] = all_data['Body'].apply(lambda x: "No info / No info" if x == "No info" else x)
all_data[['Height', 'Weight']] = all_data['Body'].str.split(' /', expand=True)
all_data['Height'] = all_data['Height'].str.replace('cm', '').str.strip()
all_data['Weight'] = all_data['Weight'].str.replace('kg', '').str.strip()
all_data['Weight'] = all_data['Weight'].fillna("No info")

all_data.drop('Body', axis=1, inplace=True)

all_data.to_csv("all_injury_data.csv", index = False, encoding='utf-16')
roster_table.to_csv('roster_table.csv', index=False, encoding='utf-16')
team_df.to_csv('teams_urls.csv', index=False, encoding='utf-16')

driver.quit()



