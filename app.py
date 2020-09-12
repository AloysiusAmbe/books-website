import os

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


@app.route("/<author>")
def author(author):
    return render_template("info.html")


@app.route("/<isbn>")
def isbn(isbn):
    return render_template("info.html")


@app.route("/<title>")
def title(title):
    return render_template("info.html")