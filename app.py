import os, requests, time
from bs4 import BeautifulSoup

from flask import Flask, session, render_template, redirect, request, flash, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from datetime import timedelta

app = Flask(__name__)

# Session
app.secret_key = os.getenv("SECRET_KEY")
app.permanent_session_lifetime = timedelta(minutes=15)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/", methods=["POST", "GET"])
def index():
    if "user" in session:
        user_in_session = True
    else:
        user_in_session = False

    return render_template("landing_page.html", user_in_session=user_in_session)


@app.route("/login", methods=["POST", "GET"])
def login():
    # Redirects user of logged in
    if "user" in session:
        user_in_session = True
        return redirect(url_for('index'))
    else:
        user_in_session = False

    # Check if the method was post and performs form validation
    if request.method == 'POST':
        # Gets username and password
        username = request.form.get('username')
        password = request.form.get('password')

        users = db.execute("SELECT * FROM users")
        # Check to see if user is in the database
        for id, db_username, db_password in users:
            if username == db_username and password == db_password:
                session.permanent = True
                session["user"] = username
                user_in_session = True
                return redirect(url_for("index"))

        error = "Invalid credentials"
        return render_template("login.html", username_error=error, user_in_session=user_in_session)

    return render_template("login.html", user_in_session=user_in_session)


@app.route("/register", methods=["POST", "GET"])
def register():
    # Redirects user of logged in
    if "user" in session:
        user_in_session = True
        return redirect(url_for('index'))
    else:
        user_in_session = False

    password_error = ""
    username_error = ""

    # Form valiadation
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password2 = request.form.get('confirm_password')

        # Checks if the username length is acceptable
        username_length = len(username)
        if username_length < 5 or username_length > 12:
            username_error = "Username must be of lengt 5 to 12."
            return render_template("register.html", username_error=username_error, user_in_session=user_in_session)

        # Checks if both password fields are the same
        if password != password2:
            password_error = "Passwords do not match."
            return render_template("register.html", password_error=password_error, user_in_session=user_in_session)

        # Checks if the password length is acceptable
        password_length = len(password)
        if password_length < 8 or password_length > 16:
            password_error = "Password must be of length 7 - 16."
            return render_template("register.html", password_error=password_error, user_in_session=user_in_session)

        # Checks if the username and password already exist
        users = db.execute("SELECT * FROM users")
        for id, db_username, db_password in users:
            if username == db_username:
                username_error = "Username taken"
                return render_template("register.html", password_error=password_error, username_error=username_error, user_in_session=user_in_session)
            if password == db_username:
                password_error = "Invalid Password"
                return render_template("register.html", password_error=password_error, username_error=username_error, user_in_session=user_in_session)

        # Stores the username and password
        db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
                {"username": username, "password": password})
        db.commit()
        return render_template("login.html", user_in_session=user_in_session)

    return render_template("register.html", user_in_session=user_in_session)


@app.route("/logout")
def logout():
    # Logs the user out of the session
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/books")
def books():
    if "user" in session:
        user_in_session = True
    else:
        user_in_session = False

    # Displays all the available books
    books = db.execute(f"SELECT * FROM books")
    return render_template("book_list.html", books=books, user_in_session=user_in_session)


@app.route("/books/author/<author>")
def author(author):
    '''
    Scrapes wikipedia for the author's information and picture.
    Gets the average rating and working rating for each book
    written by the author.
    '''

    author = author
    url = "https://en.wikipedia.org/wiki/"

    # Formats the authors name into url
    name_substrings = author.split()
    for substring in name_substrings:
        url += substring
        url += "_"
    response = requests.get(url)

    # Checks to make sure the response was successful
    if response.status_code != 200:
        print("Connection Unsuccessful")
        return
    soup = BeautifulSoup(response.content, "html.parser")

    # Scraps the author's image
    images = soup.find_all("img")
    for image in images:
        img = image['src']
        if img[-3:].lower() == "jpg":
            break

    # Scraps the author's information
    info = soup.find_all("p")
    author_info = ""
    for passage in info:
        passage = passage.get_text()
        if name_substrings[-1] in passage:
            author_info = passage
            break

    # Gets the books written by the author
    books = db.execute(f"SELECT * FROM books WHERE author='{author}'")
    isbns = [isbn for id, isbn, title, author, year in books]

    # Gets the rating for each book by the selected author
    data = {}
    for isbn in isbns:
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "X88NGhXpOk5vLNQuNpk0iA", "isbns": isbn})
        goodreads_data = res.json()["books"][0]
        average_rating = goodreads_data["average_rating"]
        working_rating = goodreads_data["work_ratings_count"]

        data[isbn] = {"average_rating": average_rating, 
                    "working_rating": working_rating}
        time.sleep(1)
    
    if "user" in session:
        user_in_session = True
    else:
        user_in_session = False
    books = db.execute(f"SELECT * FROM books WHERE author='{author}'")
    return render_template("author_info.html", author=author, books=books, img=img, author_info=author_info, url=url, data=data, user_in_session=user_in_session)


@app.route("/books/isbn/<isbn>")
def isbn(isbn):
    '''
    Gets and displays the details of a selected book by isbn.
    '''

    book = db.execute(f"SELECT * FROM books WHERE isbn='{isbn}'")
    url = "https://www.goodreads.com/book/review_counts.json"
    res = requests.get(url, params={"key": "X88NGhXpOk5vLNQuNpk0iA", "isbns": isbn})
    data = res.json()['books'][0]
    average_rating = data['average_rating']
    working_rating = data['work_ratings_count']
    return render_template("isbn_book_info.html", book=book, average_rating=average_rating, working_rating=working_rating)


@app.route("/books/title/<title>")
def title(title):
    '''
    Gets and displays the details of a selected book by title.
    '''

    book = db.execute(f"SELECT * FROM books WHERE title='{title}'")
    url = "https://www.goodreads.com/book/review_counts.json"
    for id, isbn, title, author, year in book:
        res = requests.get(url, params={"key": "X88NGhXpOk5vLNQuNpk0iA", "isbns": isbn})
        data = res.json()['books'][0]
        average_rating = data['average_rating']
        working_rating = data['work_ratings_count']

    if "user" in session:
        user_in_session = True
    else:
        user_in_session = False
    book = db.execute(f"SELECT * FROM books WHERE title='{title}'")
    return render_template("isbn_book_info.html", book=book, average_rating=average_rating, working_rating=working_rating, user_in_session=user_in_session)


@app.route("/results", methods=["POST"])
def results():
    input_query = request.form.get("search_input")
    results = db.execute(f"SELECT * FROM books WHERE author LIKE '{input_query}%' ORDER BY author ASC")
    return render_template("results.html", results=results)