import os, requests, time, datetime
from bs4 import BeautifulSoup

from flask import Flask, session, render_template, redirect, request, flash, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from datetime import timedelta

app = Flask(__name__)

# Check for environment variableS
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

if not os.getenv("SECRET_KEY"):
    raise RuntimeError("SECRET_KEY is not set")

if not os.getenv("GOODREADS_KEY"):
    raise RuntimeError("GOODREADS_KEY is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.secret_key = os.getenv("SECRET_KEY")
app.permanent_session_lifetime = timedelta(minutes=15)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

user_id = None

@app.route("/", methods=["POST", "GET"])
def index():
    '''
    Main page
    '''
    
    if "user" in session:
        user_in_session = True
    else:
        user_in_session = False

    return render_template("landing_page.html", user_in_session=user_in_session)


@app.route("/login", methods=["POST", "GET"])
def login():
    # Redirects the user to the main passage if in session
    if "user" in session:
        return redirect(url_for('index'))
    else:
        user_in_session = False

    # Check if the method was post and performs form validation
    if request.method == 'POST':
        # Gets username and password
        username = request.form.get('username')
        password = request.form.get('password')

        users = db.execute("SELECT * FROM users WHERE username = :username AND password = :password",
                            {"username": username, "password": password})

        # Check to see if user is in the database
        for id, db_username, db_password in users:
            if username == db_username and password == db_password:
                # Sets up a session for the user and redirects them to the main page
                session.permanent = True
                session["user"] = username
                user_in_session = True

                # Gets the user's id and stores it in a global variable
                global user_id
                user_id = id

                return redirect(url_for("index"))

        error = "Invalid login credentials"
        return render_template("login.html", username_error=error, user_in_session=user_in_session)

    return render_template("login.html", user_in_session=user_in_session)


@app.route("/register", methods=["POST", "GET"])
def register():
    # Redirects the user to the main passage if in session
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
        if username_length < 3 or username_length > 12:
            username_error = "Username must be between 3 to 12 characters."
            return render_template("register.html", username_error=username_error, user_in_session=user_in_session)

        # Checks if both password fields are the same
        if password != password2:
            password_error = "Passwords do not match."
            return render_template("register.html", password_error=password_error, user_in_session=user_in_session)

        # Checks if the password length is acceptable
        password_length = len(password)
        if password_length < 8 or password_length > 16:
            password_error = "Password must be between 7 - 16 characters."
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
    books = db.execute("SELECT * FROM books")
    return render_template("book_list.html", books=books, user_in_session=user_in_session)


@app.route("/books/author/<author>")
def author(author):
    '''
    Scrapes wikipedia for the author's information and picture.
    Gets the average rating and working rating for each book
    written by the author from the Goodreads API.
    '''

    author = author
    url = "https://en.wikipedia.org/wiki/"

    # Formats the authors name into url
    name_substrings = author.split()
    for substring in name_substrings:
        url += substring
        url += "_"
    response = requests.get(url)

    img = None
    author_info = None

    # Checks to make sure the response was successful
    if response.status_code == 200:
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
    
    if "user" in session:
        user_in_session = True
    else:
        user_in_session = False
    books = db.execute("SELECT * FROM books WHERE author = :author",
                        {"author": author})
    return render_template("author_info.html", author=author, books=books, img=img, author_info=author_info, url=url, user_in_session=user_in_session)


@app.route("/books/isbn/<isbn>")
def isbn(isbn):
    '''
    Gets and displays the details of a book selected by isbn.
    '''

    if "user" in session:
        user_in_session = True
    else:
        user_in_session = False
    
    global user_id
    
    # Gets the ratings of the book from the goodreads API
    book = db.execute(f"SELECT * FROM books WHERE isbn='{isbn}'")
    url = "https://www.goodreads.com/book/review_counts.json"
    res = requests.get(url, params={"key": os.getenv("GOODREADS_KEY"), "isbns": isbn})
    data = res.json()['books'][0]
    average_rating = data['average_rating']
    working_rating = data['work_ratings_count']

    # Gets the book_id
    db_id = db.execute("SELECT * FROM books WHERE isbn = :isbn",
                        {"isbn": isbn})
    for id, isbn, title, author, year in db_id:
        book_id = id # Gets the book's id - used for query later

    # Gets the reviews for the book
    reviews = db.execute("SELECT username, review, date FROM users JOIN reviews ON reviews.user_id = users.id AND reviews.book_id = :book_id",
                        {"book_id": book_id})

    # Checks if they user has already rated the book
    user_rated_book = False
    if "user" in session:
        rating = db.execute("SELECT rating, user_id, book_id FROM ratings WHERE user_id = :user_id AND book_id = :book_id",
                                {"user_id": user_id, "book_id": book_id})
        if rating.rowcount != 0:
            user_rated_book = True
    return render_template("book_info.html", book=book, average_rating=average_rating, working_rating=working_rating, user_rated_book=user_rated_book, reviews=reviews, user_in_session=user_in_session)


@app.route("/books/title/<author>/<title>", methods=["POST", "GET"])
def title(title, author):
    '''
    Gets and displays the details of a book selected by title.
    Allows the user to rate the book.
    Allows the user to write and submit a review for the book.
    '''

    # Sets a user_in_session variable
    if "user" in session:
        user_in_session = True
    else:
        user_in_session = False

    global user_id

    # Gets the rating of the book from the Goodreads API
    book = db.execute("SELECT * FROM books WHERE title = :title AND author = :author",
                        {"title": title, "author": author})
    url = "https://www.goodreads.com/book/review_counts.json"
    for id, isbn, title, author, year in book:
        book_id = id # Gets the book's id - used for query later
        res = requests.get(url, params={"key": os.getenv("GOODREADS_KEY"), "isbns": isbn})
        data = res.json()['books'][0]
        average_rating = data['average_rating']
        working_rating = data['work_ratings_count']

    book = db.execute("SELECT * FROM books WHERE title = :title AND author = :author",
                        {"title": title, "author": author})

    # Checks if they user has already rated the book
    user_rated_book = False
    if "user" in session:
        rating = db.execute("SELECT rating, user_id, book_id FROM ratings WHERE user_id = :user_id AND book_id = :book_id",
                            {"user_id": user_id, "book_id": book_id})
        if rating.rowcount != 0:
            user_rated_book = True

    # Gets the reviews for the book
    reviews = db.execute("SELECT username, review, date FROM users JOIN reviews ON reviews.user_id = users.id AND reviews.book_id = :book_id",
                        {"book_id": book_id})

    # Post method is for ratings
    if request.method == "POST":
        # Gets which form is being submitted to the server
        form_id = request.args.get('form_id', 2, type=int)

        # The rating form is sbumitted
        if form_id == 1:
            rating = request.form.get("star")
            isRated = False

            # Makes sure the user rated the book
            if rating != None:
                rating = int(rating)
                isRated = True

                # Inserts the rating into a database if no rating already exists
                if not user_rated_book:
                    db.execute("INSERT INTO ratings (rating, user_id, book_id) VALUES (:rating, :user_id, :book_id)",
                                {"rating": rating, "user_id": user_id, "book_id": book_id})
                    db.commit()
                    success_message = "Thanks for rating this book."
                    return render_template("book_info.html", book=book, isRated=isRated, user_rated_book=user_rated_book, average_rating=average_rating, working_rating=working_rating, success_message=success_message, user_in_session=user_in_session)
            return render_template("book_info.html", book=book, isRated=isRated, user_rated_book=user_rated_book, average_rating=average_rating, working_rating=working_rating, user_in_session=user_in_session)

        # The reviews form is submitted
        else:
            # Gets the date
            current_time = datetime.datetime.now()
            month = current_time.strftime("%b")
            day = current_time.strftime("%d")
            year = current_time.strftime("%Y")
            date = f"{month} {day}, {year}"

            # Gets the review submitted
            review = request.form.get('review')

            has_blank_review = False
            if review == "":
                has_blank_review = True
                error_message = "Cannot leave a blank review."
                return render_template("book_info.html", book=book, has_blank_review=has_blank_review, user_rated_book=user_rated_book, average_rating=average_rating, working_rating=working_rating, error_message=error_message, user_in_session=user_in_session)
            
            # Inserts the comment into the database
            db.execute("INSERT INTO reviews (review, date, user_id, book_id) VALUES (:review, :date, :user_id, :book_id)",
                        {"review": review, "date": date, "user_id": user_id, "book_id": book_id})
            db.commit()
            success_message = "Review has been submitted."
            review_submitted = True

            return render_template("book_info.html", book=book, review_submitted=review_submitted, user_rated_book=user_rated_book, average_rating=average_rating, working_rating=working_rating, success_message=success_message, user_in_session=user_in_session)
    
    # Gets request response
    else:
        return render_template("book_info.html", book=book, average_rating=average_rating, working_rating=working_rating, user_rated_book=user_rated_book, reviews=reviews, user_in_session=user_in_session)


@app.route("/results", methods=["POST"])
def results():
    '''
    Gets and returns the results of the user search input
    '''
    # Gets the user's search input and formats it to match database query
    input_query = request.form.get("search_input")
    input_query.strip("'")
    substrings = input_query.split()
    input_query = ""
    for word in substrings:
        input_query += word.capitalize() + " "
    input_query = input_query.strip()

    rows = db.execute("SELECT id, isbn, title, author, year FROM books WHERE \
                        isbn LIKE :query OR \
                        title LIKE :query OR \
                        author LIKE :query",
                        {"query": input_query})
    
    row_count = rows.rowcount
    if row_count == 0:
        return render_template("results.html", row_count=row_count)

    results = rows.fetchall()
    return render_template("results.html", results=results, row_count=row_count)
