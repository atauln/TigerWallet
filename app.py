"""
Flask application created to show users their TigerSpend account information
in a more efficient and well-tailored manner.
"""

import datetime
import os
import time
import csv
from threading import Thread
import requests

from dotenv import load_dotenv

from flask import Flask, redirect, render_template, request, session

from bs4 import BeautifulSoup

import copy

import database


# load environment variables
load_dotenv()

# intialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(16)

# set local time zone
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
    if check_session_value(key):
        return session[key]
    return ""

def get_session():
    """Get the session object"""
    return session

# dictionary of datetimes for all semesters
# select the currect semester with evironmental variables
semester_times = {
    2221: {
        "start": datetime.datetime(2022, 7, 1, 0, 0, 0),
        "end": datetime.datetime(2022, 12, 15, 0, 0, 0)
    },
    2225: {
        "start": datetime.datetime(2022, 12, 15, 0, 0, 0),
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

    # Using the second to last result is important, as 
    # the last result is the deposit date, which is
    # not a purchase date
    date_string = spending[-2][0].split(" ")[0]
    return datetime.datetime.strptime(date_string, "%m/%d/%Y")

def get_meal_plan_name(plan_id):
    """Gets the name for a plan based on it's ID"""
    meal_plans = {
        1: "TigerBucks",
        24: "Voluntary Dining",
        29: "Rollover",
        54: "Orange Plan",
        55: "Tiger Plan"
    }
    if plan_id in meal_plans:
        return meal_plans[plan_id]
    return "Meal Plan"

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
        return ""

    return response.status_code

def verify_skey_integrity(skey):
    """Verifies the integrity of the skey."""

    payload = {
        'cid': 105,
        'skey': skey,
        'acct': 1
    }
    count = 0
    while count < 10:
        try:
            response = requests.get(
                "https://tigerspend.rit.edu/statementdetail.php",
                payload
            )
            break
        except ConnectionError:
            # there has to be a better way to do this
            # look into using something other than the
            # vanilla requests library
            count += 1
        time.sleep(.1)

    if len(response.history) != 0:
        return False
    return True


def force_retrieve_spending(skey, acct, format_output = 'csv', cid = 105):
    """Return user spending information.
    This should be used very carefully, as it does not check for values."""

    start_date, _, end_date = [date.strftime("%Y-%m-%d") for date in get_datetimes()]

    # send TigerSpend the payload details and get CSV back
    payload = {
        'skey': skey,
        'format': format_output,
        'startdate': start_date,
        'enddate': end_date,
        'acct': acct,
        'cid': cid
    }
    try:
        response = requests.get(
            "https://tigerspend.rit.edu/statementdetail.php",
            payload
        )
    except requests.exceptions.ConnectionError:
        log_to_console("Failed to connect to TigerSpend!")
        return '[]'

    lines = response.content.decode(response.encoding).splitlines()
    reader = csv.reader(lines)
    result = list(reader)
    #try:
    #    json_result = json.loads(result)
    #except json.JSONDecodeError:
    #    print (f'failed lol {result}')
    #    return '[]'

    return result

def get_formatted_spending(sess_data: database.SessionData, plan_id: int) -> list[database.Purchases]:
    """Return an array of spending information in the form of Purchase items"""
    response = force_retrieve_spending(sess_data.skey, plan_id)

    result = []
    for item in response:
        if item[0] == "Date":
            continue
        date = datetime.datetime.strptime(item[0], "%m/%d/%Y %H:%M%p")
        location = process_location(item[1])
        amount = -1 * float(item[2])
        new_balance = float(item[3])

        result.append(database.Purchases(
            uid=sess_data.uid,
            dt=date,
            location=location,
            amount=amount,
            new_balance=new_balance,
            plan_id=sess_data.default_plan,
            pid=time.time()
        ))

    return result

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
        log_to_console(f"Ran into error while finding user accounts, {response.url}")

    return [( plan.attrs['value'], get_meal_plan_name(int(plan.attrs['value'])) ) for plan in options]


def get_account_info(skey, cid=105):
    """Get the user's account information from their account page."""

    if check_session_value('id'):
        return [
            get_session_value("id"),
            database.get_user(get_session_value("id")).first_name,
            database.get_user(get_session_value("id")).last_name,
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

    return account_data # [account_id, first_name, last_name]



def get_daily_spending(purchases):
    """Process CSV output from TigerSpend into array of total costs per day"""
    daily_spent = {}

    for purchase in purchases:
        # keys in the dictionary are the date on which transactions occurred
        key = purchase.dt.strftime("%-m/%d/%Y")
        try:
            if not key in daily_spent:
                daily_spent[key] = 0
            daily_spent[key] += round(purchase.amount, 2)
        except ValueError:
            continue
        except IndexError:
            continue
    return daily_spent


def get_spending_over_time(purchases, days=7, backwards_offset=0):
    """Return cost over a certain pay period."""
    daily_spent = get_daily_spending(purchases)

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
        "FOOD": "Vending Machine (FOOD)",
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
        "Deposit": "Deposit",
        "Moves": "Transfer to Rollover"
    }

    for item in locations.items():
        if item[0] in raw_location:
            if "OnDemand" in raw_location:
                return item[1] + " (Online)"
            return item[1]
    return None

def get_spending_per_day(spending, days):
    """Uses the spending to generate a dictionary of spending per day"""
    a_sum = 0
    count = 0
    spending_a = {}
    for i in range(days):
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
    return spending_a, a_sum, count

# def update_based_on_skey(entry):
#     """Update the value based on an skey
#     Made for extend_skey()"""
#     if not verify_skey_integrity(entry[1]):
#         remove_user(str(entry[0]))
#     else:
#         acct_id = str(retrieve_db_values(entry[0], 'dining_id')[0][0]).replace("'", "\"")
#         update_db_value(
#             'spending',
#             str(force_retrieve_spending(entry[1], acct_id)),
#             str(entry[0])
#         )
#         update_db_value(
#             'statement_date',
#             datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S"),
#             str(entry[0])
#         )

# def extend_skey(minutes):
#     """Extends all skey's in the database"""
#     while True:
#         sql = 'SELECT id, skey FROM account_data'
#         values = execute_sql(sql, False, True, [])

#         for entry in [entry for entry in values if entry[1] != '']:
#             Thread(target=update_based_on_skey, args=(entry,), name='SkeyUpdate').start()
#         time.sleep(minutes * 60)

# print ("Starting skey regen thread!")
# Thread(
#     target=extend_skey,
#     args=(int(os.environ['UPDATE_RATE']),),
#     daemon=True,
#     name='Background').start()

@app.route('/')
def landing():
    """Method run upon landing on the main page."""
    # give theme value if not already given

    print (session)

    if not check_session_value('theme'):
        set_session_value('theme', 'dark')
    
    if database.user_exists(get_session_value('id')):
        spending = get_formatted_spending(database.get_session_data(get_session_value('id')), database.get_session_data(get_session_value('id')).default_plan)
        # check if the skey is contained within the db
    else:
        log_to_console("id was invalid")
        if check_session_value('id'):
            get_session().pop('id')
        return render_template("index.html", session=get_session(),
            redir=f"https://tigerspend.rit.edu/login.php?wason={request.url_root}auth")

    _, currentdate, lastdate = get_datetimes()

    # get the number of days until the end of the semester
    delta = lastdate - currentdate

    #starting_balance = float(spending[-1][3]) - float(spending[-1][2])
    current_balance = float(spending[0].new_balance)

    # get daily budget based off balance in account yesterday
    daily_budget = round(
        ((current_balance - get_spending_over_time(spending, 1)) / delta.days), 2)

    if daily_budget == 0:
        daily_budget = 1

    # packaging up data to send to template
    data = [current_balance, daily_budget,
        get_spending_over_time(spending, 1),
        get_spending_over_time(spending, 7, 1),
        get_spending_over_time(spending, 30, 1)]

    view = render_template("index.html", session=get_session(), data=data,
        records=spending, plan_name=get_meal_plan_name(database.get_session_data(get_session_value('id')).default_plan),
        plans=database.get_meal_plans(get_session_value('id')))

    database.safely_add_purchases(get_session_value('id'), spending)

    return view


@app.route('/purchases')
def purchases():
    """Method run upon opening the Purchases tab"""

    # give theme value if not already given
    if not check_session_value('theme'):
        set_session_value('theme', 'dark')

    if database.user_exists(get_session_value('id')):
        spending = get_formatted_spending(database.get_session_data(get_session_value('id')))
        # check if the skey is contained within the db
    else:
        log_to_console("id was invalid")
        if check_session_value('id'):
            get_session().pop('id')
        return render_template("index.html", session=get_session(),
            redir=f"https://tigerspend.rit.edu/login.php?wason={request.url_root}auth")

    firstdate, currentdate, _ = get_datetimes()
    delta = currentdate - firstdate

    spending_per_day, _, _ = get_spending_per_day(spending, delta.days)

    return render_template("purchases.html", session=get_session(), spending=spending_per_day,
            plans=database.get_meal_plans(get_session_value('id')))

@app.route('/stats')
def stats():
    """Method run upon opening the Stats tab"""

    # give theme value if not already given
    if not check_session_value('theme'):
        set_session_value('theme', 'dark')

    if database.user_exists(get_session_value('id')):
        spending = get_formatted_spending(database.get_session_data(get_session_value('id')))
        # check if the skey is contained within the db
    else:
        log_to_console("id was invalid")
        if check_session_value('id'):
            get_session().pop('id')
        return render_template("index.html", session=get_session(),
            redir=f"https://tigerspend.rit.edu/login.php?wason={request.url_root}auth")

    _, currentdate, enddate = get_datetimes()
    firstdate = get_first_purchase_date(spending)
    sincefirst = currentdate - firstdate
    totaldays = enddate - firstdate

    balance = float(spending[0].new_balance)
    deposit = -1 * float(spending[-1].amount)
    recommended_balance = (deposit / totaldays.days) * sincefirst.days

    money_spent_per_day = {}

    delta = currentdate - firstdate
    for i in range(delta.days + 1):
        date = datetime.datetime.strftime(currentdate - datetime.timedelta(days=i), "%-m/%-d")
        money_spent_per_day[date] = get_spending_over_time(spending, 1, i)

    spending_per_day, _, _ = get_spending_per_day(spending, delta.days)

    cost_per_day = {}
    for key, value in spending_per_day.items():
        if key not in cost_per_day:
            cost_per_day[key] = 0.0
        for val in value:
            cost_per_day[key] += float(val[2])

    return render_template("stats.html", session=get_session(),
        balance=balance, deposit=deposit,
        recommended_balance = recommended_balance,
        plans=database.get_meal_plans(get_session_value('id')),
        cost_per_day=cost_per_day)

##@app.route('/vending', methods=['GET', 'POST'])
##def vending():
##    """Vending form"""
##
##    # give theme value if not already given
##    if not check_session_value('theme'):
##        set_session_value('theme', 'dark')
##
##    if request.method == 'POST':
##        vending_id = request.form['id']
##        vending_type = request.form['type']
##        building = request.form['building']
##        floor = request.form['floor']
##        if not (vending_id or vending_type or building or floor):
##            return render_template('vending.html', success=False)
##        open_db()
##        try:
##            sql = "INSERT INTO VendingMachineLocations (id, type, building, floor) "
##            sql += "VALUES (%s, %s, %s, %s)"
##            val = (
##                vending_id,
##                vending_type,
##                building,
##                floor
##            )
##            execute_sql(sql, True, False, val)
##            return render_template('vending.html', success=True)
##        except mysql.connector.errors.IntegrityError as ex:
##            print (ex)
##            return render_template('vending.html', duplicate=True)
##        except Exception as ex:
##            print (ex)
##            return render_template('vending.html')
##
##    return render_template('vending.html')



@app.route('/accounts')
def accounts():
    """Method run upon opening the Accounts tab
    args provided: plan (dining_id)"""

    if check_session_value('id') and 'plan' in request.args.keys():
        plan_id = int(request.args.get('plan'))
        database.change_default_plan(get_session_value('id'), plan_id)

    return redirect('/')

@app.route('/auth')
def auth():
    """Method for authenticating on /auth"""
    # authenticate user based on redirect from tigerspend with skey enclosed as arg

    if not check_session_value('theme'):
        set_session_value('theme', 'dark')

    if 'skey' in request.args.keys():
        skey = str(request.args.get('skey'))
        account_info = get_account_info(skey)
        set_session_value('id', account_info[0])

        if database.user_exists(account_info[0]):
            database.log_user_auth(account_info[0])
            database.update_skey(account_info[0], skey)

        else:
            plans = get_user_plans(skey)

            database.create_user(
                get_session_value('id'),
                account_info[1],
                account_info[2],
                account_info[1],
                skey,
                plans[0][0],
                plans
            )
            # no database queries before this point

    else:
        log_to_console("Did not provide an 'skey'")

    if 'wason' in request.args:
        if str(request.args.get('wason'))[0] == '/':
            return redirect(request.args.get('wason'))

        log_to_console("Detected external link for wason: " +
            f"{str(request.args.get('wason'))} | Redirecting to '/'")

    return redirect('/')

@app.route('/refresh_user')
def refresh_user():
    if database.user_exists(get_session_value('id')):
        skey = str(database.get_session_data(get_session_value('id')).skey)
        account_info = get_account_info(skey)
        set_session_value('id', account_info[0])

        database.update_user(
            get_session_value('id'),
            account_info[1],
            account_info[2],
            account_info[1],
            skey
        )

        database.replace_meal_plans(
            get_session_value('id'),
            [database.MealPlans(
                uid=get_session_value('id'),
                plan_id=plan[0],
                plan_name=plan[1],
                pid=time.time()
            ) for plan in get_user_plans(skey)]
        )
    
    return redirect('/')


@app.route('/switch_theme')
def switch_theme():
    """Closed URL for switching the site's theme."""

    # give theme value if not already given
    # light = 1
    # dark = 0
    if database.user_exists(get_session_value('id')):
        session_data = database.get_session_data(get_session_value('id'))
        theme = session_data.theme
        if theme == 'dark':
            database.change_user_theme(get_session_value('id'), 'light')
        else:
            database.change_user_theme(get_session_value('id'), 'dark')
        session_data = database.get_session_data(get_session_value('id'))
        set_session_value('theme', session_data.theme)
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
