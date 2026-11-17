# StayFinder part 1 of 4 (Person 1): data classes and the database (all the SQL).
import os
import sqlite3
from datetime import date

# ==================== Data classes ====================

def money(amount):
    """Show a price in rupees, e.g. 1200 -> 'Rs 1,200'."""
    return "Rs " + format(round(amount), ",")

class Listing:
    def __init__(self, row):
        self.id = row["id"]
        self.name = row["name"]
        self.neighbourhood = row["neighbourhood"]
        self.room_type = row["room_type"]
        self.price = row["price"]
        self.reviews = row["number_of_reviews"]
        self.rating = row["rating"]
        self.host = row["host_name"]
        self.latitude = row["latitude"]
        self.longitude = row["longitude"]

    def rating_text(self):
        return "New" if self.rating is None else "%.2f" % self.rating

class User:
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.password_hash = row["password_hash"]

class Booking:
    def __init__(self, row):
        self.id = row["id"]
        self.user_id = row["user_id"]
        self.listing_id = row["listing_id"]
        self.listing_name = row["name"]
        self.check_in = date.fromisoformat(row["check_in"])
        self.check_out = date.fromisoformat(row["check_out"])
        self.guests = row["guests"]
        self.total = row["total"]
        self.status = row["status"]

    def nights(self):
        return (self.check_out - self.check_in).days

    def status_text(self):
        if self.status == "cancelled":
            return "Cancelled"
        return "Past" if self.check_out <= date.today() else "Upcoming"

# ==================== Database: all the SQL lives here ====================

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stayfinder.db")
# What each choice in the "Sort by" dropdown means in SQL
SORT_OPTIONS = {"Price (low to high)": "price ASC", "Price (high to low)": "price DESC",
                "Rating": "rating IS NULL, rating DESC",
                "Number of reviews": "number_of_reviews DESC"}
BOOKINGS_SQL = ("SELECT bookings.*, listings.name FROM bookings "
                "JOIN listings ON listings.id = bookings.listing_id ")

class Database:

    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row  # lets us write row["name"]
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS listings (id INTEGER PRIMARY KEY, name TEXT,
                neighbourhood TEXT, room_type TEXT, price REAL, number_of_reviews INTEGER,
                rating REAL, host_name TEXT, latitude REAL, longitude REAL);
            CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE, password_hash TEXT);
            CREATE TABLE IF NOT EXISTS favorites (user_id INTEGER, listing_id INTEGER,
                PRIMARY KEY (user_id, listing_id));
            CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, listing_id INTEGER, check_in TEXT, check_out TEXT,
                guests INTEGER, total REAL, status TEXT DEFAULT 'active');""")

    def run(self, sql, params=()):  # for queries that change the data
        self.conn.execute(sql, params)
        self.conn.commit()

    def one(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()

    def close(self):
        self.conn.close()

    # ----- listings -----
    def save_listings(self, rows):
        """Replace all listings. Bookings and favorites point at the old listings, so they go too."""
        for table in ["favorites", "bookings", "listings"]:
            self.conn.execute("DELETE FROM " + table)
        self.conn.executemany("INSERT INTO listings VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
        self.conn.commit()

    def count_listings(self):
        return self.one("SELECT COUNT(*) FROM listings")[0]

    def get_listing(self, listing_id):
        return Listing(self.one("SELECT * FROM listings WHERE id = ?", (listing_id,)))

    def search(self, text="", area="All", room="All", max_price=None, min_rating=0,
               hide_shared=False, sort="Price (low to high)"):
        sql = "SELECT * FROM listings WHERE name LIKE ?"
        params = ["%" + text.strip() + "%"]
        if area != "All":
            sql += " AND neighbourhood = ?"
            params.append(area)
        if room != "All":
            sql += " AND room_type = ?"
            params.append(room)
        if max_price is not None:
            sql += " AND price <= ?"
            params.append(max_price)
        if min_rating > 0:
            sql += " AND rating >= ?"
            params.append(min_rating)
        if hide_shared:
            sql += " AND room_type != 'Shared room'"
        sql += " ORDER BY " + SORT_OPTIONS[sort]
        return [Listing(row) for row in self.conn.execute(sql, params)]

    def get_choices(self, column):
        """Every different value in a column, for a dropdown. column is 'neighbourhood' or
        'room_type' (it comes from our own code, never from the user)."""
        return [row[0] for row in self.conn.execute(
            "SELECT DISTINCT %s FROM listings ORDER BY 1" % column)]

    def get_max_price(self):
        return self.one("SELECT MAX(price) FROM listings")[0] or 0

    # ----- users -----
    def add_user(self, username, password_hash):
        try:
            self.run("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                     (username, password_hash))
            return True
        except sqlite3.IntegrityError:  # the username is already taken
            return False

    def get_user(self, username):
        row = self.one("SELECT * FROM users WHERE username = ?", (username,))
        return User(row) if row else None

    # ----- favorites -----
    def add_favorite(self, user_id, listing_id):
        self.run("INSERT OR IGNORE INTO favorites VALUES (?, ?)", (user_id, listing_id))

    def remove_favorite(self, user_id, listing_id):
        self.run("DELETE FROM favorites WHERE user_id = ? AND listing_id = ?",
                 (user_id, listing_id))

    def is_favorite(self, user_id, listing_id):
        return self.one("SELECT 1 FROM favorites WHERE user_id = ? AND listing_id = ?",
                        (user_id, listing_id)) is not None

    def get_favorites(self, user_id):
        return [Listing(row) for row in self.conn.execute(
            "SELECT listings.* FROM listings JOIN favorites ON id = listing_id "
            "WHERE user_id = ? ORDER BY name", (user_id,))]

    # ----- bookings -----
    def add_booking(self, user_id, listing_id, check_in, check_out, guests, total):
        self.run("INSERT INTO bookings (user_id, listing_id, check_in, check_out, guests, total) "
                 "VALUES (?, ?, ?, ?, ?, ?)",
                 (user_id, listing_id, str(check_in), str(check_out), guests, total))

    def is_booked(self, listing_id, check_in, check_out):
        """True if an active booking overlaps these dates.
        Arriving on the day the last guest leaves is fine."""
        return self.one("SELECT 1 FROM bookings WHERE listing_id = ? AND status = 'active' "
                        "AND check_in < ? AND check_out > ?",
                        (listing_id, str(check_out), str(check_in))) is not None

    def has_booked(self, user_id, listing_id):
        """True if this user has an active stay at this listing that is not over yet."""
        return self.one("SELECT 1 FROM bookings WHERE user_id = ? AND listing_id = ? AND "
                        "status = 'active' AND check_out > ?",
                        (user_id, listing_id, str(date.today()))) is not None

    def get_bookings(self, user_id):
        return [Booking(row) for row in self.conn.execute(
            BOOKINGS_SQL + "WHERE user_id = ? ORDER BY check_in DESC", (user_id,))]

    def get_booking(self, booking_id):
        row = self.one(BOOKINGS_SQL + "WHERE bookings.id = ?", (booking_id,))
        return Booking(row) if row else None

    def cancel_booking(self, booking_id):
        self.run("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
