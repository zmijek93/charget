from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
from apscheduler.schedulers.background import BackgroundScheduler

from helpers import apology, login_required, send_email, generate_confirmation_link, confirm_token, user_ccy, ccy_format, fx_rate, clean_users

placeholder_email = "zmijewski.kam@gmail.com"

# Configure application
app = Flask(__name__)

# Delete users who have not been confirmed every 24 hours
scheduler = BackgroundScheduler()
job = scheduler.add_job(clean_users, 'interval', minutes = 1440)
scheduler.start()


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///charget.db")


@app.route("/")
@login_required
def index():
    """Show balance and charges history"""

    # get user's username
    rows_user = db.execute("SELECT * FROM users WHERE id = :id",
                            id = session["user_id"])

    # choose all charges to user's account
    table = db.execute("SELECT * FROM history WHERE to_user = :user",
                        user = rows_user[0]["username"])

    # replace transaction and user amounts with formatted numbers
    for i in table:
        i["amount"] = ccy_format(i["amount"])
        i["user_amount"] = ccy_format(i["user_amount"])

    # reverse charges list
    table = list(reversed(table))

    # # get up to 5 most recent trades
    # if len(table) > 5:
    #     table = table[:5]

    if not table:
        return render_template("index.html",
                            ccy = rows_user[0]["ccy"],
                            balance = ccy_format(rows_user[0]["balance"]),
                            user_ccy = rows_user[0]["ccy"])

    else:
        return render_template("index.html",
                            ccy = rows_user[0]["ccy"],
                            balance = ccy_format(rows_user[0]["balance"]),
                            table = table,
                            user_ccy = rows_user[0]["ccy"])


@app.route("/login", methods = ["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                            username = str.lower(request.form.get("username")))

        # Ensure username exists
        if len(rows) != 1:
            return render_template("login.html",
                                    wrong_user = True)

        # Ensure password is correct
        elif not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("login.html",
                                    wrong_pw = True)

        # Ensure user is confirmed
        elif rows[0]["confirmed"] != 1:
            return render_template("login.html",
                                    not_confirmed = True)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods = ["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Check if the username exists
        rows = db.execute("SELECT * FROM users where username = :username",
                            username = request.form.get("username"))

        # If it exists, return apology
        if len(rows) == 1:
            return render_template("register.html",
                                    user_exists = True)

        # Else insert username, hash into database
        else:
            db.execute("INSERT INTO users (username, hash, ccy) VALUES (:username, :hash, :ccy)",
                        username = str.lower(request.form.get("username")),
                        hash = generate_password_hash(request.form.get("password")),
                        ccy = request.form.get("ccy"))

            # Send confirmation link to user
            confirmation_link = generate_confirmation_link(request.form.get("username") + "@chathamfinancial.com")

            ##### Commented lines to be used once app goes live #####

            # send_email(str.lower(request.form.get("username")) + "@chathamfinancial.com",
            #             "Activate you Charget account",
            #             "Your activation link is: " + "http://pset9-kzmijewski.cs50.io:8080/confirm/" + confirmation_link)

            #########################################################

            send_email(placeholder_email, "Activate your Charget account",
                        "Your activation link is: " + "http://pset9-kzmijewski.cs50.io:8080/confirm/" + confirmation_link)

        # Redirect user to home page
        return render_template("register.html",
                                email_sent=True)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/confirm/<token>")
def confirm_user(token):
    """Confirms user via email token"""

    # Ensure token is correct
    email = confirm_token(token)
    if not email:
        return apology("Link expired")

    # Extract username from email
    username = ''
    for i in email:
        if i == "@":
            break
        else:
            username += i

    # Update database (set confirmed to True)
    db.execute("UPDATE users SET confirmed = 1 WHERE username = :username",
                username = str.lower(username))

    # Query database for username again (check if it was added)
    rows = db.execute("SELECT * FROM users WHERE username = :username",
                        username = str.lower(username))

    # Remember which user has logged in
    session["user_id"] = rows[0]["id"]

    # Redirect user to home page
    return redirect("/")


@app.route("/change_pw", methods = ["GET", "POST"])
@login_required
def change_pw():
    """Change user password"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Update database with new password hash
        db.execute("UPDATE users SET hash = :hash WHERE id = :id",
                    hash = generate_password_hash(request.form.get("password")),
                    id = session["user_id"])

        # Redirect user to home page
        return render_template("change_pw.html",
                                pw_changed = True)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("change_pw.html")


@app.route("/forgot_pw", methods = ["GET", "POST"])
def forgot_pw():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username = str.lower(request.form.get("username")))

        # Ensure username exists
        if len(rows) != 1:
            return render_template("forgot_pw.html",
                                    no_user = True)

        # Generate and send link to log in (and change password)
        confirmation_link = generate_confirmation_link(request.form.get("username") + "@chathamfinancial.com")

        ##### Commented lines to be used once app goes live #####

        # send_email(str.lower(request.form.get("username")) + "@chathamfinancial.com",
        #             "Reset your Charget password",
        #             "Click to log in and change password: " + "http://pset9-kzmijewski.cs50.io:8080/confirm/" + confirmation_link)

        #########################################################

        send_email(placeholder_email, "Reset your Charget password",
                    "Click to log in and change password: " + "http://pset9-kzmijewski.cs50.io:8080/reset/" + confirmation_link)

        return render_template("forgot_pw.html",
                                email_sent = True)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("forgot_pw.html")


@app.route("/reset/<token>")
def reset_pw(token):
    """Resets via email token"""

    # Ensure token is correct
    email = confirm_token(token)
    if not email:
        return apology("link expired")

    # Extract username from email
    username = ''
    for i in email:
        if i == "@":
            break
        else:
            username += i

    # Query database for username
    rows = db.execute("SELECT * FROM users WHERE username = :username",
                        username = str.lower(username))

    # Remember which user has logged in
    session["user_id"] = rows[0]["id"]

    # Redirect user to home page
    return render_template("change_pw.html")


@app.route("/charge", methods = ["GET", "POST"])
@login_required
def charge():
    """Charges user account"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure amount is int/float
        try:
            amount = float(request.form.get("amount"))
        except ValueError:
            return render_template("charge.html", wrong_amount = True, users = available_users)

        # Database queries for chargor and chargee
        rows_chargor = db.execute("SELECT * FROM users WHERE id = :id", id = session["user_id"])
        rows_chargee = db.execute("SELECT * FROM users WHERE username = :username", username = request.form.get("user"))

        # Get transaction currency
        ccy = request.form.get("ccy")

        # Get charge amount and home currency for chargor and chargee
        chargor_amount, chargor_rate = user_ccy(amount, ccy, rows_chargor[0]["ccy"])
        chargee_amount, chargee_rate = user_ccy(amount, ccy, rows_chargee[0]["ccy"])

        # Insert transaction into history (chargor side)
        db.execute("INSERT INTO history (to_user, by_user, amount, ccy, user_amount, rate, notes) \
                    VALUES (:to_user, :by_user, :amount, :ccy, :user_amount, :rate, :notes)",
                    to_user = rows_chargor[0]["username"],
                    by_user = rows_chargee[0]["username"],
                    amount = -round(amount, 2),
                    ccy = ccy,
                    user_amount = -round(chargor_amount, 2),
                    rate = chargor_rate,
                    notes = request.form.get("notes"))

        # Update chargor's balance
        db.execute("UPDATE users SET balance = balance - :charge WHERE id = :id",
                    charge = round(chargor_amount, 2),
                    id = session["user_id"])

        # If balance is over 50, send email
        if round(rows_chargor[0]["balance"] - chargor_amount, 2) < -50:

            # Generate notification message
            message = "Your current balance is: " + ccy_format(round(rows_chargor[0]["balance"] - chargor_amount, 2)) \
                        + " " + rows_chargor[0]["ccy"] + ". Note that your debt is over 50.00 " + rows_chargor[0]["ccy"] \
                        + ". Consider settling!"

            # Send notification email

            ##### Commented lines to be used once app goes live #####

            # send_email(str.lower(rows_chargor[0]["username") + "@chathamfinancial.com",
            #             "Settle your debt!",
            #             message)

            #########################################################

            send_email(placeholder_email, "Settle your debt!", message)


        # Insert transaction into history (chargee side)
        db.execute("INSERT INTO history (to_user, by_user, amount, ccy, user_amount, rate, notes) \
                    VALUES (:to_user, :by_user, :amount, :ccy, :user_amount, :rate, :notes)",
                    to_user = rows_chargee[0]["username"],
                    by_user = rows_chargor[0]["username"],
                    amount = round(amount, 2),
                    ccy = ccy,
                    user_amount = round(chargee_amount, 2),
                    rate = chargee_rate,
                    notes = request.form.get("notes"))

        db.execute("UPDATE users SET balance = balance + :charge WHERE username = :username",
                    charge = round(chargee_amount, 2),
                    username = request.form.get("user"))

        # Generate notification message
        message = "User " + rows_chargor[0]["username"] + " charged your account with " + ccy_format(round(amount, 2)) + " " + ccy

        # Add notes, if any
        if request.form.get("notes"):
            message += " (notes: " + request.form.get("notes") + ")"

        # Add balance info
        message += ". Your current balance is: " + ccy_format(round(rows_chargee[0]["balance"] + chargee_amount, 2)) \
                    + " " + rows_chargee[0]["ccy"] + "."

        # Add note if debt is over 50
        if round(rows_chargee[0]["balance"] + chargee_amount, 2) < -50:
            message += " Note that your debt is over 50.00 " + rows_chargee[0]["ccy"] + ". Consider settling!"

        # Send notification email

        ##### Commented lines to be used once app goes live #####

        # send_email(str.lower(rows_chargee[0]["username") + "@chathamfinancial.com",
        #             "New Charget charge",
        #             message)

        #########################################################

        send_email(placeholder_email, "New Charget charge", message)

        # Prepare dropdown list for users
        rows = db.execute("SELECT * FROM users")

        # List of available users
        available_users = []
        for i in rows:
            if session["user_id"] != i["id"]:
                available_users.append(i["username"])
        available_users.sort()

        return render_template("charge.html",
                                charge_added = True,
                                users = available_users)

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        # get users list
        rows = db.execute("SELECT * FROM users")

        # List of available users
        available_users = []
        for i in rows:
            if session["user_id"] != i["id"]:
                available_users.append(i["username"])
        available_users.sort()

        return render_template("charge.html",
                                users = available_users)


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)