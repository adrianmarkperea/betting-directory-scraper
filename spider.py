import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import xlsxwriter
from datetime import date, timedelta
import threading
import time
import sys

class NapEntry : pass

class ParserThread(threading.Thread):
    def __init__(self, nap_element, current_date, browser, timeout):
        threading.Thread.__init__(self)
        self.nap_element = nap_element
        self.current_date = current_date
        self.browser = browser
        self.timeout = timeout
        self.new_nap_entry = ''
    def run(self):
        print('Starting thread')
        self.new_nap_entry = parse(self.nap_element, self.current_date, self.browser, self.timeout)
        print('thread finished')

def getNapsList(browser):
    return browser.find_elements_by_class_name('dog-list-item')

def extractNapInformation(nap_element, nap_entry):
    runner_name_element = nap_element.find_element_by_class_name('runner-name')
    runner_name = runner_name_element.text
    runner_profile_link = runner_name_element.get_attribute('href')

    nap_name_element = nap_element.find_element_by_class_name('nap-name')
    nap_source_element = nap_element.find_element_by_class_name('nap-source')
    nap_name = nap_name_element.text + ' {}'.format(nap_source_element.text)

    odds_element = nap_element.find_element_by_xpath('td[5]')
    odds = '"{}"'.format(odds_element.text)

    view_results_element = nap_element.find_element_by_class_name('nap-odds')
    results_link = view_results_element.get_attribute('href')

    nap_entry.runner_name = runner_name
    nap_entry.runner_profile_link = runner_profile_link
    nap_entry.nap_name = nap_name
    nap_entry.odds = odds
    nap_entry.results_link = results_link

def extractOwnerInformation(browser, nap_entry):
    player_info_element = browser.find_element_by_class_name('player-info')
    owner = player_info_element.find_element_by_xpath(
        '//div[@class=\'info-item\'][3]/div[1]/span[1]'
    ).text
    nap_entry.owner = owner

def extractResultsInformation(browser, nap_entry):
    race_time = ''
    race_track = ''
    race_type = ''
    num_runners = ''

    race_title_element = browser.find_element_by_xpath('//div[@class=\'ctleft\']')
    race_title_array = race_title_element.text.split()
    race_time = race_title_array[0]
    del race_title_array[0]
    race_track = ' '.join(race_title_array).split(':')[0]

    race_type_element = browser.find_element_by_xpath('//div[@class=\'card-info\']/table/tbody/tr[2]/td[2]')
    race_type = race_type_element.text

    num_runners_element = browser.find_element_by_xpath('//div[@class=\'card-info\']/table/tbody/tr[3]/td[4]')
    num_runners = num_runners_element.text

    nap_entry.race_time = race_time if race_time != '' else 'UNDEFINED'
    nap_entry.race_track = race_track if race_track != '' else 'UNDEFINED'
    nap_entry.race_type = race_type if race_type != '' else 'UNDEFINED'
    nap_entry.num_runners = num_runners if num_runners != '' else 'UNDEFINED'

    racecard_table_element = browser.find_element_by_class_name('racecard-table')
    racecard_entry_elements = racecard_table_element.find_elements_by_xpath('tbody/tr')

    other_runners = []
    other_trainers = []
    other_jockeys = []

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

        if runner_name == nap_entry.runner_name:
            nap_entry.jockey_name = jockey_name
            nap_entry.trainer_name = trainer_name
            continue

        other_runners.append(runner_name)
        other_trainers.append(trainer_name)
        other_jockeys.append(jockey_name)

    nap_entry.other_runners = other_runners
    nap_entry.other_trainers = other_trainers
    nap_entry.other_jockeys = other_jockeys

def parse(nap_element, current_date, browser, timeout):
    new_nap_entry = NapEntry()

    new_nap_entry.date = '{}/{}/{}'.format(current_date.day,
        current_date.month, current_date.year)

    print('Extracting nap information...')
    extractNapInformation(nap_element, new_nap_entry)
    print('Nap information extracted')

    print('Opening nap owner info at [{}]...'.format(new_nap_entry.runner_profile_link))

    try:
        browser.get(new_nap_entry.runner_profile_link)
        WebDriverWait(browser, timeout).until(
            EC.visibility_of_element_located((By.CLASS_NAME, 'player-info'))
        )

        print('Nap owner info opened')
        print('Extracting nap owner information...')
        extractOwnerInformation(browser, new_nap_entry)
        print('Nap owner information extracted')

    except TimeoutException:
        print('[{}] cannot be found!'.format(
            new_nap_entry.runner_profile_link)
        )
        new_nap_entry.owner = 'UNDEFINED'

    print('Opening results at [{}]...'.format(new_nap_entry.results_link))
    try:
        browser.get(new_nap_entry.results_link)
        WebDriverWait(browser, timeout).until(
            EC.visibility_of_element_located(
                (By.CLASS_NAME, 'racecard-table')
            )
        )
        print('Results opened')

        print('Extracting results information...')
        extractResultsInformation(browser, new_nap_entry)
        print('Results extracted')

    except TimeoutException:
        print('[{}] cannot be found!'.format(
            new_nap_entry.runner_profile_link)
        )
        nap_entry.race_time = 'UNDEFINED'
        nap_entry.race_track = 'UNDEFINED'
        nap_entry.race_type = 'UNDEFINED'
        nap_entry.num_runners = 'UNDEFINED'

    return new_nap_entry

def scrape(url, main_browser, sub_browsers, current_date, timeout = 5):

    try:
        main_browser.get(url)
        WebDriverWait(main_browser, timeout).until(
            EC.visibility_of_element_located((By.CLASS_NAME, 'naps-list-contain'))
        )
    except TimeoutException:
        print('Timed out waiting for page to load')
        return None

    nap_elements = getNapsList(main_browser)

    nap_entries = []
    i = 0
    while i < len(nap_elements):
        threads = []
        count = 0
        while count < len(sub_browsers):
            nap_element = nap_elements[i]
            t = ParserThread(nap_element, current_date, sub_browsers[count], timeout)
            t.start()
            threads.append(t)
            count += 1
            i += 1
            if i == len(nap_elements):
                break
            time.sleep(1)
        for t in threads:
            t.join()
        for t in threads:
            nap_entries.append(t.new_nap_entry)

    print('Finished extracting')

    return nap_entries

def write_entries(worksheet, row, entries_to_write, format):
    for entry in entries_to_write:
        worksheet.write(row, 0, entry.date, format)
        worksheet.write(row, 1, entry.runner_name, format)
        worksheet.write(row, 2, entry.nap_name, format)
        worksheet.write(row, 3, entry.race_track, format)
        worksheet.write(row, 4, entry.race_time, format)
        worksheet.write(row, 5, entry.owner, format)
        worksheet.write(row, 6, entry.jockey_name, format)
        worksheet.write(row, 7, entry.trainer_name, format)
        worksheet.write(row, 8, entry.odds, format)
        worksheet.write(row, 9, entry.race_type, format)
        worksheet.write(row, 10, entry.num_runners, format)
        column = 11
        for runner in entry.other_runners:
            worksheet.write(row, column, runner, format)
            column += 1
        column = 61
        for trainer in entry.other_trainers:
            worksheet.write(row, column, trainer, format)
            column += 1
        column = 111
        for jockey in entry.other_jockeys:
            worksheet.write(row, column, jockey, format)
            column += 1
        row += 1

def generate_url(current_date):
    date_array = current_date.strftime('%d %B %Y').split()
    day = date_array[0]
    month = date_array[1].lower()
    year = date_array[2]
    base_url = 'http://racing.betting-directory.com/'
    url = base_url + 'naps/{}th-{}-{}.php'.format(day, month, year)
    return url

if __name__ == '__main__':

    # init workbook
    workbook = xlsxwriter.Workbook('July 7 to December 2017.xlsx')
    # year-month-day
    start_date = date(2017, 7, 7)
    end_date = date(2017, 12, 31)
    # num browsers
    num_browsers = 8

    worksheet = workbook.add_worksheet()

    # define formats
    bold = workbook.add_format({'bold': True})
    nap_horse_and_race_format = workbook.add_format({'bold': True, 'bg_color': 'yellow'})
    other_horses_format = workbook.add_format({'bold': True, 'bg_color': 'green'})
    other_trainers_format = workbook.add_format({'bold': True, 'bg_color': 'blue'})
    other_jockeys_format = workbook.add_format({'bold': True, 'bg_color': 'red'})
    entry_format = workbook.add_format({'valign': 'vcenter'})

    # set column formatting
    worksheet.set_column(0, 10, 25)

    # write headers
    worksheet.merge_range('A1:K1', 'NAP HORSE & RACE', nap_horse_and_race_format)
    worksheet.write(1, 0, 'Date', nap_horse_and_race_format)
    worksheet.write(1, 1, 'Nap', nap_horse_and_race_format)
    worksheet.write(1, 2, 'Tipster', nap_horse_and_race_format)
    worksheet.write(1, 3, 'Race Track', nap_horse_and_race_format)
    worksheet.write(1, 4, 'Race Time', nap_horse_and_race_format)
    worksheet.write(1, 5, 'Owner', nap_horse_and_race_format)
    worksheet.write(1, 6, 'Trainer', nap_horse_and_race_format)
    worksheet.write(1, 7, 'Jockey', nap_horse_and_race_format)
    worksheet.write(1, 8, 'SP', nap_horse_and_race_format)
    worksheet.write(1, 9, 'Race Type', nap_horse_and_race_format)
    worksheet.write(1, 10, 'Runners', nap_horse_and_race_format)

    worksheet.merge_range('L1:BI2', 'Other Horses', other_horses_format)
    worksheet.merge_range('BJ1:DG2', 'Other Trainers', other_trainers_format)
    worksheet.merge_range('DH1:FE2', 'Other Jockeys', other_jockeys_format)

    row = 2

    chrome_path = os.path.dirname(os.path.realpath(__file__)) + '/chromedriver_win32/chromedriver.exe'
    chrome_options = webdriver.ChromeOptions()
    chrome_prefs = {}
    chrome_options.experimental_options["prefs"] = chrome_prefs
    chrome_prefs["profile.default_content_settings"] = {"images": 2}
    chrome_options.add_argument('-incognito')
    chrome_options.add_argument("--window-size=200,200")

    main_browser = webdriver.Chrome(executable_path=chrome_path, chrome_options=chrome_options)
    sub_browsers = [webdriver.Chrome(executable_path=chrome_path, chrome_options=chrome_options) for i in range(num_browsers)]

    delta = end_date - start_date
    skipped_dates = []

    for i in range(delta.days + 1):
        current_date = start_date + timedelta(days=i)
        url = generate_url(current_date)
        print('Scraping: {}'.format(url))
        try:
            entries_to_write = scrape(url, main_browser, sub_browsers, current_date, timeout = 20)
        except KeyboardInterrupt:
            workbook.close()
            main_browser.quit()
            for sb in sub_browsers:
                sb.quit()
            sys.exit('Program Interrupted. Closing.')
        except:
            print('Error SCRAPING at: {}. Skipping.'.format(current_date))
            skipped_dates.append(current_date)
            continue

        if entries_to_write is not None:
            try:
                write_entries(worksheet, row, entries_to_write, entry_format)
            except:
                print('Error WRITING at: {}. Skipping'.format(current_date))
                skipped_dates.append(current_date)
                continue

            row += len(entries_to_write)

    workbook.close()

    logs_name = 'skipped_dates.txt'
    print('Printing skipped dates to {}'.format(logs_name))
    f = open(logs_name, 'w+')
    for date in skipped_dates:
        f.write('{}\r\n'.format(date))
    f.close()

    main_browser.quit()
    for sb in sub_browsers:
        sb.quit()
    print('Program finished')
