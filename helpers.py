import csv
import urllib.request

from flask import redirect, render_template, request, session
from functools import wraps
from itsdangerous import URLSafeTimedSerializer
from forex_python.converter import CurrencyRates
from datetime import datetime, timedelta


def apology(message, code=400):
    """Renders message as an apology to user"""
    def escape(s):
        """
        Escape special characters.
        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.
    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def send_email(recipient, subject, body):
    """Sends email to user(s) from Charget account"""

    import smtplib

    # email details (from, to, etc.)
    user = "chathamcharget@gmail.com"
    pwd = "jtrmohgqzvagmdbn"
    FROM = user
    TO = recipient if type(recipient) is list else [recipient]
    SUBJECT = subject
    TEXT = body

    # Prepare actual message
    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(user, pwd)
        server.sendmail(FROM, TO, message)
        server.close()
        print('successfully sent mail')
    except:
        print("failed to send mail")


def generate_confirmation_link(email):
    """Generates confirmation link for account activation"""
    serializer = URLSafeTimedSerializer("chathamfinancial")
    return serializer.dumps(email)


def confirm_token(token, expiration = 3600):
    """Confirm token in activation link, (default active for 1 hour)"""
    serializer = URLSafeTimedSerializer("chathamfinancial")
    try:
        email = serializer.loads(token, max_age = expiration)
    except:
        return False
    return email


def fx_rate(rate):
    """Returns FX Rate string formatted as 0.0000"""
    rate = round(rate, 4)
    rate = str(rate)
    if len(rate) < 6:
        rate = rate + '0'
    return rate


def ccy_format(amount):
    """Returns amount string formatted as 0.00"""
    amount = round(amount, 2)
    amount = str(amount)
    if '.' not in amount:
        amount += '.00'
    elif amount[-2] == '.':
        amount += "0"
    return amount


def user_ccy(charge_amount, charge_ccy, user_ccy):
    """Picks correct FX rate and converts amount depending on transaction and user currency"""

    # get FX rates as of EOD yesterday
    yesterday = datetime.today() - timedelta(1)
    c = CurrencyRates()

    # series of conditions for different PLN/GBP/USD combinations
    if charge_ccy == "GBP" and user_ccy == "PLN":
        return charge_amount * c.get_rate('GBP', 'PLN', yesterday), fx_rate(c.get_rate('GBP', 'PLN', yesterday))
    elif charge_ccy == "PLN" and user_ccy == "GBP":
        return charge_amount / c.get_rate('GBP', 'PLN', yesterday), fx_rate(c.get_rate('GBP', 'PLN', yesterday))
    elif charge_ccy == "USD" and user_ccy == "PLN":
        return charge_amount * c.get_rate('USD', 'PLN', yesterday), fx_rate(c.get_rate('USD', 'PLN', yesterday))
    elif charge_ccy == "PLN" and user_ccy == "USD":
        return charge_amount / c.get_rate('USD', 'PLN', yesterday), fx_rate(c.get_rate('USD', 'PLN', yesterday))
    elif charge_ccy == "GBP" and user_ccy == "USD":
        return charge_amount * c.get_rate('GBP', 'USD', yesterday), fx_rate(c.get_rate('GBP', 'USD', yesterday))
    elif charge_ccy == "USD" and user_ccy == "GBP":
        return charge_amount / c.get_rate('GBP', 'USD', yesterday), fx_rate(c.get_rate('GBP', 'USD', yesterday))
    else:
        return charge_amount, ""

# Delete users who have not been confirmed
def clean_users():
    """Clears database from users who have not been confirmed"""
    db.execute("DELETE FROM users WHERE confirmed = 0")