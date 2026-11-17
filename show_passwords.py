# Shows the users table inside stayfinder.db, to prove passwords are saved as hashes.
# Run it in the same folder as the app:   python show_passwords.py
import hashlib
import sqlite3

from data import DB_FILE

conn = sqlite3.connect(DB_FILE)
rows = conn.execute("SELECT id, username, password_hash FROM users ORDER BY id").fetchall()

print("Database file:", DB_FILE)
print("SQL: SELECT id, username, password_hash FROM users\n")
print("%-4s %-15s %s" % ("id", "username", "password_hash (salt$sha256)"))
print("-" * 100)
for user_id, username, password_hash in rows:
    print("%-4s %-15s %s" % (user_id, username, password_hash))
if not rows:
    print("No users yet. Run main_app.py once first.")

# How the app checks a password: split off the salt, hash again, compare.
for user_id, username, password_hash in rows:
    if username == "APPisfav":
        salt, saved = password_hash.split("$")
        print("\nChecking the password 'fullmarks' for APPisfav:")
        print("  salt from the database :", salt)
        new = hashlib.sha256((salt + "fullmarks").encode()).hexdigest()
        print("  sha256(salt + password):", new)
        print("  matches the saved hash :", new == saved)
        wrong = hashlib.sha256((salt + "wrongpass").encode()).hexdigest()
        print("  'wrongpass' would give :", wrong, "->", wrong == saved)
conn.close()
