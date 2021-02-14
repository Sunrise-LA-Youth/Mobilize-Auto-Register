import re
import os
import csv
import time
import psycopg2
import sys
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from datetime import datetime
from ftplib import FTP

def rsvp():
    
    DATABASE_URL = os.environ['DATABASE_URL']
    FTP_HOST = os.environ['FTP_HOST']
    FTP_USER = os.environ['FTP_USER']
    FTP_PASS = os.environ['FTP_PASS']
    UTM_MEDIUM = os.environ['UTM_MEDIUM']
    UTM_SOURCE = os.environ['UTM_SOURCE']
    UTM_CAMPAIGN = os.environ['UTM_CAMPAIGN']
    DEFAULT_CUSTOM_FIELD_VAL = os.environ['DEFAULT_CUSTOM_FIELD_VAL']
    SLEEP_TIME = int(os.environ['SLEEP_TIME'])

    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    
    cur = conn.cursor()
    
    # Find next event to register contacts for
    cur.execute("SELECT * FROM registrations ORDER BY id ASC LIMIT 1;")
    row = cur.fetchone()
    if row is not None:

        # Verify Mobilize link is a valid Mobilize URL
        mobilizeLink = row[1]
        verifyUrl = re.search("^https://www.mobilize.us/sunrisemovement/event/[0-9]+/", mobilizeLink)
        if verifyUrl is None:
            print("Invalid Mobilize RSVP URL. It should look like this: https://www.mobilize.us/sunrisemovement/event/313945/")
            sys.stdout.flush()

        # Fetch tsv file
        ftp = FTP(FTP_HOST,FTP_USER,FTP_PASS)
        with open('contact-list.txt', 'wb') as fp:
            ftp.retrbinary('RETR '+row[3], fp.write)

        path = 'contact-list.txt';
        numRows = len(open(path).readlines(  )) - 1
        with open(path) as tsv:
            chrome_options = webdriver.ChromeOptions()
            chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=chrome_options)

            countRows = 0
            reader = csv.reader((line.replace('\0','') for line in tsv), delimiter="\t")

            firstline = True

            for line in csv.reader((line.replace('\0','') for line in tsv), delimiter="\t"):
                if firstline:    #skip first line
                    firstline = False
                    continue

                countRows += 1
                fName = line[row[4]]
                lName = line[row[5]]
                zipCode = line[row[6]]
                email = line[row[7]]
                cPhone = line[row[8]]
                hPhone = line[row[9]]
                if not cPhone:
                    phone = hPhone
                else:
                    phone = cPhone

                uniqueUrl = mobilizeLink + "?first_name=" + fName + "&last_name=" + lName + "&email=" + email + "&zip=" + zipCode + "&phone=" + phone + "&utm_medium="+UTM_MEDIUM+"&utm_source="+UTM_SOURCE+"&utm_campaign="+UTM_CAMPAIGN

                driver.get(uniqueUrl)
                customFieldWrapper = driver.find_element_by_css_selector(".signup-form div[class*=\"CustomFieldWrapper\"]")
                customFields = customFieldWrapper.find_elements_by_tag_name("input")
                for field in customFields:
                    reqVal = field.get_attribute("required")
                    if reqVal:
                        field.clear()
                        field.send_keys(DEFAULT_CUSTOM_FIELD_VAL)

                birthYear = driver.find_elements_by_name("custom-field-birthyear")
                if birthYear:
                    for textInput in birthYear:
                        reqVal = textInput.get_attribute("required")
                        if reqVal:
                            textInput.clear()
                            textInput.send_keys(datetime.now().year)

                customFieldWrapper.submit()

                time.sleep(SLEEP_TIME)
            driver.close()
            ftp.delete(row[3])
            cur.execute("DELETE FROM registrations WHERE id='"+str(row[0])+"';")
            conn.commit()
            print("RSVPed",str(numRows),"contacts to event")
            sys.stdout.flush()

    cur.close()
    conn.close()
