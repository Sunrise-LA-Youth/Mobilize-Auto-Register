<?php

$submitted = false;
if(isset($_POST["mobilizeUrl"])) {
    $dbconn = pg_connect("host=ec2-3-214-3-162.compute-1.amazonaws.com dbname=d6hfp2dbijrlg2 user=gfjwqvfaqsvqfg password=8ef3e8122f476780fc9238984051a3833b7c7ea4007828d72dce58488320df5a")
    or die('Could not connect: ' . pg_last_error());

    // Performing SQL query
    $query = 'SELECT * FROM registrations';
    $result = pg_query($query) or die('Query failed: ' . pg_last_error());
    $rows = pg_num_rows($result);
    $eta = ($rows+1) * 3;
    pg_free_result($result);
    
    
    $fileType = strtolower(pathinfo($_FILES["tsvFile"]["name"],PATHINFO_EXTENSION));
    $target_file = uniqid() . '.' . $fileType;
    $uploadOk = 1;
    
    $error = '';
    if (file_exists($target_file)) {
        $error .= 'File already exists. ';
        $uploadOk = 0;
    }
    
    if ($_FILES["tsvFile"]["size"] > 500000) {
        $error .= 'File too big. ';
        $uploadOk = 0;
    }
    
    if($fileType != "txt") {
        $error .= "File not a .txt file.";
        $uploadOk = 0;
    }
    
    if ($uploadOk != 0) {
        move_uploaded_file($_FILES["tsvFile"]["tmp_name"], $target_file);

        $result = pg_prepare($dbconn, "insert", 'INSERT INTO registrations (mobilize_url,tsv_file,col_fname,col_lname,col_zip,col_email,col_cell,col_home) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)');

        

        if($result = pg_execute($dbconn, "insert", array($_POST['mobilizeUrl'],$target_file,$_POST['firstNameCol'],$_POST['lastNameCol'],$_POST['zipCol'],$_POST['emailCol'],$_POST['cellPhoneCol'],$_POST['homePhoneCol']))) {
            $submitted = true;
        }
        else {
            $error .= "Failed.";
        }
        pg_free_result($result);
    
    }
    
    
    // Closing connection
    pg_close($dbconn);
}
?>

<!doctype html>
<html lang="en">
    <head>
        <!-- Required meta tags -->
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <!-- Bootstrap CSS -->
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-BmbxuPwQa2lc/FVzBcNJ7UAyJxM6wuqIj61tLrc4wSX0szH/Ev+nYRRuWlolflfl" crossorigin="anonymous">

        <title>Mobilize America Automatic RSVPer</title>
    </head>
    <body class="p-5 container">
        <h1>Mobilize America Automatic RSVPer</h1>
        <p class="lead mb-5">Submit the form below to automatically RSVP a list of contacts to a Mobilize America event.</p>
        <?php if (isset($error) && $error != '') { ?>
        <div class="alert alert-danger mb-5 alert-dismissible fade show" role="alert">
            <?=$error;?>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        <?php } ?>
        <?php if ($submitted) { ?>
        <div class="alert alert-info mb-5 alert-dismissible fade show" role="alert">
            <strong>List submitted!</strong> The contacts you selected will be registered shortly for the specified Mobilize event. We estimate the contacts will be RSVPed in the next <?=$eta;?> minutes, with <?=$rows;?> other registrations ahead.
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        <?php } ?>
        <form action="" method="post" onsubmit="return validateMyForm();" enctype="multipart/form-data">
            <div class="mb-3 form-floating">
                <input type="url" required formnovalidate class="form-control" id="mobilizeUrl" name="mobilizeUrl" placeholder="https://www.mobilize.us/sunrisemovement/event/313945/">
                <label for="mobilizeUrl" class="form-label">Mobilize America RSVP URL</label>
            </div>
            <div class="mb-4">
                <label for="tsvFile" class="form-label">Tab-separated-value list of contacts</label>
                <input required class="form-control" type="file" id="tsvFile" name="tsvFile" accept=".txt" aria-describedby="tsvHelp">
                <div id="tsvHelp" class="form-text">
                    This must be a tab-separated-value .txt file, with the first line being headers.
                </div>
            </div>
            <div class="row mb-3">
                <div class="col">
                    <div class="form-floating">
                        <input required type="number" id="firstNameCol" name="firstNameCol" class="form-control" placeholder="First name column" aria-label="First name column" value="2">
                        <label for="firstNameCol" class="form-label">First Name Column Number (0-index)</label>
                    </div>
                </div>
                <div class="col">
                    <div class="form-floating">
                        <input required type="number" id="lastNameCol" name="lastNameCol" class="form-control" placeholder="Last name column" aria-label="Last name column" value="1">
                        <label for="lastNameCol" class="form-label">Last Name Column Number (0-index)</label>
                    </div>
                </div>
                <div class="col">
                    <div class="form-floating">
                        <input required type="number" id="zipCol" name="zipCol" class="form-control" placeholder="Zip code column" aria-label="Zip code column" value="9">
                        <label for="zipCol" class="form-label">Zip Code Column Number (0-index)</label>
                    </div>
                </div>
            </div>
            <div class="row mb-3">
                <div class="col">
                    <div class="form-floating">
                        <input required type="number" id="emailCol" name="emailCol" class="form-control" placeholder="Email address column" aria-label="Email address column" value="12">
                        <label for="emailCol" class="form-label">Email Address Column Number (0-index)</label>
                    </div>
                </div>
                <div class="col">
                    <div class="form-floating">
                        <input required type="number" id="cellPhoneCol" name="cellPhoneCol" class="form-control" placeholder="Cell phone column" aria-label="Cell phone column" value="13">
                        <label for="cellPhoneCol" class="form-label">Cell Phone Column Number (0-index)</label>
                    </div>
                </div>
                <div class="col">
                    <div class="form-floating">
                        <input required type="number" id="homePhoneCol" name="homePhoneCol" class="form-control" placeholder="Home phone column" aria-label="Home phone column" value="5">
                        <label for="homePhoneCol" class="form-label">Home Phone Column Number (0-index)</label>
                    </div>
                </div>
            </div>
            <button type="submit" class="btn btn-primary">RSVP this list of contacts</button>
        </form>

        <script src="https://code.jquery.com/jquery-3.5.1.min.js" integrity="sha256-9/aliU8dGd2tb6OSsuzixeV4y/faTqgFtohetphbbj0=" crossorigin="anonymous"></script>
        <script>
            $('#mobilizeUrl').keyup(function() {
                var rsvpUrl = $('#mobilizeUrl').val();
                var matchRegex = rsvpUrl.match("^https://www.mobilize.us/sunrisemovement/event/[0-9]+/");
                if (matchRegex) {
                    $('#mobilizeUrl').removeClass('is-invalid');
                    $('#mobilizeUrl').addClass('is-valid');
                }
                else {
                    $('#mobilizeUrl').removeClass('is-valid');
                    $('#mobilizeUrl').addClass('is-invalid');
                }
            })
            function checkUrl() {
                var rsvpUrl = $('#mobilizeUrl').val();
                var matchRegex = rsvpUrl.match("^https://www.mobilize.us/sunrisemovement/event/[0-9]+/");
                if (matchRegex) {
                    $('#mobilizeUrl').removeClass('is-invalid');
                    $('#mobilizeUrl').addClass('is-valid');
                }
                else {
                    $('#mobilizeUrl').removeClass('is-valid');
                    $('#mobilizeUrl').addClass('is-invalid');
                }
                return matchRegex;
            }
            function validateMyForm() {
                if(!checkUrl()) { 
                    return false;
                }
                return true;
            }
        </script>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta2/dist/js/bootstrap.bundle.min.js" integrity="sha384-b5kHyXgcpbZJO/tY9Ul7kGkf1S0CWuKcCD38l8YkeH8z8QjE0GmW1gYU5S9FOnJ0" crossorigin="anonymous"></script>
    </body>
</html>
