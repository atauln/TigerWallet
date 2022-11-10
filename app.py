"""
Flask application created to show users their TigerSpend account information
in a more efficient and well-tailored manner.
"""

import datetime
import os
import time

import csv
import json
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session
import requests
from bs4 import BeautifulSoup
import mysql.connector

load_dotenv()

mydb = mysql.connector.connect(
  host = os.environ['DB_URL'],
  user = os.environ['DB_USERNAME'],
  password = os.environ['DB_PASSWORD'],
  database = os.environ['DB_USERNAME']
)

app = Flask(__name__)
app.secret_key = os.urandom(16)

os.environ['TZ'] = "America/New_York"
time.tzset()

def set_session_value(key, value):
    """Sets a session value for the user session"""
    session[key] = value

def check_session_value(key):
    """Check to see if a value is in the user's session"""
    return key in session

def get_session_value(key):
    """Return a value from the session"""
    return session[key]

def get_session():
    """Get the session object"""
    return session

def extend_skey():
    """Extends the lifetime of an skey"""
    sql = 'SELECT id, skey FROM account_data'

    mycursor = mydb.cursor()
    mycursor.execute(sql)

    for entry in [entry for entry in mycursor.fetchall() if entry[1] != '']:
        skey = entry[1]
        payload = {
            'skey': skey
        }
        response = requests.get(
            "https://tigerspend.rit.edu/statementdetail.php",
            payload
        )

        lines = response.content.decode(response.encoding).splitlines()
        reader = csv.reader(lines)

        if len(list(reader)[0]) == 1:
            update_sql = f"UPDATE account_data SET skey = '', spending = '' WHERE id = '{entry[0]}'"

            mycursor2 = mydb.cursor()
            mycursor2.execute(update_sql)

            mydb.commit()

# dictionary of datetimes for all semesters
# select the currect semester with evironmental variables
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
    """Returns datetimes for the current semester"""
    return (
        semester_times[int(os.getenv("CURRENT_SEMESTER"))]["start"],
        datetime.datetime.today(),
        semester_times[int(os.getenv("CURRENT_SEMESTER"))]["end"]
    )

def get_date_strings():
    """Returns formatted date strings for the current semester"""
    return (
        semester_times[int(os.getenv("CURRENT_SEMESTER"))]["start"].strftime("%-m/%d/%Y"),
        datetime.datetime.today().strftime("%-m/%d/%Y"),
        semester_times[int(os.getenv("CURRENT_SEMESTER"))]["end"].strftime("%-m/%d/%Y")
    )

def get_first_purchase_date(spending):
    """Returns the first date of purchase"""
    date_string = spending[-2][0].split(" ")[0]
    return datetime.datetime.strptime(date_string, "%m/%d/%Y")

def get_meal_plan_name(plan_id):
    """Gets the name for a plan based on it's ID"""
    meal_plans = {
        1: "TigerBucks",
        24: "Voluntary Dining",
        29: "Rollover"
    }
    if plan_id in meal_plans:
        return meal_plans[plan_id]
    return "Meal Plan"

def update_db_value(col, value, account_id=""):
    """Update a value for a user"""
    if account_id == "":
        account_id = get_account_info(get_db_value('skey'))[0]

    sql = f'UPDATE account_data SET {col} = "{value}" WHERE id = "{account_id}"'

    mycursor = mydb.cursor()
    mycursor.execute(sql)

    mydb.commit()

def retrieve_db_values(account_id, *args):
    """Retrieve columns from a database"""
    sql = "SELECT "
    for arg in args:
        sql += str(arg) + ", "
    sql = sql[:-2]
    sql += f" FROM account_data WHERE id = '{account_id}'"

    mycursor = mydb.cursor()
    mycursor.execute(sql)

    return mycursor.fetchall()

def check_db_value(key):
    """Checks a value for a user in the database"""
    if not check_session_value('id'):
        return False
    values = retrieve_db_values(get_session_value('id'), key)
    if len(values) == 0:
        return False
    if values is None or values == [] or values == "" or values == 0:
        return False
    if len(values) > 0:
        if values[0] == '':
            return False
        if len(values[0]) > 0:
            if values[0][0] == '':
                return False
    return True

def get_db_value(key):
    """Gets a value for a user in the database"""
    return str(retrieve_db_values(get_session_value("id"), key)[0][0]).replace("'", "\"")

def load_spending(acct_id):
    """Gets spending from the db"""
    if check_db_value('id'):
        statement_date = datetime.datetime.strptime(
            get_db_value('statement_date'),
            "%m/%d/%Y %H:%M:%S"
        )
        deadline = statement_date + datetime.timedelta(minutes=10)
        if deadline < datetime.datetime.now() or acct_id != get_db_value('dining_id'):
            print ("regenerating statement")
            update_db_value(
                'spending',
                str(force_retrieve_spending(get_db_value('skey'), acct_id))
            )
            update_db_value('statement_date', datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S"))
            update_db_value('dining_id', acct_id)
    else:
        return None

    spending = json.loads(str(get_db_value('spending')).replace("\\", "").replace("'", "\""))
    if len(spending[0]) != 4:
        get_session().pop('id')
    if spending[1][3] == '':
        return load_spending(json.loads(get_db_value('plans'))[0][0])

    return spending

def log_to_console(message):
    """Simple function to send message to the console
    in a consistent manner."""
    if check_session_value("id"):
        print(f"GET {get_session_value('id')} @ {request.url} -> {message}")
    else:
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
        response = requests.post(
            f"https://pings.csh.rit.edu/service/route/{subject_uuid}/ping",
            timeout=7,
            headers=headers,
            json=payload
        )
    except requests.exceptions.ChunkedEncodingError:
        log_to_console("Failed to access os env var 'PINGS_TOKEN'!")

    return response.status_code

def verify_skey_integrity(skey):
    """Verifies the integrity of the skey."""

    payload = {
        'cid': 105,
        'skey': skey
    }

    if check_db_value('dining_id'):
        payload['acct'] = get_db_value('dining_id')

    response = requests.get(
        "https://tigerspend.rit.edu/statementdetail.php",
        payload
    )

    if len(response.history) != 0:
        return False
    return True


def get_user_spending(acct: int, format_output: str, cid=105):
    """Return user spending information."""

    # check the semester ID and update start and end dates accordingly
    start_date = semester_times[int(os.getenv("CURRENT_SEMESTER"))]["start"].strftime("%Y-%m-%d")
    end_date = semester_times[int(os.getenv("CURRENT_SEMESTER"))]["end"].strftime("%Y-%m-%d")

    if 'skey' in session:
        if check_session_value('statement_date'):
            statement_date = datetime.datetime.strptime(
                get_session_value('statement_date'),
                "%m/%d/%Y %H:%M:%S"
            )
            if statement_date + datetime.timedelta(minutes=10) < datetime.datetime.now():
                session.pop('statement_date')
                if check_db_value('statement_date'):
                    update_db_value('statement_date', '')
                    update_db_value('spending', '')
        if check_db_value('statement_date'):
            statement_date = datetime.datetime.strptime(
                get_db_value('statement_date')[0],
                "%m/%d/%Y %H:%M:%S"
            )
            if statement_date + datetime.timedelta(minutes=10) < datetime.datetime.now():
                if check_session_value('statement_date'):
                    session.pop('statement_date')
                update_db_value('spending', '')
                update_db_value('statement_date', '')
        if not check_db_value('spending') or int(get_db_value('dining_id')[0]) != acct:
            # send TigerSpend the payload details and get CSV back
            # only done if the statement is not already in the session
            payload = {
                'skey': session['skey'],
                'format': format_output,
                'startdate': start_date,
                'enddate': end_date,
                'acct': acct,
                'cid': cid
            }

            response = requests.get(
                "https://tigerspend.rit.edu/statementdetail.php",
                payload
            )

            lines = response.content.decode(response.encoding).splitlines()
            reader = csv.reader(lines)

            set_session_value('statement_date',
                datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S"))
            update_db_value('statement_date', get_session_value('statement_date'))
            update_db_value(
                'spending',
                str(list(reader))
                    .replace("Sol's", "Sols")
                    .replace("Jerry's", "Jerrys")
                    .replace("Gracie's", "Gracies")
                    .replace("Nathan's", "Nathans")
                    .replace("\"", "'")
            )
        back =  str(get_db_value('spending')[0]).replace("\\", "").replace("'", "\"")
        return json.loads(back)
    return None

def force_retrieve_spending(skey, acct, format_output = 'csv', cid = 105):
    """Return user spending information.
    This should be used very carefully, as it does not check for values."""

    # check the semester ID and update start and end dates accordingly
    start_date = semester_times[int(os.getenv("CURRENT_SEMESTER"))]["start"].strftime("%Y-%m-%d")
    end_date = semester_times[int(os.getenv("CURRENT_SEMESTER"))]["end"].strftime("%Y-%m-%d")

    # send TigerSpend the payload details and get CSV back
    # only done if the statement is not already in the session
    payload = {
        'skey': skey,
        'format': format_output,
        'startdate': start_date,
        'enddate': end_date,
        'acct': acct,
        'cid': cid
    }

    response = requests.get(
        "https://tigerspend.rit.edu/statementdetail.php",
        payload
    )

    lines = response.content.decode(response.encoding).splitlines()
    reader = csv.reader(lines)
    result = str(list(reader)).replace("Sol's", "Sols").replace("Jerry's", "Jerrys")
    result = result.replace("Nathan's", "Nathans").replace("Gracie's", "Gracies").replace("'", "\"")
    try:
        json_result = json.loads(result)
    except json.JSONDecodeError:
        print ("skey must be invalid")
        return '[]'

    return json_result


def get_user_plans(skey, cid=105):
    """Get a list of all the user's plans and return the first one."""

    payload = {
        'skey': skey,
        'cid': cid
    }
    response = requests.get(
        "https://tigerspend.rit.edu/statementnew.php",
        payload
    )
    soup = BeautifulSoup(response.content, 'html.parser')
    try:
        options = soup.find(id="select-account").find_all('option')
    except AttributeError:
        log_to_console("Ran into error while finding user accounts")
        return None

    return [[plan.attrs['value'], get_meal_plan_name(int(plan.attrs['value']))] for plan in options]


def get_account_info(skey, cid=105):
    """Get the user's account information from their account page."""

    if check_session_value('id'):
        return [
            get_session_value("id"),
            get_db_value("first_name"),
            get_db_value("last_name")
        ]

    payload = {
        'skey': skey,
        'cid': cid
    }
    response = requests.get(
        "https://tigerspend.rit.edu/statementnew.php", payload)

    soup = BeautifulSoup(response.content, 'html.parser')
    options = soup.find("div", {"class": "jsa_account-info"}).find_all("b")

    name = options[0].getText().replace("'", "").split(" ")
    options[1] = str(options[1]).strip("<b>")
    options[1] = str(options[1]).strip("</b>") # lmao this is so cursed

    account_data = [
        str(name[0][0]).lower() + str(name[1]).lower() + str(options[1]).strip('X'), # account_id
        str(name[0]).replace("'", ""), # first_name
        str(name[1]).replace("'", ""), # last_name
    ]

    return account_data



def get_daily_spending(csv_file):
    """Process CSV output from TigerSpend into array of total costs per day"""
    daily_spent = {}

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


def get_spending_over_time(csv_file, days=7, backwards_offset=0):
    """Return cost over a certain pay period."""
    daily_spent = get_daily_spending(csv_file)

    money_spent = 0
    today = datetime.datetime.today()
    for daydelta in range(backwards_offset, days + backwards_offset):
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
    return round(money_spent, 2)


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
        "Petals": "RIT Inn Petals",
        "Deposit": "Deposit"
    }

    for item in locations.items():
        if item[0] in raw_location:
            if "OnDemand" in raw_location:
                return item[1] + " (Online)"
            return item[1]
    return None

@app.route('/')
def landing():
    """Method run upon landing on the main page."""
    # give theme value if not already given
    if not check_session_value('theme'):
        set_session_value('theme', 'dark')
    if check_db_value('id'):
        spending = load_spending(get_db_value('dining_id'))

    # check if the skey is contained within the db
    if not check_db_value('id'):
        log_to_console("id was invalid")
        if check_session_value('id'):
            get_session().pop('id')
        return render_template("index.html", session=get_session(),
            redir=f"https://tigerspend.rit.edu/login.php?wason={request.url_root}auth")

    _, currentdate, lastdate = get_datetimes()

    # get the number of days until the end of the semester
    delta = lastdate - currentdate

    #starting_balance = float(spending[-1][3]) - float(spending[-1][2])
    current_balance = float(spending[1][3])

    # get daily budget based off balance in account yesterday
    daily_budget = round(
        ((current_balance - get_spending_over_time(spending, 1)) / delta.days), 2)

    if daily_budget == 0:
        daily_budget = 1

    first_name = get_db_value('first_name')

    # packaging up data to send to template
    data = [current_balance, daily_budget,
        get_spending_over_time(spending, 1),
        get_spending_over_time(spending, 7, 1),
        get_spending_over_time(spending, 30, 1),
        first_name]

    return render_template("index.html", session=get_session(), data=data,
        records=spending, plan_name=get_meal_plan_name(get_db_value('dining_id')),
        plans=json.loads(get_db_value('plans')))


@app.route('/purchases')
def daily():
    """Method run upon opening the Purchases tab"""

    # give theme value if not already given
    if not check_session_value('theme'):
        set_session_value('theme', 'dark')

    if check_db_value('id'):
        spending = load_spending(get_db_value('dining_id'))

    # check if the skey is contained within the db
    if not check_db_value('id'):
        log_to_console("id was invalid")
        if check_session_value('id'):
            get_session().pop('id')
        return render_template("index.html", session=get_session(),
            redir=f"https://tigerspend.rit.edu/login.php?wason={request.url_root}auth")

    firstdate, currentdate, _ = get_datetimes()

    spending_a = {}

    a_sum = 0
    count = 0

    delta = currentdate - firstdate
    for i in range(delta.days):
        date = datetime.datetime.today() - datetime.timedelta(days=i)
        date_processed = date.strftime("%-m/%d/%Y")
        if date_processed not in spending_a:
            spending_a[date_processed] = []
        for purchase in list(spending):
            if str(purchase[0]).split(" ", maxsplit=1)[0] == date_processed:
                purchase[1] = process_location(purchase[1])
                purchase[2] = float(purchase[2]) * -1
                purchase[3] = float(purchase[3])
                a_sum += purchase[2]
                count += 1
                spending_list = spending_a[date_processed]
                spending_list.append(purchase)

    return render_template("purchases.html", session=get_session(), spending=spending_a)

@app.route('/stats')
def stats():
    """Method run upon opening the Stats tab"""

    # give theme value if not already given
    if not check_session_value('theme'):
        set_session_value('theme', 'dark')

    if check_db_value('id'):
        spending = load_spending(get_db_value('dining_id'))

    # check if the skey is contained within the db
    if not check_db_value('id'):
        log_to_console("id was invalid")
        if check_session_value('id'):
            get_session().pop('id')
        return render_template("index.html", session=get_session(),
            redir=f"https://tigerspend.rit.edu/login.php?wason={request.url_root}auth")

    _, currentdate, enddate = get_datetimes()
    firstdate = get_first_purchase_date(spending)
    sincefirst = currentdate - firstdate
    totaldays = enddate - firstdate

    balance = float(list(spending)[1][3])
    deposit = float(str(list(spending)[-1][2]).strip("-"))
    recommended_balance = (deposit / totaldays.days) * sincefirst.days

    money_spent_per_day = {}

    delta = currentdate - firstdate
    for i in range(delta.days + 1):
        date = datetime.datetime.strftime(currentdate - datetime.timedelta(days=i), "%-m/%-d")
        money_spent_per_day[date] = get_spending_over_time(spending, 1, i)

    return render_template("stats.html", session=get_session(),
        balance=balance, deposit=deposit,
        recommended_balance = recommended_balance)

@app.route('/accounts')
def accounts():
    """Method run upon opening the Accounts tab
    args provided: plan (dining_id)"""

    if check_db_value('id') and 'plan' in request.args:
        load_spending(int(request.args.get('plan')))
        update_db_value('dining_id', int(request.args.get('plan')))

    return redirect('/')

@app.route('/auth')
def auth():
    """Method for authenticating on /auth"""
    # authenticate user based on redirect from tigerspend with skey enclosed as arg

    if not check_session_value('theme'):
        set_session_value('theme', 'dark')

    if 'skey' in request.args.keys():
        skey = str(request.args.get('skey'))
        current_datetime = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")

        if check_db_value('id'):
            update_db_value('skey', skey)
            update_db_value('last_signed_in', current_datetime)
        else:
            account_info = get_account_info(skey)
            set_session_value('id', account_info[0])
            plans = get_user_plans(skey)
            spending = force_retrieve_spending(skey, plans[0][0], 'csv')
            sql = "INSERT INTO account_data (id, first_name, last_name, plans, skey, spending, "
            sql += "theme, dining_id, statement_date, last_signed_in, first_signed_in) VALUES "
            sql += "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            val = (
                get_session_value('id'),
                account_info[1],
                account_info[2],
                str(plans),
                skey,
                str(spending),
                get_session_value('theme'),
                plans[0][0],
                current_datetime,
                current_datetime,
                current_datetime
            )
            mycursor = mydb.cursor()
            mycursor.execute(sql, val)

            mydb.commit()
    else:
        log_to_console("Did not provide an 'skey'")

    if 'wason' in request.args:
        if str(request.args.get('wason'))[0] == '/':
            return redirect(request.args.get('wason'))

        log_to_console("Detected external link for wason: " +
            f"{str(request.args.get('wason'))} | Redirecting to '/'")

    return redirect('/')


@app.route('/switch_theme')
def switch_theme():
    """Closed URL for switching the site's theme."""
    if check_db_value('id'):
        theme = get_db_value('theme')
        if theme == 'dark':
            update_db_value('theme', 'light')
        else:
            update_db_value('theme', 'dark')
        set_session_value('theme', get_db_value('theme'))
    else:
        if not check_session_value('theme'):
            set_session_value('theme', 'dark')
        elif get_session_value('theme') == 'dark':
            set_session_value('theme', 'light')
        elif get_session_value('theme') == 'light':
            set_session_value('theme', 'dark')
        else:
            set_session_value('theme', 'dark')

    if 'wason' in request.args:
        if str(request.args.get('wason'))[0] != '/':
            log_to_console("Detected external link for wason:" +
                f"{str(request.args.get('wason'))} | Redirecting to '/'")
            return redirect('/')

    return redirect(request.args.get('wason'))

@app.route('/logout')
def logout():
    """Allows users to log out from their session."""
    if len(session) > 0:
        keys = []
        for item in session.keys():
            keys.append(item)
        for item in keys:
            session.pop(item)
    return redirect('/')


@app.errorhandler(404)
def page_not_found(ex):
    """Redirect to landing if page not found"""
    print (str(ex))
    return redirect('/')

if __name__ == '__main__':
    app.run()
