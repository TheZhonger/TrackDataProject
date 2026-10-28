from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from io import BytesIO
from PIL import Image
#import html5lib
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

#df = pd.read_csv('milesplit data/5K.csv')


"""state = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL",
         "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
         "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
         "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
         "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI",
         "WY"]"""

#state = ['NY']
gender = ['m', 'f']
"""year = ['2000','2001','2002','2003','2004','2005','2006','2007',
        '2008','2009','2010','2011','2012','2013','2014','2015','2016']"""

#year = ['2024']
page = ['1','2','3','4','5','6','7','8','9','10',
        '11','12','13','14','15','16','17','18','19','20']
event = [1600]

#url = "http://" + state[0] + ".milesplit.com/rankings/pro/high-school-boys/outdoor-track-and-filed/" + event[1] + year[0] + "&accuracy=fat"
url = 'https://www.athletic.net/TrackAndField/rankings/list/169804/m/1600m?restrict=true&wind=2'


#for ge in gender:
    #for st in state:
    #for yr in year:
for pg in range(1, 46):
    url = "http://" + "www.athletic.net/TrackAndField/rankings/list/169804/" + ge + event + '?restrict=true&wind=2' + "&page=" + pg
    driver.get(url)
    time.sleep(1)  #wait until whole table loads, or, pretend I'm not a robot
    content = driver.page_source  # 'content' is raw HTML
    df_page = pd.read_html(content)[0]
print(df_page)

"""df = pd.DataFrame

df.columns = ['Rank', 'Time','Athlete/School','Grade','Meet','Year','State','Gender']
df['Time'] = df['Time'].fillna(0).astype(str)
df['Time'] = df['Time'].str.split(':').apply(lambda x: int(x[0]) * 60 + float(x[1][0:4]))
df['Grade'] = df['Grade'].fillna(0).astype(int)
df['Year'] = df['Year'].fillna(0).astype(int)

df.head()
"""