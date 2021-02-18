"""This module powers the Flask webpage of the registration bot."""

# Imports
import os
import uuid # to randomly generate filename
from ftplib import FTP # to connect to FTP server
from flask import Flask, render_template, request, flash, make_response # Flask
from flask_talisman import Talisman # to improve Flask security
import psycopg2 # PostgreSQL database connection

# Initialize Flask app and Talisman security features
app = Flask(__name__)
app.secret_key = os.urandom(24)
csp = {
    'default-src': [
        '\'self\'',
        'cdn.jsdelivr.net',
        'buttons.github.io',
        '*.mobilize.us',
        'code.jquery.com',
        'api.github.com'
    ],
    'script-src': [
        '\'self\'',
        'cdn.jsdelivr.net',
        'buttons.github.io',
        'code.jquery.com'
    ],
    'style-src': [
        '\'self\'',
        'cdn.jsdelivr.net',
        '\'unsafe-inline\''
    ]
}
talisman = Talisman(app,
                    content_security_policy=csp,
                    content_security_policy_nonce_in=['script-src'],
                    strict_transport_security_preload=True)

# Register route
@app.route('/', methods=['GET', 'POST'])
def form():
    """This function runs the Flask webpage to show and submit a form to the queue of registrations."""
    # Get RegEx env variable, set default if not set
    url_regex = os.getenv('URL_REGEX', "^https://www.mobilize.us/[a-zA-Z0-9]+/event/[0-9]+/")

    if request.method == 'POST': # If form submitted

        # Get env variables
        database_url = os.getenv('DATABASE_URL')
        ftp_host = os.getenv('FTP_HOST')
        ftp_user = os.getenv('FTP_USER')
        ftp_pass = os.getenv('FTP_PASS')
        min_interval = int(os.getenv('MIN_INTERVAL', '3'))

        # Connect to PostgreSQL database
        conn = psycopg2.connect(database_url, sslmode='require')
        cur = conn.cursor()

        # Calculate ETA based on how many registrations are in the queue
        cur.execute("SELECT * FROM registrations;")
        rowcount = cur.rowcount
        eta = (rowcount + 1) * min_interval

        # Get submitted .txt file and set new random filename
        new_filename = str(uuid.uuid4()) + '.txt'
        file = request.files['tsvFile']

        # We'll use this later to not do anything with the submitted data if it gets set to True
        error = False
        if ".txt" not in file.filename: # If file is not a .txt file
            flash('<strong>Invalid file type:</strong> You must upload a .txt file.',
                  'danger') # Flash error message
            error = True
        if not error: # If file is ok to upload
            # Connect to FTP server and upload submitted file
            ftp = FTP(ftp_host,ftp_user,ftp_pass)
            ftp.storlines("STOR " + new_filename, file)

            # Add registration to queue
            cur.execute("INSERT INTO "
                        "registrations (mobilize_url,tsv_file,col_fname,col_lname,"
                        "col_zip,col_email,col_cell,col_home) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (
                            request.form['mobilizeUrl'],
                            new_filename,
                            request.form['firstNameCol'],
                            request.form['lastNameCol'],
                            request.form['zipCol'],
                            request.form['emailCol'],
                            request.form['cellPhoneCol'],
                            request.form['homePhoneCol']
                        ))
            conn.commit()

            # Flash success message with queue details
            flash("<strong>List submitted!</strong> The contacts you selected will "
                  "be registered shortly for the specified Mobilize event. We estimate "
                  "the contacts will be RSVPed in the next " + str(eta)
                  " minutes, with " + str(rowcount) + " other registrations ahead."
                  ,'info')

        # Close PostgreSQL connection
        cur.close()
        conn.close()
    # Render template and pass RegEx as a variable
    resp = make_response(render_template('index.html',regex=url_regex))
    resp.cache_control.max_age = 86400
    return resp

if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)
    