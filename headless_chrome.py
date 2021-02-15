# Imports
import re # RegEx
import os
import csv # Read submitted CSV file
import time # To sleep between attendees
import psycopg2 # PostgreSQL database connection
import sys # To print logs
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from datetime import datetime # to get current year for year-based custom fields
from ftplib import FTP # to connect to FTP server

def rsvp():
    
    # Get env variables, set defaults if not set (for some)
    DATABASE_URL = os.getenv('DATABASE_URL')
    FTP_HOST = os.getenv('FTP_HOST')
    FTP_USER = os.getenv('FTP_USER')
    FTP_PASS = os.getenv('FTP_PASS')
    URL_REGEX = os.getenv('URL_REGEX', "^https://www.mobilize.us/[a-zA-Z0-9]+/event/[0-9]+/") # URL RegEx to match submitted URL to
    UTM_MEDIUM = os.getenv('UTM_MEDIUM') # Added to Mobilize RSVP URL to track how attendees registered in attendee reports
    UTM_SOURCE = os.getenv('UTM_SOURCE') # Added to Mobilize RSVP URL to track how attendees registered in attendee reports
    UTM_CAMPAIGN = os.getenv('UTM_CAMPAIGN',"python+auto+register") # Added to Mobilize RSVP URL to track how attendees registered in attendee reports
    DEFAULT_CUSTOM_FIELD_VAL = os.getenv('DEFAULT_CUSTOM_FIELD_VAL',"PYTHON AUTO REGISTER") # In the event there are custom fields that are required to register, this will be submitted in that field
    SLEEP_TIME = float(os.getenv('SLEEP_TIME',0.5)) # Time to wait between attendees

    # Connect to PostgreSQL database
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    
    # Find next event to register contacts for
    cur.execute("SELECT * FROM registrations ORDER BY id ASC LIMIT 1;")
    row = cur.fetchone()
    if row is not None: # If queue is not empty

        # Verify Mobilize link is a valid Mobilize URL
        mobilizeLink = row[1]
        verifyUrl = re.search(URL_REGEX, mobilizeLink)
        if verifyUrl is None: # If submitted URL doesn't match RegEx
            print("Invalid Mobilize RSVP URL. It should look like this: https://www.mobilize.us/mobilize/event/313945/")
            sys.stdout.flush()

        # Fetch tsv file from FTP server
        ftp = FTP(FTP_HOST,FTP_USER,FTP_PASS)
        with open('contact-list.txt', 'wb') as fp:
            ftp.retrbinary('RETR '+row[3], fp.write)

        path = 'contact-list.txt'; # Path to local list of contacts to register
        numRows = len(open(path).readlines(  )) - 1 # Num of contacts to register
        with open(path) as tsv:
            # Initialize headless Chrome driver
            chrome_options = webdriver.ChromeOptions()
            chrome_options.binary_location = os.getenv("GOOGLE_CHROME_BIN","/app/.apt/usr/bin/google_chrome")
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            driver = webdriver.Chrome(executable_path=os.getenv("CHROMEDRIVER_PATH","/app/.chromedriver/bin/chromedriver"), chrome_options=chrome_options)

            firstline = True

            for line in csv.reader((line.replace('\0','') for line in tsv), delimiter="\t"): # Foreach line in CSV with tabs as delimiter and NUL characters removed
                if firstline: # skip first line (header)
                    firstline = False
                    continue
                
                # Map columns from TSV to variables used to generate RSVP url
                fName = line[row[4]]
                lName = line[row[5]]
                zipCode = line[row[6]]
                email = line[row[7]]
                cPhone = line[row[8]]
                hPhone = line[row[9]]
                # Home phone fallback if no cell phone
                if not cPhone:
                    phone = hPhone
                else:
                    phone = cPhone

                # Generate unique URL to register this attendee, and only include UTM parameters that are set to shorten link
                uniqueUrl = mobilizeLink + "?first_name=" + fName + "&last_name=" + lName + "&email=" + email + "&zip=" + zipCode + "&phone=" + phone
                if UTM_MEDIUM:
                    uniqueUrl += "&utm_medium="+UTM_MEDIUM
                if UTM_SOURCE:
                    uniqueUrl += "&utm_source="+UTM_SOURCE
                if UTM_CAMPAIGN:
                    uniqueUrl += "&utm_campaign="+UTM_CAMPAIGN

                driver.get(uniqueUrl) # Open URL
                customFieldWrapper = driver.find_element_by_css_selector(".signup-form div[class*=\"CustomFieldWrapper\"]") # Get custom field wrapper element
                customFields = customFieldWrapper.find_elements_by_tag_name("input") # Get custom field inputs
                for field in customFields: # foreach custom field input
                    reqVal = field.get_attribute("required") # determine if input is required
                    if reqVal: # if input is required, clear whatever's there already and type in the default value (set in env variables)
                        field.clear()
                        field.send_keys(DEFAULT_CUSTOM_FIELD_VAL)

                # Set birthyear custom field (if exists and required) to current year
                birthYear = driver.find_elements_by_name("custom-field-birthyear")
                if birthYear:
                    for textInput in birthYear:
                        reqVal = textInput.get_attribute("required")
                        if reqVal:
                            textInput.clear()
                            textInput.send_keys(datetime.now().year)

                customFieldWrapper.submit() # Submit registration form

                time.sleep(SLEEP_TIME) # Wait SLEEP_TIME to ensure form gets submitted successfully
            driver.close() # Close Chrome window
            
            ftp.delete(row[3]) # Delete CSV from FTP server
            
            # Remove from queue
            cur.execute("DELETE FROM registrations WHERE id='"+str(row[0])+"';")
            conn.commit()
            
            # Log how many contacts were RSVPed to this event
            print("RSVPed",str(numRows),"contacts to",mobilizeLink)
            sys.stdout.flush()

    # Close PostgreSQL connection
    cur.close()
    conn.close()
