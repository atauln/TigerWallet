"""
Flask application created to show users their TigerSpend account information
in a more efficient and well-tailored manner.
"""

import datetime

import csv
import requests

from flask import Flask, render_template, session, redirect, request

app = Flask(__name__)

colors = ["ff6666", "f8f1ff", "023c40"] # primary, foreground, background

app.secret_key = 'haha_gamer'

def get_user_spending(acct: int, semester: int, format_output: str, cid=105):
    """Return user spending information."""

    # check the semester ID and update start and end dates accordingly
    if semester == 2221:
        start_date = "2022-08-01"
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
        response = requests.get("https://tigerspend.rit.edu/statementdetail.php", payload)

        # decode the CSV and turn into an array of records
        lines = response.content.decode(response.encoding).splitlines()
        reader = csv.reader(lines)
        return list(reader)
    else:
        return None

def get_daily_spending(csv_file):
    """Process CSV output from TigerSpend into array of total costs per day"""
    daily_spent = dict()

    for record in csv_file:
        # keys in the dictionary are the date on which transactions occurred
        key = record[0].split(" ")[0]
        try:
            if key in daily_spent:
                # add to the sum in the pair
                daily_spent[key] -= round(float(record[2]), 2)
            else:
                # create the key-value pair, and initialize with this record's value
                daily_spent[key] = -round(float(record[2]), 2)
        except ValueError:
            continue
        except IndexError:
            continue
    return daily_spent

def get_spending_over_time(csv_file, days=7, offset=0):
    """Return cost over a certain pay period."""
    daily_spent = get_daily_spending(csv_file)

    money_spent_week = 0
    today = datetime.datetime.today()
    for daydelta in range(offset, days + offset):
        # get the date of the start of the range
        target = datetime.timedelta(days=daydelta)

        # add on the spending per day
        money_spent_week += daily_spent[datetime.datetime.strftime(today - target, "%m/%d/%Y")]
    return money_spent_week

@app.route('/')
def landing():
    """Method run upon landing on the main page."""
    # first check if the skey is already contained in the session
    if 'skey' in session:
        # validate that it is returning an actual csv, and not an HTML
        parsed_csv = [['', '', '', ''], ['', '', '', '']]
        if 'dining_id' in session:
            parsed_csv = get_user_spending(session['dining_id'], 2221, 'csv')
            try:
                # if it returns a csv but it does not contain anything at this point,
                # it means that there is no account under this name
                if parsed_csv[1][2] == '':
                    session.pop('dining_id')
                    return redirect('/')
            except IndexError:
                # if it gets an exception, it's because it returned an HTML,
                # in which case the skey is invalid
                session.pop('skey')
                session.pop('dining_id')
                return redirect('/')
        else:
            # iterate until you find the account id that works for dining dollars
            # locates meal plan in use
            dining_id = 53
            while parsed_csv[1][2] == '':
                dining_id += 1
                parsed_csv = get_user_spending(id, 2221, 'csv')

            # save the meal plan to your session
            session['dining_id'] = id

        # invalidate session, retry authentication
        if len(parsed_csv[0]) < 4:
            session.pop('skey')
            session.pop('dining_id')
            return redirect('/')

        current_date_time = datetime.datetime.today().strftime("%m/%d/%Y")

        #first_date = parsed_csv[-2][0].split(' ')[0]
        current_date = current_date_time.split(' ')[0]
        last_date = "12/14/2022"

        date_format = "%m/%d/%Y"

        # get the number of days until the end of the semester
        delta = datetime.datetime.strptime(last_date, date_format) - datetime.datetime.strptime(current_date, date_format)

        #starting_balance = float(parsed_csv[-1][3]) - float(parsed_csv[-1][2])
        current_balance = float(parsed_csv[1][3])

        # get daily budget based off balance in account yesterday
        daily_budget = round(((current_balance + get_spending_over_time(parsed_csv, 1)) / delta.days), 2)

        # packaging up data to send to template
        data = [current_balance, daily_budget, get_spending_over_time(parsed_csv, 1), get_spending_over_time(parsed_csv, 7), get_spending_over_time(parsed_csv, 30)]

        return render_template("index.html", session=session, data=data)

    return render_template("index.html", session=session)

@app.route('/auth')
def auth():
    """Method for authenticating on /auth"""
    # authenticate user based on redirect from tigerspend with skey enclosed as arg
    if 'skey' in request.args.keys():
        session['skey'] = str(request.args.get('skey'))
    return redirect('/')
