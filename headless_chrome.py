"""This module RSVPs the next submission of attendees in the queue."""

# Imports
import re # RegEx
import os
import csv # Read submitted CSV file
import time # To sleep between attendees
from datetime import datetime # to get current year for year-based custom fields
from ftplib import FTP # to connect to FTP server
import sys # To print logs
import psycopg2 # PostgreSQL database connection
from selenium import webdriver

def rsvp():
    """This function RSVPs the next submission of attendees in the queue."""
    # Get env variables, set defaults if not set (for some)
    database_url = os.getenv('DATABASE_URL')
    ftp_host = os.getenv('FTP_HOST')
    ftp_user = os.getenv('FTP_USER')
    ftp_pass = os.getenv('FTP_PASS')
    # URL RegEx to match submitted URL to
    url_regex = os.getenv('URL_REGEX', "^https://www.mobilize.us/[a-zA-Z0-9]+/event/[0-9]+/")
    # Added to Mobilize RSVP URL to track how attendees registered in attendee reports
    utm_medium = os.getenv('UTM_MEDIUM')
    # Added to Mobilize RSVP URL to track how attendees registered in attendee reports
    utm_source = os.getenv('UTM_SOURCE')
    # Added to Mobilize RSVP URL to track how attendees registered in attendee reports
    utm_campaign = os.getenv('UTM_CAMPAIGN',"python+auto+register")
    # In the event there are custom fields that are required to
    # register, this will be submitted in that field
    default_custom_field_val = os.getenv('DEFAULT_CUSTOM_FIELD_VAL',"PYTHON AUTO REGISTER")
    sleep_time = float(os.getenv('SLEEP_TIME', '0.5')) # Time to wait between attendees

    # Connect to PostgreSQL database
    conn = psycopg2.connect(database_url, sslmode='require')
    cur = conn.cursor()

    # Find next event to register contacts for
    cur.execute("SELECT * FROM registrations ORDER BY id ASC LIMIT 1;")
    row = cur.fetchone()
    if row is not None: # If queue is not empty

        # Verify Mobilize link is a valid Mobilize URL
        mobilize_link = row[1]
        verify_url = re.search(url_regex, mobilize_link)
        if verify_url is None: # If submitted URL doesn't match RegEx
            print("Invalid Mobilize RSVP URL. "
                  "It should look like this: https://www.mobilize.us/mobilize/event/313945/")
            sys.stdout.flush()

        # Fetch tsv file from FTP server
        ftp = FTP(ftp_host,ftp_user,ftp_pass)
        with open('contact-list.txt', 'wb') as file_to_receive:
            ftp.retrbinary('RETR '+row[3], file_to_receive.write)

        path = 'contact-list.txt' # Path to local list of contacts to register
        num_rows = len(open(path).readlines(  )) - 1 # Num of contacts to register
        with open(path) as tsv:
            # Initialize headless Chrome driver
            chrome_options = webdriver.ChromeOptions()
            chrome_options.binary_location = os.getenv(
                "GOOGLE_CHROME_BIN",
                "/app/.apt/usr/bin/google_chrome")
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            driver = webdriver.Chrome(
                executable_path=os.getenv(
                    "CHROMEDRIVER_PATH",
                    "/app/.chromedriver/bin/chromedriver"),
                chrome_options=chrome_options)

            firstline = True
            # Foreach line in CSV with tabs as delimiter and NUL characters removed
            for line in csv.reader((line.replace('\0','') for line in tsv), delimiter="\t"):
                if firstline: # skip first line (header)
                    firstline = False
                    continue

                # Map columns from TSV to variables used to generate RSVP url
                first_name = line[row[4]]
                last_name = line[row[5]]
                zip_code = line[row[6]]
                email = line[row[7]]
                cell_phone = line[row[8]]
                home_phone = line[row[9]]
                # Home phone fallback if no cell phone
                if not cell_phone:
                    phone = home_phone
                else:
                    phone = cell_phone

                # Generate unique URL to register this attendee, and only include
                # UTM parameters that are set to shorten link
                unique_url = mobilize_link
                unique_url += "?first_name=" + first_name
                unique_url += "&last_name=" + last_name
                unique_url += "&email=" + email
                unique_url += "&zip="+ zip_code
                unique_url += "&phone=" + phone
                if utm_medium:
                    unique_url += "&utm_medium="+utm_medium
                if utm_source:
                    unique_url += "&utm_source="+utm_source
                if utm_campaign:
                    unique_url += "&utm_campaign="+utm_campaign

                driver.get(unique_url) # Open URL
                # Get custom field wrapper element
                custom_field_wrapper = driver.find_element_by_css_selector(
                    ".signup-form div[class*=\"CustomFieldWrapper\"]")
                # Get custom field inputs
                custom_fields = custom_field_wrapper.find_elements_by_tag_name("input")
                for field in custom_fields: # foreach custom field input
                    req_val = field.get_attribute("required") # determine if input is required

                    # if input is required, clear whatever's there already
                    # and type in the default value (set in env variables)
                    if req_val:
                        field.clear()
                        field.send_keys(default_custom_field_val)

                # Set birthyear custom field (if exists and required) to current year
                birth_year = driver.find_elements_by_name("custom-field-birthyear")
                if birth_year:
                    for text_input in birth_year:
                        req_val = text_input.get_attribute("required")
                        if req_val:
                            text_input.clear()
                            text_input.send_keys(datetime.now().year)

                custom_field_wrapper.submit() # Submit registration form

                time.sleep(sleep_time) # Wait sleep_time to ensure form gets submitted successfully
            driver.close() # Close Chrome window

            ftp.delete(row[3]) # Delete CSV from FTP server

            # Remove from queue
            cur.execute("DELETE FROM registrations WHERE id='"+str(row[0])+"';")
            conn.commit()

            # Log how many contacts were RSVPed to this event
            print("RSVPed",str(num_rows),"contacts to",mobilize_link)
            sys.stdout.flush()

    # Close PostgreSQL connection
    cur.close()
    conn.close()
