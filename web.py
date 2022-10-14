from datetime import datetime
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
        return requests.get("https://tigerspend.rit.edu/statementdetail.php", payload)
    else:
        return None




@app.route('/')
def landing():
    return render_template("index.html", session=session)

@app.route('/auth')
def auth():
    for item in request.args.items():
        print(item[0], item[1])
    if 'skey' in request.args.keys():
        session['skey'] = str(request.args.get('skey'))
    return redirect('/')

@app.route('/budget')
def budget():
    if 'skey' in session:

        response = getuserspending(55, 2221, "csv")

        lines = response.content.decode(response.encoding).splitlines()
        reader = csv.reader(lines)
        parsed_csv = list(reader)

        if len(parsed_csv[0]) < 4:
            session.pop('skey')
            return redirect('/')

        current_date_time = datetime.today().strftime("%m/%d/%Y")


        money_spent = 0
        for record in parsed_csv:
            if len(record) <= 0:
                continue
            if record[0].split(' ')[0] != current_date_time:
                continue
            money_spent -= float(record[2])

        first_date = parsed_csv[-2][0].split(' ')[0]
        current_date = current_date_time.split(' ')[0]
        last_date = "12/14/2022"

        date_format = "%m/%d/%Y"
        delta = datetime.strptime(last_date, date_format) - datetime.strptime(current_date, date_format)
        # print(float(parsed_csv[-1][2]), float(parsed_csv[1][3]), float(parsed_csv[-1][2]) - float(parsed_csv[1][3]))
        print(parsed_csv[1])

        starting_balance = float(parsed_csv[-1][3]) - float(parsed_csv[-1][2])
        current_balance = float(parsed_csv[1][3])

        daily_budget = round((current_balance / delta.days), 2)
        


        return render_template("budget.html", colors=colors, records=parsed_csv, money_spent=money_spent, daily_budget=daily_budget)
    else:
        return redirect('/')
