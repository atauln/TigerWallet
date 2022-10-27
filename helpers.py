import datetime
import os
from flask import request, session
import requests
import csv
from bs4 import BeautifulSoup
import app

semester_times = {
    2221: {
        "start": datetime.datetime(2022, 7, 1, 0, 0, 0),
        "end": datetime.datetime(2022, 12, 14, 0, 0, 0)
    },
    2222: {
        "start": datetime.datetime(2023, 1, 14, 0, 0, 0),
        "end": datetime.datetime(2023, 5, 14, 0, 0, 0)
    }
}

def get_datetimes():
    return (
        semester_times[int(os.getenv("CURRENT_SEMESTER"))]["start"], 
        datetime.datetime.today(), 
        semester_times[int(os.getenv("CURRENT_SEMESTER"))]["end"]
    )

def get_date_strings():
    return (
        semester_times[int(os.getenv("CURRENT_SEMESTER"))]["start"].strftime("%-m/%d/%Y"), 
        datetime.datetime.today().strftime("%-m/%d/%Y"), 
        semester_times[int(os.getenv("CURRENT_SEMESTER"))]["end"].strftime("%-m/%d/%Y")
    )

def get_meal_plan_name(plan_id):
    meal_plans = {
        1: "TigerBucks",
        24: "Voluntary Dining",
        29: "Rollover"
    }
    if plan_id in meal_plans:
        return meal_plans[plan_id]
    else:
        return "Meal Plan"

def log_to_console(message):
    """Simple function to send message to the console
    in a consistent manner."""
    print(f"GET {request.remote_addr} @ {request.url} -> {message}")

def post_to_pings(subject_uuid, username, body):
    """POST to pings.csh.rit.edu (created by Ethan Fergussen | @ethanf108)"""

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
        log_to_console("Failed to access os env var 'PINGS_TOKEN'!")

    return response.status_code

def verify_skey_integrity():
    """Verifies the integrity of the session variables.

    Regenerates them if they are found to have expired."""

    if not app.check_session_value('theme'):
        app.set_session_value('theme', 'dark')

    # validate that it is returning an actual csv, and not an HTML
    parsed_csv = [['', '', '', ''], ['', '', '', '']]

    if app.check_session_value('skey'):
        if not app.check_session_value('dining_id'):
            # locates meal plan in use
            plans = get_user_plans()
            for plan in plans:
                plan_id = int(plan.attrs['value'])
                if get_meal_plan_name(plan_id) == "Meal Plan":
                    # save the meal plan to your session
                    log_to_console(f"Found meal plan {plan_id}")
                    app.set_session_value('dining_id', plan_id)
                    break
            else:
                log_to_console("Could not find a meal plan")
                app.set_session_value("dining_id", plans[0].attrs['value'])

        if app.check_session_value('dining_id'):
            parsed_csv = get_user_spending(app.get_session_value('dining_id'), int(os.getenv("CURRENT_SEMESTER")), 'csv')
            try:
                # if it returns a csv but it does not contain anything at this point,
                # it means that there is no account under this name
                if parsed_csv[1][2] == '':
                    log_to_console("Returned an empty account during skey verification")
                    app.get_session().pop('dining_id')
                    return verify_skey_integrity()

            except IndexError:
                # if it gets an exception, it's because it returned an HTML,
                # in which case the skey is invalid
                log_to_console("Caught an HTML document while verifying skey integrity")
                app.get_session().pop('skey')
                app.get_session().pop('dining_id')
                return None, app.get_session()

        # invalidate session, retry authentication
        if len(parsed_csv[0]) < 4:
            log_to_console("Invalid session during skey verification, retrying...")
            app.get_session().pop('skey')
            app.get_session().pop('dining_id')
            return verify_skey_integrity()
    else:
        return None, session
    
    if parsed_csv[1][2] == '':
        log_to_console("Returned an empty account during skey verification")
        session.pop('dining_id')
        return verify_skey_integrity()

    return parsed_csv, app.get_session()


def get_user_spending(acct: int, semester: int, format_output: str, cid=105):
    """Return user spending information."""

    # check the semester ID and update start and end dates accordingly
    start_date = semester_times[int(os.getenv("CURRENT_SEMESTER"))]["start"].strftime("%Y-%m-%d")
    end_date = semester_times[int(os.getenv("CURRENT_SEMESTER"))]["end"].strftime("%Y-%m-%d")

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

    if 'skey' not in session:
        return None

    payload = {
        'skey': session['skey'],
        'cid': cid
    }
    response = requests.get(
        "https://tigerspend.rit.edu/statementnew.php", payload)
    soup = BeautifulSoup(response.content, 'html.parser')
    options = soup.find(id="select-account").find_all('option')
    app.set_session_value('meal_plans', [[plan.attrs['value'], get_meal_plan_name(int(plan.attrs['value']))] for plan in options])
    return options


def get_account_info(cid=105):
    """Get the user's account information from their account page."""

    while 'skey' not in session:
        verify_skey_integrity()

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
        "Artesano": "Artesano Bakery & Cafe",
        "Brick City": "Brick City Cafe",
        "Nathan": "Nathan's Soup & Salad",
        "Jerry": "Ben & Jerry's",
        "Petals": "RIT Inn Petals"
    }

    for item in locations.items():
        if item[0] in raw_location:
            if "OnDemand" in raw_location:
                return item[1] + " (Online)"
            else:
                return item[1]