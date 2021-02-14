from flask import Flask, render_template, request
from ftplib import FTP
import uuid
import os
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def form():
    URL_REGEX = os.getenv('URL_REGEX', "^https://www.mobilize.us/[a-zA-Z0-9]+/event/[0-9]+/")
    if request.method == 'POST':
        DATABASE_URL = os.getenv('DATABASE_URL')
        FTP_HOST = os.getenv('FTP_HOST')
        FTP_USER = os.getenv('FTP_USER')
        FTP_PASS = os.getenv('FTP_PASS')
        MIN_INTERVAL = int(os.getenv('MIN_INTERVAL',3))
        
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM registrations;")
        rowcount = cur.rowcount
        eta = (rowcount + 1) * MIN_INTERVAL
        
        newFilename = uuid.uuid4() + '.txt'
        file = request.files['tsvFile']
        file.save('/uploads/'+newFilename)
        
        error = False
        if ".txt" not in file.filename:
            flash('<strong>Invalid file type:</strong> You must upload a .txt file.', 'danger')
            error = True
        if os.stat('/uploads/'+newFilename).st_size > 10000000:
            flash('<strong>File too big:</strong> You must upload a .txt file that is under 10mb.', 'danger')
            error = True
        if not error:
            ftp = FTP(FTP_HOST,FTP_USER,FTP_PASS)
            ftp.storlines("STOR " + newFilename, open('/uploads/'+newFilename, 'rb'))
            os.remove('/uploads/'+newFilename)
            
            cur.execute("INSERT INTO registrations (mobilize_url,tsv_file,col_fname,col_lname,col_zip,col_email,col_cell,col_home) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",(request.form['mobilizeUrl'],newFilename,request.form['firstNameCol'],request.form['lastNameCol'],request.form['zipCol'],request.form['emailCol'],request.form['cellPhoneCol'],request.form['homePhoneCol']))
            conn.commit()
            flash('<strong>List submitted!</strong> The contacts you selected will be registered shortly for the specified Mobilize event. We estimate the contacts will be RSVPed in the next ' + eta + ' minutes, with ' + rowcount + ' other registrations ahead.', 'info')
        
        cur.close()
        conn.close()
    return render_template('index.html',regex=URL_REGEX)

if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)
    