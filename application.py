import os
import sqlite3

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# For Heroku PostgreSQL
# uri = os.getenv("DATABASE_URL")  # or other relevant config var
# if uri.startswith("postgres://"):
#     uri = uri.replace("postgres://", "postgresql://", 1)
# db = SQL(uri)

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # Show the sum of shares as 'totalShares', not individual one
    rows = db.execute("""
    SELECT symbol, SUM(shares) as totalShares FROM transactions
    WHERE user_id = :user_id
    GROUP BY symbol
    HAVING totalShares > 0;
    """, user_id=session["user_id"])

    # Create portfolio array
    portfolio = []
    grand_total = 0

    # add stock name to the table, using lookup function
    for row in rows:
        stock = lookup(row["symbol"])

        # Add all tables we want to portfolio table
        portfolio.append({
            "symbol": stock["symbol"],
            "name": stock["name"],
            "shares": row["totalShares"],
            "price": stock["price"],
            "total": stock["price"] * row["totalShares"]
        })
        grand_total += stock["price"] * row["totalShares"]

    rows = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=session["user_id"])
    cash = round(rows[0]["cash"], 2)
    grand_total = round((grand_total + cash), 2)

    return render_template("index.html", portfolio=portfolio, cash=cash, grand_total=grand_total)


@app.route("/add_cash", methods=["GET", "POST"])
@login_required
def add_cash():
    """Add cash. Additional feature"""

    if request.method == "POST":
        if int(request.form.get("cash")) < 0:
            return apology("Invalid amount of cash")

        else:
            db.execute("""UPDATE users
            SET cash = cash + :amount
            WHERE id = :user_id;""", amount=request.form.get("cash"), user_id=session["user_id"])

            flash("Added Cash!")
            return redirect("/")

    else:
        return render_template("add_cash.html")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":

        # Stock symbol or shares must be submitted
        if (not request.form.get("symbol")) or (not request.form.get("shares")):
            return apology("Must provide stock symbol and number of shares")

        # Ensure shares are valid
        if not (request.form.get("shares")).isnumeric():
            return apology("Must provide integer number of shares")

        if int(request.form.get("shares")) <= 0:
            return apology("Must provide valid number of shares")

        if lookup(request.form.get("symbol")) == None:
            return apology("Invalid symbol")

        rows = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
        cash = rows[0]["cash"]

        symbol = request.form.get("symbol").upper()
        shares = int(request.form.get("shares"))
        stock = lookup(symbol)

        updated_cash = cash - shares * stock['price']
        if updated_cash < 0:
            return apology("Not enough cash for transaction")

        else:
            # updated user's Cash
            db.execute("UPDATE users SET cash = :updated_cash WHERE id=:id", updated_cash=updated_cash, id=session["user_id"])

            # Update transaction table
            db.execute("""INSERT INTO transactions (user_id, symbol, shares, price)
            VALUES (:user_id, :symbol, :shares, :price)""", user_id=session["user_id"], symbol=stock["symbol"], shares=shares, price=stock["price"])

            # Shares bought successfully
            flash("Shares Bought!")

            # Redirect to home page
            return redirect(url_for("index"))

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # pull from transactions table
    portfolio = db.execute("""
    SELECT symbol, shares, price, transacted
    FROM transactions
    WHERE user_id = :user_id
    ORDER BY transacted DESC;
    """, user_id=session["user_id"])

    if not portfolio:
        return apology("Sorry, you have no transaction records")

    return render_template("history.html", portfolio=portfolio)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password")

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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":

        # Ensure name of stock submitted
        if not request.form.get("symbol"):
            return apology("must provide stock symbol", 400)

        # lookup quote symbol
        stock = lookup(request.form.get("symbol").upper())

        # check if stock provided is valid
        if stock == None:
            return apology("Invalid symbol", 400)

        # All checks valid. Pass in variable "stock" from lookup function
        else:
            return render_template("quoted.html", stock=stock)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # Ensure password confirmation matches
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords confirmation did not match")

        # Insert new user into database
        else:
            try:
                # self-note: placeholder ':'' supports one-line function, '?' have to use separate lines
                result = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)",
                                    username=request.form.get("username"),
                                    hash=generate_password_hash(request.form.get("password"))
                                    )

            # Ensure username is unique, ie. insertion fail if errors occurs.
            except:
                return apology("Username is already registered")

            # All other errors
            if not result:
                return apology("Registration error")

            # Remember session ID
            session["user_id"] = result

            # Redirect to home page
            return redirect("/login")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    print(request.method)

    # if user reach route via POST eg. submit a form via POST
    if request.method == "POST":

        # Stock symbol or shares must be submitted
        if (not request.form.get("symbol")) or (not request.form.get("shares")):
            return apology("Must provide stock symbol and number of shares")

        # Ensure shares are valid
        if int(request.form.get("shares")) <= 0:
            return apology("Must provide valid number of shares")

        if lookup(request.form.get("symbol")) == None:
            return apology("Invalid symbol")

        # Query for user's Cash
        rows = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
        cash = rows[0]["cash"]

        symbol = request.form.get("symbol").upper()
        shares = int(request.form.get("shares"))
        stock = lookup(symbol)

        # Query for user's shares holding
        rows = db.execute("""
        SELECT symbol, SUM(shares) as totalShares
        FROM transactions
        WHERE user_id = :user_id
        GROUP BY symbol
        HAVING totalShares > 0;
        """, user_id=session["user_id"])

        # check if users have sufficient shares to sell
        for row in rows:
            if row["symbol"] == symbol:
                if shares > row["totalShares"]:
                    return apology("Insufficient shares for transaction")

        updated_cash = cash + shares * stock['price']

        # updated user's Cash
        db.execute("UPDATE users SET cash = :updated_cash WHERE id=:id", updated_cash=updated_cash, id=session["user_id"])

        # Update transaction table
        db.execute("""INSERT INTO transactions (user_id, symbol, shares, price)
        VALUES (:user_id, :symbol, :shares, :price)""", user_id=session["user_id"], symbol=stock["symbol"], shares=-shares, price=stock["price"])

        # Shares bought successfully
        flash("Shares Sold!")

        # Redirect to home page
        return redirect(url_for("index"))

    # if user reached via GET (by clicking on a link to reach this page)
    else:
        symbols = db.execute("""
        SELECT symbol
        FROM transactions
        WHERE user_id=:user_id
        GROUP BY symbol
        HAVING SUM(shares) > 0;
        """, user_id=session["user_id"])

        # to simplify [{symbol: APPL}, {}]... etc to [{AAPL}, {}]...

        return render_template("sell.html", symbols=symbols)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
