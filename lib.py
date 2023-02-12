import datetime
import os

import database

from flask import session, request

# dictionary of datetimes for all semesters
# select the currect semester with evironmental variables
first_date = datetime.datetime(2010, 7, 1, 0, 0, 0)

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

def get_first_purchase_date(spending: list[database.Purchases]) -> datetime.datetime:
    """Returns the first date of purchase"""

    # Using the second to last result is important, as 
    # the last result is the deposit date, which is
    # not a purchase date
    return spending[-2].dt

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

def log_to_console(message):
    """Simple function to send message to the console
    in a consistent manner."""
    if check_session_value("id"):
        print(f"GET {get_session_value('id')} @ {request.url} -> {message}")
    else:
        print(f"GET {request.remote_addr} @ {request.url} -> {message}")

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
        "MILK": "Vending Machine (Milk)",
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
    print(f"got nothing for: {raw_location}")
    return "Unknown"

def get_spending_per_day(spending: list[database.Purchases], days):
    """Uses the spending to generate a dictionary of spending per day"""
    a_sum = 0
    count = 0
    spending_a = { (datetime.datetime.today() - datetime.timedelta(days=i)).date(): [] for i in range(days)}
    for purchase in list(spending):
        purchase.location = process_location(purchase.location)
        purchase.amount *= -1
        a_sum += purchase.amount
        count += 1
        if purchase.dt.date() not in spending_a:
            spending_a[purchase.dt.date()] = []
        spending_list = spending_a[purchase.dt.date()]
        spending_list.append(purchase)
    return spending_a, a_sum, count
