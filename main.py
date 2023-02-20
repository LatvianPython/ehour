import json
import time
import re
from collections import namedtuple

import keyring
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

import config


LoggedTime = namedtuple("LoggedTime", "day task hours comments")


def get_driver():
    options = Options()
    options.binary_location = config.firefox_install
    s = Service(config.gecko_path)
    return webdriver.Firefox(service=s, options=options)


def login(driver):
    elem = driver.find_element(By.NAME, "username")
    elem.send_keys(config.username)

    elem = driver.find_element(By.NAME, "password")
    elem.send_keys(keyring.get_password("domain", config.username))
    elem.send_keys(Keys.RETURN)


def wait_until(driver, by, value):
    return WebDriverWait(driver, 10).until(ec.presence_of_element_located((by, value)))


def open_calendar_first_week(driver):
    elem = wait_until(driver, By.CLASS_NAME, "CalendarWeek")
    elem.click()


def check_exists_tasks(driver, project):
    for project_div in driver.find_elements(
        By.CSS_SELECTOR, 'td[class="project"] > span > div'
    ):
        if project_div.text == project:
            return True
    return False


def add_task(driver, task):
    elem = driver.find_element(By.CSS_SELECTOR, "select[id^=inactiveProject]")
    elem.click()

    for option in driver.find_elements(By.CSS_SELECTOR, "tr>td>select>option"):
        if option.text == config.project:
            option.click()
            found_project = True
            break
    else:
        found_project = False

    for option in driver.find_elements(By.CSS_SELECTOR, "tr>td>select>option"):
        if option.text == task:
            option.click()
            found_task = True
            break
    else:
        found_task = False

    if found_task and found_project:
        elem = driver.find_element(By.CSS_SELECTOR, "a[id^=addButton]")
        elem.click()


def get_current_weekdays(driver):
    wait_until(driver, By.CLASS_NAME, "weekColumnRow")
    time.sleep(1)
    elem = wait_until(driver, By.CLASS_NAME, "weekColumnRow")

    return [int(day.strip()) for day in re.findall(r"\n\d+? ", elem.text)]


def get_current_tasks(driver):
    return [
        task.text
        for task in driver.find_elements(By.CSS_SELECTOR, "td[class=project]")
        if task.text.strip()
    ]


def go_next_week(driver):
    elem = driver.find_element(By.CSS_SELECTOR, 'a[id^="nextWeek"]')
    elem.click()


def open_day(driver, day, task):
    days = driver.find_elements(By.CSS_SELECTOR, "input[id^=day]")
    to_open = days[day + task * 7]
    to_open.click()


def add_worklog(driver, hours, comments):
    elem = driver.find_element(By.CSS_SELECTOR, "input[id^=hours]")
    elem.send_keys(hours)

    elem = driver.find_element(By.CSS_SELECTOR, "textarea[id^=comment]")
    elem.send_keys(comments)

    elem = driver.find_element(By.CSS_SELECTOR, "a[id^=submit]")
    elem.click()


def check_already_logged(driver, day):
    elem = driver.find_elements(
        By.CSS_SELECTOR, 'tr[class="totalRow"] > td[id^="day"]'
    )[day]
    return elem.text == "8,00"


def main():
    data = get_data("data")

    driver = get_driver()

    driver.get(config.ehour_url)

    login(driver)

    open_calendar_first_week(driver)

    for row in data:
        (day, task, hours, comments) = row

        weekdays = get_current_weekdays(driver)
        if day not in weekdays:
            go_next_week(driver)

            weekdays = get_current_weekdays(driver)
            if day not in weekdays:
                raise RuntimeError(f"Can't find desired day {day}")

        tasks = get_current_tasks(driver)
        if task not in tasks:
            add_task(driver, task)

            tasks = get_current_tasks(driver)
            if task not in tasks:
                raise RuntimeError(f"Project {config.project} @ {task} not found")

        day_index, task_index = weekdays.index(day), tasks.index(task)

        if check_already_logged(driver, day_index):
            continue

        open_day(driver, day_index, task_index)
        add_worklog(driver, hours, comments)

    time.sleep(100)
    driver.close()


def get_data(file_name):
    with open(file_name, mode="r", encoding="utf8") as file:
        return [LoggedTime(*row.values()) for row in json.loads(file.read())]


def create_test_data(file_name):
    data = [
        {"day": 1, "task": "Development", "hours": 1, "comments": "task 1"},
        {"day": 1, "task": "Development", "hours": 2, "comments": "task 2"},
        {"day": 1, "task": "Maintenance", "hours": 1, "comments": "task 3"},
        {"day": 2, "task": "Development", "hours": 1, "comments": "task 4"},
        {"day": 6, "task": "Maintenance", "hours": 1, "comments": "task 5"},
    ]
    with open(file_name, mode="w", encoding="utf8") as file:
        file.write(json.dumps(data, indent=4))


if __name__ == "__main__":
    # create_test_data("data")
    main()
