import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# set DATABASE_URL=postgres://fvncbgyogwnedd:3200e45562344293704dceed8a094446a1c36e08599f4d4649b595fd99f3d02c@ec2-52-87-135-240.compute-1.amazonaws.com:5432/dav3ellvuqpbfb

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    '''
    Imports book data to the database
    '''
    file = csv.reader(open("books.csv"))

    # for isbn, title, author, year in file:
    #     db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
    #                 {"isbn": isbn, "title": title, "author": author, "year": year})
    #     print(f"Added book {title} by {author}")
    # db.commit()


if __name__ == "__main__":
    main()