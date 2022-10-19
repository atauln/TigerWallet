"""
Flask application created to show users their TigerSpend account information
in a more efficient and well-tailored manner.
"""

import csv
import datetime
import os
import time

import requests
from bs4 import BeautifulSoup
import dotenv
from flask import Flask, redirect, render_template, request, session

dotenv.load_dotenv()

app = Flask(__name__)

PING_TOKEN = "" # this will NOT be set here, moving to env vars very soon

app.secret_key = os.urandom(16)

os.environ['TZ'] = "America/New_York"
time.tzset()


def log_to_console(message):
    """Simple function to send message to the console
    in a consistent manner."""
    print(f"GET {request.remote_addr} @ {request.url} -> {message}")

def post_to_pings(subject_uuid, username, body):
    """POST to pings.csh.rit.edu (created by Ethan Fergussen | @ethanf108)"""

    # TODO set up env vars
    headers = {
        "Authorization": "Bearer " + str(os.getenv("PINGS_TOKEN"))
    }

    payload = {
        "username": username,
        "body": body
    }

    try:
        response = requests.post(f"https://pings.csh.rit.edu/service/route/{subject_uuid}/ping", headers=headers, json=payload)
    except requests.exceptions.ChunkedEncodingError:
        return 0

    return response.status_code

def verify_skey_integrity():
    """Verifies the integrity of the session variables.

    Regenerates them if they are found to have expired."""

    # validate that it is returning an actual csv, and not an HTML
    parsed_csv = [['', '', '', ''], ['', '', '', '']]

    if 'skey' in session:
        if 'dining_id' in session:
            parsed_csv = get_user_spending(session['dining_id'], 2221, 'csv')
            try:
                # if it returns a csv but it does not contain anything at this point,
                # it means that there is no account under this name
                if parsed_csv[1][2] == '':
                    session.pop('dining_id')
                    return verify_skey_integrity()

            except IndexError:
                # if it gets an exception, it's because it returned an HTML,
                # in which case the skey is invalid
                session.pop('skey')
                session.pop('dining_id')
                return []

        else:
            # locates meal plan in use
            dining_id = get_user_plans()
            parsed_csv = get_user_spending(dining_id, 2221, 'csv')

            # save the meal plan to your session
            session['dining_id'] = dining_id

        # invalidate session, retry authentication
        # OR THROW ERROR
        if len(parsed_csv[0]) < 4:
            session.pop('skey')
            session.pop('dining_id')
            return verify_skey_integrity()
    else:
        return []
    return parsed_csv


def get_user_spending(acct: int, semester: int, format_output: str, cid=105):
    """Return user spending information."""

    # check the semester ID and update start and end dates accordingly
    if semester == 2221:
        start_date = "2022-07-01"
        end_date = "2022-12-14"

    if 'skey' in session:
        # send TigerSpend the payload details and get CSV back
        payload = {
            'skey': session['skey'],
            'format': format_output,
            'startdate': start_date,
            'enddate': end_date,
            'acct': acct,
            'cid': cid
        }

        response = requests.get(
            "https://tigerspend.rit.edu/statementdetail.php", payload)

        # decode the CSV and turn into an array of records
        # Eventually you should check if the response is in HTML because the login probably didn't work
        lines = response.content.decode(response.encoding).splitlines()
        reader = csv.reader(lines)
        return list(reader)
    else:
        return None


def get_user_plans(cid=105):
    """Get a list of all the user's plans and return the first one."""

    # TODO expand to return a list of the plans for '/accounts'

    if 'skey' not in session:
        return 0

    payload = {
        'skey': session['skey'],
        'cid': cid
    }
    response = requests.get(
        "https://tigerspend.rit.edu/statementnew.php", payload)
    soup = BeautifulSoup(response.content, 'html.parser')
    options = soup.find(id="select-account").find_all('option')
    return options[0].attrs['value']


def get_account_info(cid=105):
    """Get the user's name from their account page."""

    if 'skey' not in session:
        return ""

    payload = {
        'skey': session['skey'],
        'cid': cid
    }
    response = requests.get(
        "https://tigerspend.rit.edu/statementnew.php", payload)

    soup = BeautifulSoup(response.content, 'html.parser')
    options = soup.find("div", {"class": "jsa_account-info"}).find_all("b")

    name = options[0].getText().split(" ")

    account_data = [
        str(name[0][0]).lower() + str(name[1]).lower() + str(options[1]).strip('x'), # account_id
        name[0], # first_name
        name[1], # last_name
        str(options[1]).strip('x')] # account_number

    return account_data



def get_daily_spending(csv_file):
    """Process CSV output from TigerSpend into array of total costs per day"""
    daily_spent = dict()

    for record in csv_file:
        # keys in the dictionary are the date on which transactions occurred
        key = record[0].split(" ")[0]
        try:
            if not key in daily_spent:
                daily_spent[key] = 0
            daily_spent[key] -= round(float(record[2]), 2)
        except ValueError:
            continue
        except IndexError:
            continue
    return daily_spent


def get_spending_over_time(csv_file, days=7, offset=0):
    """Return cost over a certain pay period."""
    daily_spent = get_daily_spending(csv_file)

    money_spent = 0
    today = datetime.datetime.today()
    for daydelta in range(offset, days + offset):
        # get the date of the start of the range
        target = datetime.timedelta(days=daydelta)
        target_date = datetime.datetime.strftime(today - target, "%-m/%d/%Y")

        # add on the spending per day
        try:
            money_spent += daily_spent[target_date]
        except KeyError:
            # continues if there is no date provided in the dictionary
            # (no payments that date)
            continue
    return money_spent

def process_location(raw_location):
    """Takes the location code from the CSV and converts it to a
    more readable format."""
    locations = {
        "WELLNESS": "Vending Machine (Wellness)",
        "BEVERAGE": "Vending Machine (Beverage)",
        "SNACK": "Vending Machine (Snack)",
        "STARBUCKS": "Vending Machine (StarBucks)",
        "Beanz": "Beanz",
        "Commons": "The Commons",
        "Gracie": "Gracie's",
        "Corner": "The Corner Store",
        "Ctrl Alt DELi": "Ctrl Alt DELi",
        "Crossroads": "C&M at The Crossroads",
        "RITz": "RITz Sports Zone",
        "Market": "Global Village Market",
        "Underground": "Sol's Underground",
        "Tablet": "Food Trucks",
        "Midnight": "Midnight Oil",
        "Grind": "The College Grind",
        "Concessions": "Campus Concessions",
        "Cantina": "GV Cantina & Grille",
        "Artesano": "Artesano Bakery & Cafe"
    }

    for item in locations.items():
        if item[0] in raw_location:
            if "OnDemand" in raw_location:
                return item[1] + " (Online)"
            else:
                return item[1]


@app.route('/')
def landing():
    """Method run upon landing on the main page."""

    if 'theme' not in session:
        session['theme'] = "dark"

    parsed_csv = verify_skey_integrity()

    # check if the skey is contained within the session
    if 'skey' not in session:
        log_to_console("No 'skey' located in session...")
        return render_template("index.html", session=session, redir=f"https://tigerspend.rit.edu/login.php?wason={request.url_root}auth")

    date_unprocessed = datetime.datetime.today()
    current_date = datetime.datetime.strftime(date_unprocessed, "%-m/%d/%Y")

    last_date = "12/14/2022"

    date_format = "%m/%d/%Y"

    # get the number of days until the end of the semester
    delta = datetime.datetime.strptime(
        last_date, date_format) - date_unprocessed

    #starting_balance = float(parsed_csv[-1][3]) - float(parsed_csv[-1][2])
    current_balance = float(parsed_csv[1][3])

    # get daily budget based off balance in account yesterday
    daily_budget = round(
        ((current_balance - get_spending_over_time(parsed_csv, 1)) / delta.days), 2)

    if daily_budget == 0:
        session.pop("skey")
        session.pop("dining_id")
        log_to_console("Daily budget was equivalent to 0, invalidating session")
        return redirect('/')

    # packaging up data to send to template
    data = [current_balance, daily_budget, get_spending_over_time(parsed_csv, 1),
    get_spending_over_time(parsed_csv, 7, 1), get_spending_over_time(parsed_csv, 30, 1), get_account_info()]

    log_to_console("Skey found! Displaying page.")
    return render_template("index.html", session=session, data=data, records=parsed_csv)


@app.route('/purchases')
def daily():
    """Method run upon opening the Purchases tab"""
    if 'theme' not in session:
        session['theme'] = "dark"

    parsed_csv = verify_skey_integrity()
    if 'skey' not in session:
        log_to_console("No 'skey' located in session...")
        return redirect('/')

    total = get_spending_over_time(parsed_csv, 1)
    yesterday_total = get_spending_over_time(parsed_csv, 1, 1)

    date_unprocessed = datetime.datetime.today()
    current_date = datetime.datetime.strftime(date_unprocessed, "%-m/%d/%Y")
    last_date = "12/14/2022"

    date_format = "%m/%d/%Y"

    spending = {}

    sum = 0
    count = 0

    spending_instance = list()
    last_date = ""


    for record in parsed_csv:
        if record[0] == "Date":
            continue
        elif last_date == "":
            last_date = str(record[0]).split(" ")[0]
        record[1] = process_location(record[1])
        record[2] = float(str(record[2]).strip('-'))
        record[3] = float(record[3])
        sum += record[2]
        count += 1

        if str(record[0]).split(" ")[0] not in spending:
            spending[last_date] = spending_instance.copy()
            spending_instance.clear()
            last_date = str(record[0]).split(" ")[0]
        
        spending_instance.append(record)


    delta = datetime.datetime.strptime(last_date, date_format) - datetime.datetime.strptime(current_date, date_format)

    daily_budget = round(
        ((float(parsed_csv[1][3]) - get_spending_over_time(parsed_csv, 1)) / delta.days), 2)

    if daily_budget == 0:
        session.pop("skey")
        session.pop("dining_id")
        log_to_console("Daily budget was equivalent to 0, invalidating session")
        return redirect('/')



    log_to_console("Skey found! Displaying page.")

    return render_template("purchases.html", session=session, spending=spending)


@app.route('/auth')
def auth():
    """Method for authenticating on /auth"""
    # authenticate user based on redirect from tigerspend with skey enclosed as arg
    if 'skey' in request.args.keys():
        log_to_console("Provided a valid 'skey'")
        session['skey'] = str(request.args.get('skey'))
    else:
        log_to_console("Did not provide an 'skey'")

    if request.args.get('wason') != '/':
        log_to_console(f"Detected external link for wason: {request.args.get('wason')} | Redirecting to '/'")
        return redirect('/')

    return redirect(request.args.get('wason'))


@app.route('/switch_theme')
def switch_theme():
    """Closed URL for switching the site's theme."""
    if 'theme' not in session:
        session['theme'] = "dark"
    elif session['theme'] == "light":
        session['theme'] = "dark"
    else:
        session['theme'] = "light"

    log_to_console(f"Switched theme to {session['theme']}! Redirecting user to {request.args.get('wason')}...")

    if request.args.get('wason') != '/':
        log_to_console(f"Detected external link for wason: {request.args.get('wason')} | Redirecting to '/'")
        return redirect('/')

    return redirect(request.args.get('wason'))

@app.errorhandler(404)
def page_not_found(e):
    return redirect('/')


if __name__ == '__main__':
    app.run()
