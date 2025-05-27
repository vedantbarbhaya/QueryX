#!/usr/bin/env python3
"""
Script to create two users in the database.
Usage: python create_users.py
"""
import os
import sys

# Ensure the backend directory is on the PYTHONPATH
this_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(this_dir, '..'))
sys.path.insert(0, project_root)

from app.core.database import SessionLocal, engine, Base
from app.core.models import User
from app.core.security import get_password_hash


def main():
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Define users to create
    users = [
        {"username": "alice", "email": "alice@example.com", "password": "password123"},
        {"username": "bob",   "email": "bob@example.com",   "password": "password123"},
    ]

    for u in users:
        # Check for existing user
        existing = db.query(User).filter(
            (User.username == u["username"]) | (User.email == u["email"])
        ).first()
        if existing:
            print(f"User '{u['username']}' already exists, skipping.")
            continue

        # Hash the password and create user
        hashed_pw = get_password_hash(u["password"])
        new_user = User(
            username=u["username"],
            email=u["email"],
            hashed_password=hashed_pw
        )
        db.add(new_user)
        db.commit()
        print(f"Created user '{u['username']}'.")

    db.close()


if __name__ == '__main__':
    main() 