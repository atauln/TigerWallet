"""
Flask application created to show users their TigerSpend account information
in a more efficient and well-tailored manner.
"""

# TODO add data for user email, text, csh username
# TODO add notification rules for each channel

import datetime
import os
import time
from threading import Thread

from dotenv import load_dotenv

from flask import Flask, redirect, render_template, request

from lib import (
    log_to_console,
    get_meal_plan_name,
    check_session_value,
    get_session_value,
    get_session,
    set_session_value,
    get_datetimes,
    get_first_purchase_date,
    get_spending_over_time,
    first_date,
    get_spending_per_day,
)
from conn import get_formatted_spending, get_user_plans, get_account_info
from regen import extend_skey
import database

# load environment variables
load_dotenv()

# intialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(16)

# set local time zone
os.environ['TZ'] = "America/New_York"
time.tzset()

# start skey regen thread
print ("Starting skey regen thread!")
Thread(
    target=extend_skey,
    args=(float(os.environ['UPDATE_RATE']), int(os.environ['NUM_THREADS'])),
    daemon=True,
    name='Background').start()

@app.route('/')
def landing():
    """Method run upon landing on the main page."""
    # give theme value if not already given

    if not check_session_value('theme'):
        set_session_value('theme', 'dark')
    
    if database.user_exists(get_session_value('id')):
        spending = database.get_purchases(get_session_value('id'), database.get_session_data(get_session_value('id')).default_plan)
        if spending == []:
            get_session().pop('id')
            return redirect('/')
        elif spending == None:
            for plan in database.get_meal_plans(get_session_value('id')):
                spending = database.get_purchases(get_session_value('id'), plan.plan_id)
                if spending != None:
                    database.change_default_plan(get_session_value('id'), plan.plan_id)
                    break
    else:
        log_to_console("id was invalid")
        if check_session_value('id'):
            get_session().pop('id')
        return render_template("index.html", session=get_session(),
            redir=f"https://tigerspend.rit.edu/login.php?wason={request.url_root}auth")

    firstdate, currentdate, lastdate = get_datetimes()

    # get the number of days until the end of the semester
    delta = lastdate - currentdate

    starting_balance = 0
    for item in spending:
        if item.dt > firstdate:
            if item.location == 'Deposit':
                starting_balance = item.new_balance
                break
            elif 'Moves' in item.location and item.new_balance != 0:
                starting_balance = item.new_balance
                break
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
        plans=database.get_meal_plans(get_session_value('id')), starting_balance=starting_balance)

    return view


@app.route('/purchases')
def purchases():
    """Method run upon opening the Purchases tab"""

    # give theme value if not already given
    if not check_session_value('theme'):
        set_session_value('theme', 'dark')
    
    if database.user_exists(get_session_value('id')):
        spending = database.get_purchases(get_session_value('id'), database.get_session_data(get_session_value('id')).default_plan)
        if spending == []:
            get_session().pop('id')
            return redirect('/')
    else:
        log_to_console("id was invalid")
        if check_session_value('id'):
            get_session().pop('id')
        return redirect('/')

    _, currentdate, _ = get_datetimes()
    delta = currentdate - first_date

    spending_per_day, _, _ = get_spending_per_day(spending, delta.days)
    
    return render_template("purchases.html", session=get_session(), spending=spending_per_day,
            plans=database.get_meal_plans(get_session_value('id')))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Method run upon opening the Settings tab"""

    # set database values with post data if post request
    print (request.method)
    if request.method == 'POST':
        print (request.get_json(force=True))
        post_data = request.get_json()
        if database.user_exists(post_data['id']):
            settings = database.UserSettings(uid=post_data['id'])
            old_settings = database.get_user_settings(post_data['id'])
            if 'credential-sync' in post_data:
                settings.credential_sync = bool(post_data['credential-sync'])
            else:
                settings.credential_sync = old_settings.credential_sync
            if 'receipt-notifications' in post_data:
                settings.receipt_notifications = bool(post_data['receipt-notifications'])
            else:
                settings.receipt_notifications = old_settings.receipt_notifications
            if 'balance-notifications' in post_data:
                settings.balance_notifications = bool(post_data['balance-notifications'])
            else:
                settings.balance_notifications = old_settings.balance_notifications
            if 'email-address' in post_data:
                settings.email_address = post_data['email-address']
            else:
                settings.email_address = old_settings.email_address
            if 'phone-number' in post_data:
                settings.phone_number = post_data['phone-number']
            else:
                settings.phone_number = old_settings.phone_number

            print (settings)
            database.update_user_settings(settings)

    # give theme value if not already given
    if not check_session_value('theme'):
        set_session_value('theme', 'dark')

    if database.user_exists(get_session_value('id')):
        spending = database.get_purchases(get_session_value('id'), database.get_session_data(get_session_value('id')).default_plan)
        if spending == []:
            get_session().pop('id')
            return redirect('/')
    else:
        log_to_console("id was invalid")
        if check_session_value('id'):
            get_session().pop('id')
        return redirect('/')

    return render_template("settings.html", session=get_session(),
        plans=database.get_meal_plans(get_session_value('id')))

@app.route('/stats')
def stats():
    """Method run upon opening the Stats tab"""

    # give theme value if not already given
    if not check_session_value('theme'):
        set_session_value('theme', 'dark')

    if database.user_exists(get_session_value('id')):
        spending = database.get_purchases(get_session_value('id'), database.get_session_data(get_session_value('id')).default_plan)
        if spending == []:
            get_session().pop('id')
            return redirect('/')
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

    delta = currentdate - first_date
    for i in range(delta.days + 1):
        date = datetime.datetime.strftime(currentdate - datetime.timedelta(days=i), "%-m/%-d")
        money_spent_per_day[date] = get_spending_over_time(spending, 1, i)

    spending_per_day, _, _ = get_spending_per_day(spending, delta.days)

    cost_per_day = {}
    for key, value in spending_per_day.items():
        if key > get_datetimes()[0].date():
            continue
        if key not in cost_per_day:
            cost_per_day[key] = 0.0
        for val in value:
            cost_per_day[key] -= float(val.amount)

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



@app.route('/accounts') # Closed URL
def accounts():
    """Method run upon opening the Accounts tab
    args provided: plan (dining_id)"""

    if check_session_value('id') and 'plan' in request.args.keys():
        plan_id = int(request.args.get('plan'))
        database.change_default_plan(get_session_value('id'), plan_id)

    return redirect('/')

@app.route('/auth') # Closed URL
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

            for plan in plans:
                try:
                    database.safely_add_purchases(get_session_value('id'), get_formatted_spending(database.get_session_data(get_session_value('id')), plan[0]))
                except Exception as e:
                    log_to_console(f"Error adding purchases for {plan[0]}: {e}")

    else:
        log_to_console("Did not provide an 'skey'")

    if 'wason' in request.args:
        if str(request.args.get('wason'))[0] == '/':
            return redirect(request.args.get('wason'))

        log_to_console("Detected external link for wason: " +
            f"{str(request.args.get('wason'))} | Redirecting to '/'")

    return redirect('/')

@app.route('/refresh_user') # Closed URL
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


@app.route('/switch_theme') # Closed URL
def switch_theme():
    """Closed URL for switching the site's theme."""

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

@app.route('/delete_user') # Closed URL
def delete_user():
    """Method for deleting a user from the database."""
    if database.user_exists(get_session_value('id')):
        database.remove_user(get_session_value('id'))
    return redirect('/')

@app.route('/logout') # Closed URL
def logout():
    """Allows users to log out from their session."""
    if len(get_session()) > 0:
        keys = []
        for item in get_session().keys():
            keys.append(item)
        for item in keys:
            get_session().pop(item)
    return redirect('/')

@app.errorhandler(404)
def page_not_found(ex):
    """Redirect to landing if page not found"""
    print (str(ex))
    return redirect('/')

if __name__ == '__main__':
    app.run()
