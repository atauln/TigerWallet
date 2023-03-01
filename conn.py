import requests
import time
import os
import csv

from lib import (
    log_to_console, 
    first_date, 
    get_datetimes,
    get_meal_plan_name,
    get_session_value,
    check_session_value
)
import database

from datetime import datetime
from bs4 import BeautifulSoup

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

    _, _, end_date = [date.strftime("%Y-%m-%d") for date in get_datetimes()]

    # send TigerSpend the payload details and get CSV back
    payload = {
        'skey': skey,
        'format': format_output,
        'startdate': first_date.strftime("%Y-%m-%d"),
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

def get_formatted_spending(sess_data: database.SessionData, plan_id: int):
    """Return an array of spending information in the form of Purchase items"""
    response = force_retrieve_spending(sess_data.skey, plan_id)

    result = []
    for item in response:
        if item[0] == "Date":
            continue
        if 'transaction' in item[0]:
            return None
        date = datetime.strptime(item[0], "%m/%d/%Y %H:%M%p")
        location = item[1]
        amount = -1 * float(item[2])
        new_balance = float(item[3])

        result.append(database.Purchases(
            uid=sess_data.uid,
            dt=date,
            location=location,
            amount=amount,
            new_balance=new_balance,
            plan_id=plan_id,
            pid=time.time()
        ))

    return result

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
