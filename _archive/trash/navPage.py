from seleniumbase import SB
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from io import BytesIO
from PIL import Image
import html5lib
import lxml
import numpy as np
import pandas as pd 
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.image as mpimg
import datetime as dt
import time
import os
import requests

def navigate(url):
    with SB(uc = True) as sb:
        sb.uc_open_with_reconnect(url, 2)
        sb.click("//button[@class='btn btn-primary btn-lg d-none d-sm-inline-block']")
        sb.type("//input[@placeholder='Enter Email']", "email")
        sb.type("//input[@placeholder='Enter Password']", "pwd")
        sb.click("//button[@type='submit']")
    # driver = webdriver.Chrome() #Chrome .exe needs to be in this directory
    # driver.get(url)
    # time.sleep(.5)
    # #driver.execute_script("window.scrollBy(0, 500
    # driver.find_element(By.CLASS_NAME, "btn-primary").click()
    # element = WebDriverWait(driver, 4).until(
    #     EC.presence_of_element_located((By.XPATH, "//button[@class='btn btn-primary btn-lg d-none d-sm-inline-block']"))
    # )
    # #click on login prompt on milesplit 
    # element.click()

    # #login
    # username = driver.find_element(By.XPATH, "//input[@placeholder='Enter Email']")
    # password = driver.find_element(By.XPATH, "//input[@placeholder='Enter Password']")
    # username.send_keys("deckedimpala741@gmail.com")   #actual username and password go here..
    # password.send_keys("abcd1234")
    # driver.find_element(By.XPATH, "//button[@type='submit']").click()
#     time.sleep(3)
#     timesList = []
#     try:
#         while driver.find_element(By.CLASS_NAME, ('next')):
#             time.sleep(2.5) #wait for page to load
#             timesList.extend([x.text for x in driver.find_elements(By.CLASS_NAME,'time  ') if '.' in x.text]) #scrape times data
#             driver.find_element(By.CLASS_NAME, ('next')).click()
#         timesList.extend([x.text for x in driver.find_elements(By.CLASS_NAME,'time  ') if '.' in x.text]) #scrape times data
#     finally:
#         return timesList
# #https://ny.milesplit.com/rankings/pro/high-school-boys/outdoor-track-and-field/800m?year=2025&accuracy=fat
url = 'https://www.athletic.net/TrackAndField/rankings/list/169804/m/1600m?restrict=true&wind=2'
navigate(url)
# if 'girls' in url:
#     try:
#         with open(f"data/USA/US{url[50-3:55-3] + url[80-3:85-3]}.txt", "w") as file:
#             for item in navigate(url):
#                 file.write(item + "\n")
#     except:
#         with open(f"data/USA/US{url[50-3:55-3] + url[80-3:84-3]}.txt", "w") as file:
#             for item in navigate(url):
#                 file.write(item + "\n")
# else:
#     try:
#         with open(f"data/USA/US{url[50-3:54-3] + url[79-3:84-3]}.txt", "w") as file:
#             for item in navigate(url):
#                 file.write(item + "\n")
#     except:
#         with open(f"data/USA/US{url[50-3:54-3] + url[79-3:83-3]}.txt", "w") as file:
#             for item in navigate(url):
#                 file.write(item + "\n")