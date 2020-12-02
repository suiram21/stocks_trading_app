import os

from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
# from flask_migrate import Migrate
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd


# Configure application
app = Flask(__name__)

# Ensure templates are auto-related
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

# Configure SQL Database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    user_id = session["user_id"]

    # Get the current available cash for the user from the database
    user_info = db.execute("SELECT cash FROM users WHERE id = :id", id=user_id)

    # Get the currently owned stocks i.e. symbol and total no. of shares (only positive) for the user
    rows = db.execute("SELECT stocks_symbol, SUM(shares) FROM transactions WHERE user_id = :user_id GROUP BY stocks_symbol HAVING SUM(shares) > 0", user_id=user_id)

    # Assigned the value of cash and total value to be used for index.html
    cash = user_info[0]["cash"]
    total_value = cash

    # Initialize index list for data that will be used in the table in index.html
    index = list()
    for row in rows:
        stocks = dict()

        symbol = row["stocks_symbol"]
        shares = row["SUM(shares)"]

        # Get the name of company and the current price of the stocks
        quote = lookup(symbol)
        name = quote["name"]
        price = quote["price"]

        # Get the total amount of each stock and add it to the total value
        total_price = shares * price
        total_value += total_price

        # Create dictionary for each stocks to be added to the table in the html
        stocks['symbol'] = symbol
        stocks['name'] = name
        stocks['shares'] = shares
        stocks['price'] = usd(price)
        stocks['total_price'] = usd(total_price)

        index.append(stocks)

    return render_template("index.html", index=index, cash=usd(cash), total_value=usd(total_value))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy(stocks_symbol=''):
    """Buy shares of stock"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Assign the data (symbol, number of shares) from the form
        symbol = request.form.get("symbol").upper()

        # Ensure symbol was entered
        if not symbol:
            return apology("missing symbol")

        # Ensure number of shares was submitted
        elif not request.form.get("shares"):
            return apology("missing shares")

        shares = int(request.form.get("shares"))

        # Ensure number of shares are valid
        if shares < 1:
            return apology("value must be greater than or equal to 1", 400) # To be checked how to implement in javascript

        # Get the info. of the symbol and check if symbol is valid
        quote = lookup(symbol)
        if quote == None:
            return apology("invalid symbol", 400)

        # Query users table for the available cash using id
        rows = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])

        # Check the available cash and the price of stocks
        cash = rows[0]["cash"]
        transaction_price = shares * quote["price"]

        if cash - transaction_price < 0:
            return apology("can't afford", 400)

        # If cash is enough, deduct the price to the cash and update users table
        cash -= transaction_price

        db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash=cash, id=session["user_id"])

        # Add the buy transaction to the database
        db.execute("INSERT INTO transactions (user_id, stocks_symbol, shares, price) VALUES (:user_id, :stocks_symbol, :shares, :price)", user_id=session["user_id"], stocks_symbol=symbol, shares=shares, price=quote["price"])

        flash(f"Bought {shares} shares of {symbol}!")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html", stocks_symbol=stocks_symbol)


@app.route("/buy/<stocks_symbol>", methods=["GET", "POST"])
@login_required
def buy_home(stocks_symbol):
    """Buy shares of stock from homepage"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Assign the stocks symbol from the homepage
        symbol = stocks_symbol

        # Ensure number of shares was submitted
        if not request.form.get("shares"):
            return apology("missing shares")

        shares = int(request.form.get("shares"))

        # Ensure number of shares are valid
        if shares < 1:
            return apology("value must be greater than or equal to 1", 400) # To be checked how to implement in javascript

        # Get the info. of the symbol and check if symbol is valid
        quote = lookup(symbol)
        if quote == None:
            return apology("invalid symbol", 400)

        # Query users table for the available cash using id
        rows = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])

        # Check the available cash and the price of stocks
        cash = rows[0]["cash"]
        transaction_price = shares * quote["price"]

        if cash - transaction_price < 0:
            return apology("can't afford", 400)

        # If cash is enough, deduct the price to the cash and update users table
        cash -= transaction_price

        db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash=cash, id=session["user_id"])

        # Add the buy transaction to the database
        db.execute("INSERT INTO transactions (user_id, stocks_symbol, shares, price) VALUES (:user_id, :stocks_symbol, :shares, :price)", user_id=session["user_id"], stocks_symbol=symbol, shares=shares, price=quote["price"])

        flash(f"Bought {shares} shares of {symbol}!")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        # Query the database for the number of shares
        db_row = db.execute("SELECT stocks_symbol, SUM(shares) FROM transactions WHERE user_id = :user_id AND stocks_symbol = :stocks_symbol GROUP BY stocks_symbol HAVING SUM(shares) > 0", user_id=session["user_id"], stocks_symbol=stocks_symbol)

        try:
            num_of_shares = db_row[0]["SUM(shares)"]
        except:
            return apology("problem in database")

        quote = lookup(stocks_symbol)

        if quote == None:
            return apology("invalid symbol", 400)

        return render_template("buy.html", stocks_symbol=stocks_symbol, num_of_shares=num_of_shares, stock_price=usd(quote["price"]))


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    user_id = session["user_id"]

    # Query the transaction database for all data for the user
    rows = db.execute("SELECT * FROM transactions WHERE user_id = :user_id ORDER BY transacted DESC", user_id=user_id)

    # Initialize index dictionary for data that will be used in the table in history.html
    index = dict()
    for k, row in enumerate(rows):
        # Get the individual data from the output of the database
        symbol = row["stocks_symbol"]
        shares = row["shares"]
        price = row["price"]
        transacted = row["transacted"]

        # Create the list of data to be added to the table in the history.html
        index[k] = list()
        index[k].append(symbol)
        index[k].append(shares)
        index[k].append(usd(price))
        index[k].append(transacted)

    # Render the history.html with the data
    return render_template("history.html", index=index)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

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

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        symbol = request.form.get("symbol").upper()

        # Ensure symbol was entered
        if not symbol:
            return apology("missing symbol", 400)

        # Get the info. of the symbol and check if symbol is valid
        quote = lookup(symbol)
        if quote == None:
            return apology("invalid symbol", 400)

        # Render the html with the name of the company and the price of the stocks
        return render_template("quoted.html", name=quote["name"], symbol=quote["symbol"], price=usd(quote["price"]))

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Get the username, password and confirmation from the form
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure username was submitted
        if not username:
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 403)

        # Ensure entered passwords are the same
        elif password != confirmation:
            return apology("passwords don't match")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)

        # Ensure username doesn't exists
        if len(rows) != 0:
            return apology("username already exists", 403)

        # Enter the new user to the users table
        db.execute("INSERT INTO users (username, hash) VALUES (username = :username, hash = :hash)",
                          username=username, hash=generate_password_hash(password))

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Remember which user has registered
        session["user_id"] = rows[0]["id"]

        flash("Registered!")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell(stocks_symbol=''):
    """Sell shares of stock"""

    user_id = session["user_id"]

    # Query the database (transactions table) for the owned stocks (no. of shares is greater than 0) and no. of shares
    rows = db.execute("SELECT stocks_symbol, SUM(shares) FROM transactions WHERE user_id = :user_id GROUP BY stocks_symbol HAVING SUM(shares) > 0", user_id=user_id)

    # Create dictionary of the owned stocks symbol and no. of shares
    owned_stocks = dict()
    for row in rows:
        owned_stocks[row["stocks_symbol"]] = row["SUM(shares)"]

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Assign the symbol from the form
        symbol = request.form.get("symbol").upper()

        # Ensure symbol was entered
        if not symbol:
            return apology("missing symbol")

        # Ensure number of shares was submitted
        elif not request.form.get("shares"):
            return apology("missing shares")

        # Assign the number of shares from the form
        shares = int(request.form.get("shares"))

        # Ensure number of shares are valid
        if shares < 1:
            return apology("value must be greater than or equal to 1") # To be implemented as javascript

        # Ensure the user owned the stocks
        elif symbol not in owned_stocks:
            return apology("no shares own")

        # Ensure the number of owned shares are enough
        elif shares > owned_stocks[symbol]:
            return apology("too many shares")

        # Get the quotes of the symbol i.e. price per share
        quote = lookup(symbol)

        # Query users table for the available cash using id
        rows = db.execute("SELECT * FROM users WHERE id = :id", id=user_id)

        # Check the available cash of the user and the total price of stocks
        cash = rows[0]["cash"]
        transaction_price = shares * quote["price"]

        # Add the amount of the sold stocks to the available cash and update the database
        cash += transaction_price
        db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash=cash, id=user_id)

        # Add the sell transaction to the database
        db.execute("INSERT INTO transactions (user_id, stocks_symbol, shares, price) VALUES (:user_id, :stocks_symbol, :shares, :price)", user_id=user_id, stocks_symbol=symbol, shares=shares*-1, price=quote["price"])

        flash(f"Sold {shares} shares of {symbol}!")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("sell.html", stocks=owned_stocks, stocks_symbol=stocks_symbol)


@app.route("/sell/<stocks_symbol>", methods=["GET", "POST"])
@login_required
def sell_home(stocks_symbol):
    """Sell shares of stock from homepage"""

    user_id = session["user_id"]

    # Query the database (transactions table) for the owned stocks (no. of shares is greater than 0) and no. of shares
    rows = db.execute("SELECT stocks_symbol, SUM(shares) FROM transactions WHERE user_id = :user_id GROUP BY stocks_symbol HAVING SUM(shares) > 0", user_id=user_id)

    # Create dictionary of the owned stocks symbol and no. of shares
    owned_stocks = dict()
    for row in rows:
        owned_stocks[row["stocks_symbol"]] = row["SUM(shares)"]

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Assign the stocks symbol from the homepage
        symbol = stocks_symbol

        # Ensure number of shares was submitted
        if not request.form.get("shares"):
            return apology("missing shares")

        # Assign the number of shares from the form
        shares = int(request.form.get("shares"))

        # Ensure number of shares are valid
        if shares < 1:
            return apology("value must be greater than or equal to 1") # To be implemented as javascript

        # Ensure the user owned the stocks
        elif symbol not in owned_stocks:
            return apology("no shares own")

        # Ensure the number of owned shares are enough
        elif shares > owned_stocks[symbol]:
            return apology("too many shares")

        # Get the quotes of the symbol i.e. price per share
        quote = lookup(symbol)

        # Query users table for the available cash using id
        rows = db.execute("SELECT * FROM users WHERE id = :id", id=user_id)

        # Check the available cash of the user and the total price of stocks
        cash = rows[0]["cash"]
        transaction_price = shares * quote["price"]

        # Add the amount of the sold stocks to the available cash and update the database
        cash += transaction_price
        db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash=cash, id=user_id)

        # Add the sell transaction to the database
        db.execute("INSERT INTO transactions (user_id, stocks_symbol, shares, price) VALUES (:user_id, :stocks_symbol, :shares, :price)", user_id=user_id, stocks_symbol=symbol, shares=shares*-1, price=quote["price"])

        flash(f"Sold {shares} shares of {symbol}!")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        quote = lookup(stocks_symbol)

        if quote == None:
            return apology("invalid symbol", 400)

        return render_template("sell.html", stocks_symbol=stocks_symbol, num_of_shares=owned_stocks[stocks_symbol], stocks_price=usd(quote["price"]))


@app.route("/change_password", methods=["GET", "POST"])
def changepassword():
    """Change password of user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Forget any user_id
        session.clear()

        # Get the username, password and confirmation from the form
        username = request.form.get("username")
        old_password = request.form.get("password")
        new_password = request.form.get("new_password")
        confirmation = request.form.get("confirmation")

        # Ensure username was submitted
        if not username:
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not old_password:
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], old_password):
            return apology("invalid username and/or password", 403)

        # Ensure new password was submitted
        if not new_password:
            return apology("must provide new password", 403)

        # Ensure entered passwords are the same
        elif new_password != confirmation:
            return apology("passwords don't match")

        id = rows[0]["id"]

        # Update the new password of the user
        db.execute("UPDATE users SET hash = :hash WHERE id = :id", hash=generate_password_hash(new_password), id=id)

        # Remember which user has registered
        session["user_id"] = id

        flash("Successfully changed password!")
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("change_password.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)



