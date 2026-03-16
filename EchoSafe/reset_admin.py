#!/usr/bin/env python3
"""
Reset admin password in the database
Usage: python reset_admin.py
"""

import sqlite3
import bcrypt
import os
from datetime import datetime, UTC
import sys

# Database is in the backend directory
DB_PATH = os.path.join(os.path.dirname(__file__), "backend", "echosafe.db")

# Password that includes the user's requested digits
# Meets requirements: 8+ chars, uppercase, number, special char
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin@7038!"  # Includes 7038 + meets security requirements

def reset_admin():
    """Reset or create admin user"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Hash the password
        password_hash = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode("utf-8")
        
        # Check if admin exists
        cursor.execute("SELECT id FROM hr_users WHERE username = ?", (ADMIN_USERNAME,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing admin
            cursor.execute("""
            UPDATE hr_users
            SET password_hash = ?
            WHERE username = ?
            """, (password_hash, ADMIN_USERNAME))
            print(f"✓ Admin password updated successfully")
        else:
            # Create new admin
            created_at = datetime.now(UTC).isoformat()
            cursor.execute("""
            INSERT INTO hr_users (username, password_hash, created_at)
            VALUES (?, ?, ?)
            """, (ADMIN_USERNAME, password_hash, created_at))
            print(f"✓ Admin user created successfully")
        
        conn.commit()
        conn.close()
        
        print(f"\n📝 Admin Credentials:")
        print(f"   Username: {ADMIN_USERNAME}")
        print(f"   Password: {ADMIN_PASSWORD}")
        print(f"\n⚠️  Keep this password safe!")
        print(f"✓ Ready to login at http://localhost:8080")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    reset_admin()
