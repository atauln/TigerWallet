import datetime
import math
from flask import Flask, render_template, session, redirect, request
import requests, csv

# add session integration to store skey's
app = Flask(__name__)

colors = ["ff6666", "f8f1ff", "023c40"] # primary, foreground, background

app.secret_key = 'haha_gamer'
auth_url = "https://tigerspend.rit.edu/login.php?wason=http://localhost:8080/auth"

def getuserspending(acct: int, semester: int, format: str, cid=105):
    # url format: /statementdetail.php?cid=105&skey=8d2d0fe099b501450e05961309c76907&format=csv&startdate=2022-04-01&enddate=2022-10-30&acct=55
    if semester == 2221:
        start_date = "2022-08-01"
        end_date = "2022-12-15"

    if 'skey' in session:
        payload = {'skey': session['skey'], 'format': format, 'startdate': start_date, 'enddate': end_date, 'acct': acct, 'cid': cid}
        response = requests.get("https://tigerspend.rit.edu/statementdetail.php", payload)

        lines = response.content.decode(response.encoding).splitlines()
        reader = csv.reader(lines)
        return list(reader)
    else:
        return None

def get_daily_spending(csv_file):
    daily_spent = dict()
    for record in csv_file:
        if len(record) < 4:
            continue
        key = record[0].split(" ")[0]
        try:
            float(record[2])
        except ValueError:
            continue
        except IndexError:
            continue
        if key in daily_spent.keys():
            daily_spent[key] -= round(float(record[2]), 2)
        else:
            daily_spent[key] = -round(float(record[2]), 2)
    return daily_spent

def get_spending_over_time(csv_file, days=7):
    daily_spent = get_daily_spending(csv_file)
    money_spent_week = 0
    for daydelta in range(days):
        try:
            money_spent_week += daily_spent[datetime.datetime.strftime(datetime.datetime.today() - datetime.timedelta(days=daydelta), "%m/%d/%Y")]
        except:
            continue
    return money_spent_week




@app.route('/')
def landing():

    if 'skey' in session:
        parsed_csv = getuserspending(55, 2221, 'csv')

        if len(parsed_csv[0]) < 4:
            session.pop('skey')
            return redirect('/')

        current_date_time = datetime.datetime.today().strftime("%m/%d/%Y")
        

        #first_date = parsed_csv[-2][0].split(' ')[0]
        current_date = current_date_time.split(' ')[0]
        last_date = "12/14/2022"

        date_format = "%m/%d/%Y"
        delta = datetime.datetime.strptime(last_date, date_format) - datetime.datetime.strptime(current_date, date_format)

        #starting_balance = float(parsed_csv[-1][3]) - float(parsed_csv[-1][2])
        current_balance = float(parsed_csv[1][3])

        daily_budget = round((current_balance / delta.days), 2)

        data = [current_balance, daily_budget, get_spending_over_time(parsed_csv, 1), get_spending_over_time(parsed_csv, 7), get_spending_over_time(parsed_csv, 30)]


        return render_template("index.html", session=session, data=data)

    return render_template("index.html", session=session)

@app.route('/auth')
def auth():
    for item in request.args.items():
        print(item[0], item[1])
    if 'skey' in request.args.keys():
        session['skey'] = str(request.args.get('skey'))
    return redirect('/')
