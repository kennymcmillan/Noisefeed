
########## Noisefeed Scrape for whole league and to get videos (set up for thigh injuries)

### cp_8 is for premiership

### This code - 1. Loops through MLS teams and gets roster info and saves in all_rosters.csv
###             2. Makes csv of all injuries for all players in MLS (in all_player_injury_data.csv)
###             3. Saves all videos of Thigh injuries into a folder
    
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.window import WindowTypes
import pandas as pd
import time
from bs4 import BeautifulSoup
import requests
import os

username = "Richard.Akenhead@chelseafc.com"
password = "test"

# Initialize the Chrome driver
chrome_options = Options()
chrome_options.add_argument("--incognito")
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
    time.sleep(5)

# Login and navigate
print("Logging in")
login(username,password)
print("Logged in !")
driver.get("https://v2.noisefeed.com/explore/cp_8/competition_injuries") #cp_8 is premiership
time.sleep(2)
print("Getting all team URLs")

################# Collect all Roster Data and player URLs ##############################################

teams_div = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "div.sc-carGAA.dpbdIG")))
team_a_tags = teams_div.find_elements(By.TAG_NAME, 'a')
teams_dict = {tag.find_element(By.CSS_SELECTOR, 'div.sc-ciSmjq.fHUEUz').text: tag.get_attribute('href') for tag in team_a_tags}

print("Got all team URLS !")

team_rosters = {}
team_player_urls = {}

print("Getting all player URLs and roster data now....")

for team_name, team_url in list(teams_dict.items()):
    driver.get(team_url + "/roster")
    time.sleep(3)

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

    # Collect player URLs for each team using the id in the a-tags
    div_xpath = "//div[@class='sc-carGAA dpbdIG']"
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, div_xpath)))
    player_links = driver.find_elements(By.XPATH, f"{div_xpath}//a")
    player_ids = [link.get_attribute('id') for link in player_links]
    
    url_template = "https://v2.noisefeed.com/explore/{}/injuries"
    player_urls = [url_template.format(player_id) for player_id in player_ids]
    team_player_urls[team_name] = player_urls

###################### Get all Player data and Video links ##########################

all_player_data = []

driver.execute_script("window.onbeforeunload = function() {};")  # Suppresses pop-up alerts

for team_name, urls in team_player_urls.items():
    for url in urls:
        driver.get(url)
        print("Current URL:", driver.current_url)

        try:
            player_name = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.sc-iwaifL.gSkynp > span'))).text
            print("Player's Name:", player_name)

            table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.sc-gIvpCV.ioymRU")))
            headers = [th.text for th in table.find_elements(By.TAG_NAME, 'th')[1:]] # Can make more robust ??
            headers = ['Team Name', 'Player URL', 'Player Name'] + headers + ['Video Link']

            rows = table.find_elements(By.CSS_SELECTOR, "tr")[1:]

            for row in rows:
                cols = [col.text.strip() for col in row.find_elements(By.TAG_NAME, 'td')[1:]]
                if len(cols) == len(headers) - 4:  
                    video_link = "No video link"  # Reset video link for each row *******

                    try:
                        svg_element = row.find_element(By.CSS_SELECTOR, "svg.injected-svg")
                        if svg_element:
                            svg_element.click()
                            time.sleep(2)
                            video_elements = driver.find_elements(By.TAG_NAME, 'video')
                            video_link = video_elements[0].get_attribute('src') if video_elements else "No video link"
                            close_button = WebDriverWait(driver, 5).until(
                                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.Dialog__Close-sc-16u2hyt-6.dsMjOs")))
                            close_button.click()
                            print(video_link)
                    except (NoSuchElementException, ElementClickInterceptedException):
                        print("No video. Moving on...")

                    data_row = [team_name, url, player_name] + cols + [video_link]
                    all_player_data.append(dict(zip(headers, data_row)))

        except TimeoutException:
            print(f"Timeout or data could not be retrieved for URL: {url}")

######################### Save all data to csv ####################################################

all_rosters = pd.concat(team_rosters, names=['Team', 'Index']).reset_index(level='Team')
all_rosters = all_rosters.reset_index(drop=True)
all_rosters.to_csv("all_rosters.csv")

final_player_data_df = pd.DataFrame(all_player_data)
final_player_data_df.to_csv("all_player_injury_data.csv", encoding="utf-16", index=False)

driver.quit()

################# MAKE FOLDER WITH ALL THIGH INJURY VIDEOS ####################################################

video_data = final_player_data_df[(final_player_data_df['Video Link'] != "No video link") & 
                                  (final_player_data_df['BODY PART'] == "Thigh")]

save_directory = "thigh_videos"
os.makedirs(save_directory, exist_ok=True)

# Iterate over each row in the filtered DataFrame
for index, row in video_data.iterrows():
    video_url = row['Video Link']
    player_name = row['Player Name'].replace(' ', '_')  # Replace spaces with underscores for filename compatibility
    team_name = row['Team Name'].replace(' ', '_')
    date_of_injury = row.get('INJURED', '').replace(' ', '_')
    body_part = row.get('BODY PART', '').replace(' ', '_')

    filename = f"{player_name}_{team_name}_{date_of_injury}_{body_part}.mpg"

    if video_url != "No video link":
        try:
            response = requests.get(video_url, stream=True)
            if response.status_code == 200:
                video_path = os.path.join(save_directory, filename)
                with open(video_path, 'wb') as f:
                    f.write(response.content)
                print(f"Downloaded video saved as: {video_path}")
            else:
                print(f"Failed to download video from {video_url}: Status code {response.status_code}")
        except requests.RequestException as e:
            print(f"Error downloading {video_url}: {e}")
    else:
        print(f"No valid video link for index {index + 1}.")

print("Video downloading process completed.")
