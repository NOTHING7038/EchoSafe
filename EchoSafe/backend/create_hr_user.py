#!/usr/bin/env python3
"""
Create or update an HR user in MongoDB.
Usage:
  python create_hr_user.py admin Admin@7038!
"""

import os
import sys
from datetime import UTC, datetime

import bcrypt
from pymongo import MongoClient


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python create_hr_user.py <username> <password>")
        return 1

    username = sys.argv[1].strip()
    password = sys.argv[2]
    if not username or len(password) < 8:
        print("Username required and password must be 8+ chars.")
        return 1

    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    mongodb_db = os.getenv("MONGODB_DB", "echosafe")

    db = MongoClient(mongodb_uri)[mongodb_db]
    users = db["hr_users"]
    users.create_index("username", unique=True)

    existing = users.find_one({"username": username})
    pw_hash = hash_password(password)
    if existing:
        users.update_one({"username": username}, {"$set": {"password_hash": pw_hash}})
        print(f"Updated user: {username}")
    else:
        users.insert_one(
            {
                "username": username,
                "password_hash": pw_hash,
                "created_at": datetime.now(UTC),
            }
        )
        print(f"Created user: {username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
