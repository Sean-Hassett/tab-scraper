import os
import re
import json
import requests
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.common.exceptions import NoSuchElementException
from configparser import ConfigParser


# TODO timeout download

SEARCH_URL = "https://www.ultimate-guitar.com/search.php?page={}&search_type=title&value={}"
RESULTS_PATTERN = "\"results\":(\[.*?\]),\"pagination\""
RESULTS_COUNT_PATTERN = "\"tabs\",\"results_count\":([0-9]+?),\"results\""


def search_tabs(search_string, types):
    page = 1
    # get first page of results
    response = requests.get(SEARCH_URL.format(page, search_string))
    # count is the number of results, used to know how many pages to search
    count = 0
    try:
        # isolate results from page using regex
        response_body = response.content.decode()
        results = re.search(RESULTS_PATTERN, response_body).group(1)
        count = int(re.search(RESULTS_COUNT_PATTERN, response_body).group(1))
    except AttributeError:
        results = ''
    response_data = json.loads(results)

    ret = []
    while count > 0:
        for item in response_data:
            try:
                # Get every result that has a desired type
                if item["type"] in types:
                    ret.append((item["type"], item["artist_name"], item["song_name"],
                                str(round(float(item["rating"]), 1)), str(item["votes"]),
                                item["tab_url"], str(item["version"])))
            except KeyError:
                # key error on "official" tabs, not interested in these tabs
                ''
            count -= 1
        if count > 0:
            page += 1
            response = requests.get(SEARCH_URL.format(page, search_string))
            try:
                # isolate results from page using regex
                response_body = response.content.decode()
                results = re.search(RESULTS_PATTERN, response_body).group(1)
            except AttributeError:
                results = ''
            response_data = json.loads(results)
    return ret


def download_tab(url, tab_type, artist, title, version):
    config = ConfigParser()
    config.read('settings.cfg')
    cfg = config['MAIN']

    gecko_path = cfg['gecko_path']

    # create destination directory if it doesn't exist
    destination_root = cfg['destination_root']
    destination = destination_root + tab_type + "/" + artist
    os.makedirs(destination, exist_ok=True)

    options = Options()
    options.headless = True

    driver = webdriver.Firefox(options=options, executable_path=gecko_path)
    driver.get(url)

    # clear the privacy policy message
    try:
        popup_btn = driver.find_element_by_xpath('//button[text()="Got it, thanks!"]')
        popup_btn.click()
    except NoSuchElementException:
        pass

    # clear the official tab ad
    try:
        popup_btn = driver.find_element_by_xpath('//div[contains(@class, "ai-ah")]//button')
        popup_btn.click()
    except NoSuchElementException:
        pass

    # hide the autoscroll tool
    autoscroller = driver.find_element_by_xpath('//span[text()="Autoscroll"]/parent::button/parent::div/parent::section')
    driver.execute_script("arguments[0].setAttribute('style', 'display: none')", autoscroller)

    tab = driver.find_element_by_tag_name("pre")
    filename = destination + "/" + title + " (Ver " + version + ")" + ".png"
    tab.screenshot(filename)


def download_file(url, tab_type, artist):
    config = ConfigParser()
    config.read('settings.cfg')
    cfg = config['MAIN']

    gecko_path = cfg['gecko_path']

    # create destination directory if it doesn't exist
    destination_root = cfg['destination_root']
    destination = destination_root + tab_type + "/" + artist
    os.makedirs(destination, exist_ok=True)

    options = Options()
    options.headless = True

    profile = FirefoxProfile()
    profile.set_preference("browser.download.folderList", 2)
    profile.set_preference("browser.download.manager.showWhenStarting", False)
    profile.set_preference("browser.download.dir", destination)
    profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream")

    driver = webdriver.Firefox(options=options, firefox_profile=profile, executable_path=gecko_path)
    driver.get(url)
    button = driver.find_element_by_xpath('//button/span[text()="DOWNLOAD Guitar Pro TAB" '
                                          'or text()="DOWNLOAD Power TAB"]')
    driver.execute_script("arguments[0].click();", button)
    # driver.quit()
