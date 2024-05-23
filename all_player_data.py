
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import pandas as pd
import time

# Chrome driver
chrome_options = Options()
chrome_options.add_argument("--incognito")  # Open Chrome in incognito mode
driver_service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=driver_service, options=chrome_options)
driver.maximize_window()

# Function to login to the website
def login(username, password):
    webpage = 'https://v2.noisefeed.com/login'
    driver.get(webpage)
    username_field = driver.find_element(By.ID, 'username')
    password_field = driver.find_element(By.ID, 'password')
    username_field.send_keys(username)
    password_field.send_keys(password)
    login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in')]")
    login_button.click()
    time.sleep(5)  # Wait for login to complete

# Login and navigate
print("Logging in")
login('Richard.Akenhead@chelseafc.com', 'test')
print("Logged in !")
driver.get("https://v2.noisefeed.com/explore/cp_8/competition_injuries")
time.sleep(2)
print("Getting all team URLs")

################# Collect all Roster Data and player URLs
teams_div = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "div.sc-carGAA.dpbdIG")))
team_a_tags = teams_div.find_elements(By.TAG_NAME, 'a')
teams_dict = {tag.find_element(By.CSS_SELECTOR, 'div.sc-ciSmjq.fHUEUz').text: tag.get_attribute('href') for tag in team_a_tags}

print("Got all team URLS !")

team_rosters = {}
team_player_urls = {}

print("Getting all player URLs and roster data now....")
for team_name, team_url in teams_dict.items():
    driver.get(team_url + "/roster")
    time.sleep(3)

    # Get the roster table
    headers = ["Player", "Position", "Matches Played", "Matches On Bench", "Matches Injured",
               "Minutes Played", "Goals", "Yellow / Red Cards", "Match Sharpness"]

    table = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "sc-gIvpCV"))
    )
    html_content = table.get_attribute('outerHTML')
    soup = BeautifulSoup(html_content, 'html.parser')
    rows = soup.find_all('tr')

    all_rows_data = []
    for row in rows:
        cells = row.find_all('td')
        row_data = [cell.text.strip() for cell in cells if cell.text.strip() != '']
        if row_data:
            all_rows_data.append(row_data)

    roster_table = pd.DataFrame(all_rows_data, columns=headers)
    team_rosters[team_name] = roster_table
    print(f"Roster for {team_name} collected.")

    # Collect player URLs for each team
    div_xpath = "//div[@class='sc-carGAA dpbdIG']"
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, div_xpath)))
    player_links = driver.find_elements(By.XPATH, f"{div_xpath}//a")
    player_ids = [link.get_attribute('id') for link in player_links]
    url_template = "https://v2.noisefeed.com/explore/{}/injuries"
    player_urls = [url_template.format(player_id) for player_id in player_ids]
    team_player_urls[team_name] = player_urls


all_rosters = pd.concat(team_rosters, names=['Team', 'Index']).reset_index(level='Team')
all_rosters = all_rosters.reset_index(drop=True)
all_rosters.to_csv("all_rosters.csv")

############################################################################

all_player_data = []

# Loop through each team and their player URLs
for team_name, urls in team_player_urls.items():
    for url in urls:
        try:
            driver.get(url)
            print("Current URL:", driver.current_url)

            player_name_element = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.sc-iwaifL.gSkynp > span')))
            player_name = player_name_element.text
            print("Player's Name:", player_name)

            table_element = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.sc-gIvpCV.ioymRU")))
            html_content = table_element.get_attribute('outerHTML')
            soup = BeautifulSoup(html_content, 'html.parser')
            headers = [th.text for th in soup.find_all('th')][1:]
            headers = ['Team Name'] + headers
            headers.insert(1, 'Player Name')

            for row in soup.find_all('tr')[1:]:
                cols = row.find_all('td')
                row_data = [col.text.strip() for col in cols][1:]
                row_data = [team_name, player_name] + row_data
                all_player_data.append(dict(zip(headers, row_data)))

        except TimeoutException:
            print(f"{player_name} has not been injured")
            headers = ['Team Name', 'Player Name', 'Injury', 'Body part', 'Side', 'Contact', 'Injured', 'Return', 'Recovery (days)', 'Missed matches']
            
            data = dict(zip(headers, [team_name, player_name] + ["No Injuries"] * (len(headers) - 2)))
            all_player_data.append(data)


final_player_data_df = pd.DataFrame(all_player_data)
final_player_data_df.to_csv("all_player_injury_data.csv", encoding= "utf-16", index= "FALSE")

driver.quit()

########### Analysis

thigh_df = final_player_data_df[
    (final_player_data_df['Injury'] == "Muscle | Tendon") &
    (final_player_data_df['Contact'] == "Indirect") &
    (final_player_data_df['Body part'] == "Thigh")
]
