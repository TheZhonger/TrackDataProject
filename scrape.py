import random
from bs4 import BeautifulSoup
from seleniumbase import SB
import pandas as pd
import lxml
from lxml import etree

def parse_rankings(html):
    soup = BeautifulSoup(html, "lxml")
    rankingsDict = {
        "name": [],
        "time": [],
        "team": [],        
        "grade": [],
        "state": [],
        "date": [],
    }
    dom = etree.HTML(str(soup))
    for i in range(len(list(dom.xpath("/html[1]/body[1]/main[1]/anet-site-app[1]/shared-tf-rankings[1]/div[1]/div[1]/div[2]/div[2]/table[1]/tbody[2]//tr")))):
        try:
            if dom.xpath("/html[1]/body[1]/main[1]/anet-site-app[1]/shared-tf-rankings[1]/div[1]/div[1]/div[2]/div[2]/table[1]/tbody[2]/tr[" + str(i+1) + "]/td[5]/div[1]/a[1]")[0] is not None:
                rankingsDict['name'].append(dom.xpath("/html[1]/body[1]/main[1]/anet-site-app[1]/shared-tf-rankings[1]/div[1]/div[1]/div[2]/div[2]/table[1]/tbody[2]/tr[" + str(i+1) + "]/td[5]/div[1]/a[1]")[0].text.strip())
                rankingsDict['time'].append(dom.xpath("/html[1]/body[1]/main[1]/anet-site-app[1]/shared-tf-rankings[1]/div[1]/div[1]/div[2]/div[2]/table[1]/tbody[2]/tr[" + str(i+1) + "]/td[7]/div[1]/a[1]/span[1]")[0].text.strip())
                try:
                    rankingsDict['team'].append(dom.xpath("/html[1]/body[1]/main[1]/anet-site-app[1]/shared-tf-rankings[1]/div[1]/div[1]/div[2]/div[2]/table[1]/tbody[2]/tr[" + str(i+1) + "]/td[15]/a[1]")[0].text.strip())
                except:
                    rankingsDict['team'].append("Unattached")
                rankingsDict['grade'].append(dom.xpath("/html[1]/body[1]/main[1]/anet-site-app[1]/shared-tf-rankings[1]/div[1]/div[1]/div[2]/div[2]/table[1]/tbody[2]/tr[" + str(i+1) + "]/td[12]")[0].text.strip())
                rankingsDict['state'].append(dom.xpath("/html[1]/body[1]/main[1]/anet-site-app[1]/shared-tf-rankings[1]/div[1]/div[1]/div[2]/div[2]/table[1]/tbody[2]/tr[" + str(i+1) + "]/td[10]")[0].text.strip())
                rankingsDict['date'].append(dom.xpath("/html[1]/body[1]/main[1]/anet-site-app[1]/shared-tf-rankings[1]/div[1]/div[1]/div[2]/div[2]/table[1]/tbody[2]/tr[" + str(i+1) + "]/td[16]")[0].text.strip())
        except:
            pass
    return pd.DataFrame(data=rankingsDict)



#Paste in URL for event, and fill in the number of pages that the event has. Probably could use a counter and click on the next page box with the next page but I'm lazy..
url = "https://www.athletic.net/TrackAndField/rankings/list/169804/m/200m"
numPages = 82

eventDF = pd.DataFrame(data = {'name': [], 'time': [], 'team': [], 'grade': [], 'state': [], 'date': []})
with SB(uc=True) as sb:
    sb.uc_open_with_reconnect(url, 2)
    sb.uc_click("button.btn-primary.btn-lg")
    sb.type("//input[@id='email']", 'SUPER SECRET LOGIN INFO')
    sb.type("//input[@id='password']", 'SUPER SECRET LOGIN INFO')
    sb.click("//button[@class='athletic-auth-modal--button athletic-auth-modal--continue']")

    try:
        for i in range(1, numPages+1):
            sb.uc_open_with_reconnect(url + "?page=" + str(i), 2)
            sb.wait_for_element("#rankingsTable tbody.event-results tr[id]")
            sb.sleep(1)
            eventDF = pd.concat([eventDF, parse_rankings(sb.get_page_source())])
            sb.sleep(random.uniform(.75, 2))
    finally:
        #Need to manually file output name to match event
        eventDF.to_csv('output200.csv', index=False)
