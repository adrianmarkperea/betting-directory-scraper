import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class NapEntry : pass

def getNapsList(browser):
    return browser.find_elements_by_class_name('dog-list-item')

def extractNapInformation(nap_element, nap_entry):
    runner_name_element = nap_element.find_element_by_class_name('runner-name')
    runner_name = runner_name_element.text
    runner_profile_link = runner_name_element.get_attribute('href')

    nap_name_element = nap_element.find_element_by_class_name('nap-name')
    nap_name = nap_name_element.text

    result_element = nap_element.find_element_by_xpath('td[4]')
    result = result_element.text

    odds_element = nap_element.find_element_by_xpath('td[5]')
    odds = odds_element.text

    view_results_element = nap_element.find_element_by_class_name('nap-odds')
    results_link = view_results_element.get_attribute('href')

    nap_entry.runner_name = runner_name
    nap_entry.runner_profile_link = runner_profile_link
    nap_entry.result = result
    nap_entry.odds = odds
    nap_entry.results_link = results_link

def extractOwnerInformation(browser, nap_entry):
    player_info_element = browser.find_element_by_class_name('player-info')
    owner = player_info_element.find_element_by_xpath(
        '//div[@class=\'info-item\'][3]/div[1]/span[1]'
    ).text
    nap_entry.owner = owner

def extractResultsInformation(browser, nap_entry):
    racecard_table_element = browser.find_element_by_class_name('racecard-table')
    racecard_entry_elements = racecard_table_element.find_elements_by_xpath('tbody/tr')

    racecard_entries = []
    for racecard_entry_element in racecard_entry_elements:
        runner_name = racecard_entry_element.find_element_by_xpath(
            'td[@class=\'normal-td td-runner\']/a'
        ).text
        jockey_name = racecard_entry_element.find_element_by_xpath(
            'td[@class=\'normal-td td-runner\']/div[@class=\'small-grey-text\']'
        ).text.replace('(', '').replace(')', '')
        trainer_name = racecard_entry_element.find_element_by_xpath(
            'td[4]/div'
        ).text

        print('runner name: {}'.format(runner_name))
        print('jockey_name: {}'.format(jockey_name))
        print('tariner_name: {}'.format(trainer_name))

        racecard_entries.append({runner_name: runner_name,
                                 jockey_name: jockey_name,
                                 trainer_name: trainer_name})

        if runner_name == nap_entry.runner_name:
            nap_entry.jockey_name = jockey_name
            nap_entry.trainer_name = trainer_name

    nap_entry.racecard_entries = racecard_entries

def scrape(url, timeout = 5):
    options = webdriver.ChromeOptions()
    options.add_argument('-incognito')

    chrome_path = os.path.dirname(os.path.realpath(__file__)) + '/chromedriver_win32/chromedriver.exe'
    main_browser = webdriver.Chrome(executable_path=chrome_path, chrome_options=options)
    sub_browser = webdriver.Chrome(executable_path=chrome_path, chrome_options=options)

    main_browser.get(url)

    try:
        WebDriverWait(main_browser, timeout).until(
            EC.visibility_of_element_located((By.CLASS_NAME, 'naps-list-contain'))
        )
    except TimeoutException:
        print('Timed out waiting for page to load')
        main_browser.quit()

    nap_elements = getNapsList(main_browser)

    for nap_element in nap_elements:

        new_nap_entry = NapEntry()

        print('Extracting nap information...')
        extractNapInformation(nap_element, new_nap_entry)
        print('Nap information extracted')

        print('Opening nap owner info at [{}]...'.format(new_nap_entry.runner_profile_link))
        sub_browser.get(new_nap_entry.runner_profile_link)
        try:
            WebDriverWait(sub_browser, timeout).until(
                EC.visibility_of_element_located((By.CLASS_NAME, 'player-info'))
            )

            print('Nap owner info opened')
            print('Extracting nap owner information...')
            extractOwnerInformation(sub_browser, new_nap_entry)
            print('Nap owner information extracted')

        except TimeoutException:
            print('[{}] cannot be found!'.format(
                new_nap_entry.runner_profile_link)
            )

        print('Opening results at [{}]...'.format(new_nap_entry.results_link))
        sub_browser.get(new_nap_entry.results_link)
        try:
            WebDriverWait(sub_browser, timeout).until(
                EC.visibility_of_element_located(
                    (By.CLASS_NAME, 'racecard-table')
                )
            )
            print('Results opened')

            print('Extracting results information...')
            extractResultsInformation(sub_browser, new_nap_entry)
            print('Results extracted')

        except TimeoutException:
            print('[{}] cannot be found!'.format(
                new_nap_entry.runner_profile_link)
            )

    print('Finished extracting')
    main_browser.quit()
    sub_browser.quit()

if __name__ == '__main__':
    scrape('http://racing.betting-directory.com/naps/12th-may-2018.php')
