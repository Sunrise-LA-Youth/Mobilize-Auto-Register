# Imports
from flask import Flask, render_template, request, flash, make_response # Flask
from flask_talisman import Talisman # to improve Flask security
from ftplib import FTP # to connect to FTP server
import uuid # to randomly generate filename
import os
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
    ]
}
talisman = Talisman(app, content_security_policy=csp, content_security_policy_nonce_in=['script-src','style-src'], strict_transport_security_preload=True)

# Register route
@app.route('/', methods=['GET', 'POST'])
def form():
    # Get RegEx env variable, set default if not set
    URL_REGEX = os.getenv('URL_REGEX', "^https://www.mobilize.us/[a-zA-Z0-9]+/event/[0-9]+/")
    
    if request.method == 'POST': # If form submitted
        
        # Get env variables
        DATABASE_URL = os.getenv('DATABASE_URL')
        FTP_HOST = os.getenv('FTP_HOST')
        FTP_USER = os.getenv('FTP_USER')
        FTP_PASS = os.getenv('FTP_PASS')
        MIN_INTERVAL = int(os.getenv('MIN_INTERVAL',3))
        
        # Connect to PostgreSQL database
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        
        # Calculate ETA based on how many registrations are in the queue
        cur.execute("SELECT * FROM registrations;")
        rowcount = cur.rowcount
        eta = (rowcount + 1) * MIN_INTERVAL
        
        # Get submitted .txt file and set new random filename
        newFilename = str(uuid.uuid4()) + '.txt'
        file = request.files['tsvFile']
        
        error = False # We'll use this later to not do anything with the submitted data if it gets set to True
        if ".txt" not in file.filename: # If file is not a .txt file
            flash('<strong>Invalid file type:</strong> You must upload a .txt file.', 'danger') # Flash error message
            error = True
        if not error: # If file is ok to upload
            # Connect to FTP server and upload submitted file
            ftp = FTP(FTP_HOST,FTP_USER,FTP_PASS)
            ftp.storlines("STOR " + newFilename, file)
            
            # Add registration to queue
            cur.execute("INSERT INTO registrations (mobilize_url,tsv_file,col_fname,col_lname,col_zip,col_email,col_cell,col_home) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",(request.form['mobilizeUrl'],newFilename,request.form['firstNameCol'],request.form['lastNameCol'],request.form['zipCol'],request.form['emailCol'],request.form['cellPhoneCol'],request.form['homePhoneCol']))
            conn.commit()
            
            # Flash success message with queue details
            flash('<strong>List submitted!</strong> The contacts you selected will be registered shortly for the specified Mobilize event. We estimate the contacts will be RSVPed in the next ' + str(eta) + ' minutes, with ' + str(rowcount) + ' other registrations ahead.', 'info')
        
        # Close PostgreSQL connection
        cur.close()
        conn.close()
    resp = make_response(render_template('index.html',regex=URL_REGEX)) # Render template and pass RegEx as a variable
    resp.cache_control.max_age = 86400
    return resp

if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)
    