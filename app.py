import os
import requests
from bs4 import BeautifulSoup

from flask import Flask, session, render_template, redirect, request, flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

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


@app.route("/")
def index():
    return render_template("landing_page.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/books")
def books():
    books = db.execute("SELECT * FROM books")
    return render_template("book_list.html", books=books)


@app.route("/books/<author>")
def author(author):
    author = author
    url = "https://en.wikipedia.org/wiki/"
    name_substrings = author.split()

    for substring in name_substrings:
        url += substring
        url += "_"
    response = requests.get(url)
    if response.status_code != 200:
        print("Connection Unsuccessful")
        return
    soup = BeautifulSoup(response.content, "html.parser")

    # Scraps the author's image
    images = soup.find_all("img")
    for image in images:
        img = image['src']
        if img[-3:] == "jpg":
            print(img)
            break

    # Scraps the author's information
    info = soup.find_all("p")
    author_info = ""
    for passage in info:
        passage = passage.get_text()
        if name_substrings[-1] in passage:
            author_info = passage
            break

    books = db.execute(f"SELECT * FROM books WHERE author='{author}'")
    return render_template("author_info.html", author=author, books=books, img=img, author_info=author_info, url=url)


@app.route("/books/<isbn>")
def isbn(isbn):
    isbn = isbn
    books = db.execute(f"SELECT * FROM books WHERE author='{isbn}'")
    return render_template("info.html", books=books)


@app.route("/books/<title>")
def title(title):
    return render_template("info.html")