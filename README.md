# StayFinder – Chennai stays

A desktop app for finding and booking stays in Chennai, built with **Python, tkinter and SQLite**.
Made for the 21CSC203P Advanced Programming Practice project.

## Features
- Login and sign-up page (passwords are stored as salted SHA-256 hashes)
- Browse Chennai listings with prices in Indian rupees
- Search and filter by neighbourhood, room type, price and rating; click a column heading to sort
- Save favourites and export results to CSV
- Light and dark theme
- Book a stay with date and guest checks (no double bookings)
- View and cancel your bookings
- Data is kept in a local SQLite database (`stayfinder.db`, created on first run)

## Files
| File | What it does |
|---|---|
| `data.py` | Listing, booking and user classes, and the SQLite database |
| `rules.py` | Booking rules, validation, password hashing, and unit tests |
| `windows.py` | The login page and pop-up windows (details, booking) |
| `main_app.py` | The main window; run this file to start the app |
| `show_passwords.py` | Prints the `users` table to show passwords are saved as salted hashes |

## How to run
Needs Python 3 (tkinter and sqlite3 come with it, so nothing to install).

```
python main_app.py
```
On Windows you can also double-click `run.bat`.

Demo login: username `APPisfav`, password `fullmarks` (or create a new account).

## Run the tests
```
python -m unittest rules
```

## See the hashed passwords
Passwords are never saved as plain text. Each one is saved as `salt$sha256(salt + password)`.
After running the app once:
```
python show_passwords.py
```
