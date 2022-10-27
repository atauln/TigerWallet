"""
Flask application created to show users their TigerSpend account information
in a more efficient and well-tailored manner.
"""

import datetime
import os
import time

import dotenv
from flask import Flask, redirect, render_template, request, session

from helpers import *

dotenv.load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(16)

os.environ['TZ'] = "America/New_York"
time.tzset()

def set_session_value(key, value):
    session[key] = value

def check_session_value(key):
    return key in session

def get_session_value(key):
    return session[key]

def get_session():
    return session

@app.route('/')
def landing():
    """Method run upon landing on the main page."""

    parsed_csv, session = verify_skey_integrity()
    

    # check if the skey is contained within the session
    if not check_session_value('skey'):
        log_to_console("No 'skey' located in session...")
        return render_template("index.html", session=get_session(), redir=f"https://tigerspend.rit.edu/login.php?wason={request.url_root}auth")

    _, currentdate, lastdate = get_datetimes()

    # get the number of days until the end of the semester
    delta = lastdate - currentdate

    #starting_balance = float(parsed_csv[-1][3]) - float(parsed_csv[-1][2])
    current_balance = float(parsed_csv[1][3])

    # get daily budget based off balance in account yesterday
    daily_budget = round(
        ((current_balance - get_spending_over_time(parsed_csv, 1)) / delta.days), 2)

    if daily_budget == 0:
        daily_budget = 1

    # packaging up data to send to template
    data = [current_balance, daily_budget, get_spending_over_time(parsed_csv, 1),
    get_spending_over_time(parsed_csv, 7, 1), get_spending_over_time(parsed_csv, 30, 1), get_account_info()]

    
    return render_template("index.html", session=get_session(), data=data, records=parsed_csv, plan_name=get_meal_plan_name(session['dining_id']))


@app.route('/purchases')
def daily():
    """Method run upon opening the Purchases tab"""

    parsed_csv, session = verify_skey_integrity()
    if not check_session_value('skey'):
        log_to_console("No 'skey' located in session...")
        return redirect('/')

    firstdate, currentdate, _ = get_datetimes()

    spending = {}

    sum = 0
    count = 0

    delta = currentdate - firstdate
    for i in range(delta.days):
        date = datetime.datetime.today() - datetime.timedelta(days=i)
        date_processed = date.strftime("%-m/%d/%Y")
        if date_processed not in spending:
            spending[date_processed] = list() 
        for purchase in parsed_csv:
            if str(purchase[0]).split(" ")[0] == date_processed:
                purchase[1] = process_location(purchase[1])
                purchase[2] = float(purchase[2]) * -1
                purchase[3] = float(purchase[3])
                sum += purchase[2]
                count += 1
                spending_list = spending[date_processed]
                spending_list.append(purchase)

    daily_budget = round(
        ((float(parsed_csv[1][3]) - get_spending_over_time(parsed_csv, 1)) / delta.days), 2)

    if daily_budget == 0:
        daily_budget = 1

    return render_template("purchases.html", session=get_session(), spending=spending)


@app.route('/accounts')
def accounts():
    """Method run upon opening the Accounts tab"""

    parsed_csv, session = verify_skey_integrity()
    if not check_session_value('skey'):
        log_to_console("No 'skey' located in session...")
        return redirect('/')

    if 'plan' in request.args:
        set_session_value('dining_id', int(request.args.get("plan")))
    return redirect('/')



@app.route('/auth')
def auth():
    """Method for authenticating on /auth"""
    # authenticate user based on redirect from tigerspend with skey enclosed as arg
    if 'skey' in request.args.keys():
        log_to_console("Provided a valid 'skey'")
        set_session_value('skey', str(request.args.get('skey')))
    else:
        log_to_console("Did not provide an 'skey'")

    if 'wason' in request.args:
        if str(request.args.get('wason'))[0] == '/':
            return redirect(request.args.get('wason'))

        log_to_console(f"Detected external link for wason: {str(request.args.get('wason'))} | Redirecting to '/'")
        
    return redirect('/')


@app.route('/switch_theme')
def switch_theme():
    """Closed URL for switching the site's theme."""
    if not check_session_value('theme'):
        set_session_value('theme', 'dark')
    elif get_session_value('theme') == 'light':
        set_session_value('theme', 'dark')
    else:
        set_session_value('theme', 'light')

    if 'wason' in request.args:
        if str(request.args.get('wason'))[0] != '/':
            log_to_console(f"Detected external link for wason: {str(request.args.get('wason'))} | Redirecting to '/'")
            return redirect('/')

    return redirect(request.args.get('wason'))

@app.errorhandler(404)
def page_not_found(e):
    return redirect('/')

if __name__ == '__main__':
    app.run()
