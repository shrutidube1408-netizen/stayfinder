# StayFinder part 2 of 4 (Person 2): the listings data, account and booking rules, and tests.
# Inside Airbnb (insideairbnb.com, CC BY 4.0) has no Chennai data, so we make ~400 fake listings.
import csv
import hashlib
import os
import random
import unittest
from datetime import date, timedelta

from data import Database

# ==================== Making and cleaning the listings CSV ====================

FAKE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "listings.csv")
MAX_LISTINGS = 2000  # a smaller set keeps the app fast
# Real Chennai areas with their rough location
AREAS = {"Adyar": (13.001, 80.257), "Alwarpet": (13.034, 80.252), "Anna Nagar": (13.085, 80.210),
         "Besant Nagar": (12.999, 80.267), "Egmore": (13.073, 80.261), "Guindy": (13.007, 80.221),
         "Mylapore": (13.037, 80.268), "Nungambakkam": (13.057, 80.243), "Porur": (13.038, 80.157),
         "T. Nagar": (13.042, 80.234), "Velachery": (12.982, 80.218)}
# room type: (usual price per night, words used in the name, how common it is)
ROOMS = {"Entire home/apt": (3200, ["flat", "villa", "studio"], 55),
         "Private room": (1400, ["room", "bedroom", "AC room"], 33),
         "Shared room": (600, ["shared room", "dorm bed"], 4),
         "Hotel room": (2800, ["hotel room", "service apartment"], 8)}
WORDS = ["Sunny", "Cosy", "Modern", "Heritage", "Quiet", "Spacious", "Airy", "Homely"]
EXTRAS = ["near the metro", "with balcony", "near the beach", "with parking", ""]
HOSTS = ["Arjun", "Deepa", "Divya", "Karthik", "Kavya", "Lakshmi", "Meena", "Murali", "Priya",
         "Ramesh", "Sanjay", "Swathi", "Vignesh"]

def make_fake_csv(path, count=420):
    random.seed(2026)  # the same fake data every time
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["id", "name", "host_name", "neighbourhood", "latitude", "longitude",
                         "room_type", "price", "number_of_reviews", "review_scores_rating"])
        for i in range(1, count + 1):
            area = random.choice(list(AREAS))
            room = random.choices(list(ROOMS), [r[2] for r in ROOMS.values()])[0]
            usual_price, words, _ = ROOMS[room]
            name = "%s %s in %s %s" % (random.choice(WORDS), random.choice(words), area,
                                       random.choice(EXTRAS))
            price = max(400, round(usual_price * random.uniform(0.5, 2) / 50) * 50)
            price_text = "Rs %s.00" % format(price, ",")  # messy text, like in real files
            if i % 25 == 0:
                price_text = ""  # some rows have no price, the cleaning drops them
            reviews = 0 if random.random() < 0.1 else random.randint(1, 150)  # some are new
            rating = round(random.uniform(3.8, 5.0), 2) if reviews else ""
            lat, lon = [round(x + random.uniform(-0.01, 0.01), 5) for x in AREAS[area]]
            writer.writerow([1000 + i, name.strip(), random.choice(HOSTS), area, lat, lon, room,
                             price_text, reviews, rating])

def to_number(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None

def clean_price(text):
    """'Rs 1,200.00' -> 1200.0. Returns None if there is no usable price."""
    for junk in ["Rs", "₹", "$", ",", " "]:
        text = text.replace(junk, "")
    price = to_number(text)
    return price if price and price > 0 else None

def clean_csv(path):
    """Keep only the columns the app uses and drop rows without a price."""
    rows, seen_ids = [], set()
    with open(path, newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            price = clean_price(row.get("price") or "")
            listing_id = row.get("id") or ""
            if price is None or not listing_id.isdigit() or listing_id in seen_ids:
                continue
            seen_ids.add(listing_id)
            area = row.get("neighbourhood_cleansed") or row.get("neighbourhood")
            rows.append((int(listing_id), row["name"], area, row["room_type"], price,
                         int(row.get("number_of_reviews") or 0), to_number(row.get("review_scores_rating")),
                         row.get("host_name") or "Unknown", to_number(row.get("latitude")),
                         to_number(row.get("longitude"))))
    return rows[:MAX_LISTINGS]

def load_fake_listings(db):
    make_fake_csv(FAKE_FILE)
    rows = clean_csv(FAKE_FILE)
    db.save_listings(rows)
    return len(rows)

# ==================== Rules for accounts and bookings (no tkinter here) ====================

MAX_GUESTS = 16

class ValidationError(Exception):
    """Raised when the user enters something that breaks a rule."""

def hash_password(password, salt=None):
    """Passwords are never saved as plain text. We save 'salt$hash'."""
    if salt is None:
        salt = os.urandom(8).hex()
    return salt + "$" + hashlib.sha256((salt + password).encode()).hexdigest()

def check_password(password, saved_hash):
    salt = saved_hash.split("$")[0]
    return hash_password(password, salt) == saved_hash

def register(db, username, password):
    username = username.strip()
    if len(username) < 3 or " " in username:
        raise ValidationError("Username needs 3 or more characters and no spaces.")
    if len(password) < 6:
        raise ValidationError("Password must be at least 6 characters.")
    if not db.add_user(username, hash_password(password)):
        raise ValidationError("That username is already taken.")
    return db.get_user(username)

def login(db, username, password):
    user = db.get_user(username.strip())
    if user is None or not check_password(password, user.password_hash):
        raise ValidationError("Wrong username or password.")
    return user

def make_date(year, month, day):
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        raise ValidationError("Please enter a real date.")

def read_guests(text):
    if not text.isdigit() or not 1 <= int(text) <= MAX_GUESTS:
        raise ValidationError("Guests must be a number from 1 to %d." % MAX_GUESTS)
    return int(text)

def count_nights(check_in, check_out):
    return (check_out - check_in).days

def total_price(price, check_in, check_out):
    return count_nights(check_in, check_out) * price

def check_booking(db, listing_id, check_in, check_out, today=None):
    if check_in < (today or date.today()):
        raise ValidationError("Check-in cannot be in the past.")
    if check_out <= check_in:
        raise ValidationError("Check-out must be after check-in.")
    if db.is_booked(listing_id, check_in, check_out):
        raise ValidationError("Sorry, this place is already booked on those dates.")

def book(db, user, listing, check_in, check_out, guests, today=None):
    check_booking(db, listing.id, check_in, check_out, today)
    total = total_price(listing.price, check_in, check_out)
    db.add_booking(user.id, listing.id, check_in, check_out, guests, total)
    return total

def cancel(db, user, booking_id, today=None):
    booking = db.get_booking(booking_id)
    if booking is None or booking.user_id != user.id:
        raise ValidationError("Booking not found.")
    if booking.status == "cancelled":
        raise ValidationError("This booking is already cancelled.")
    if booking.check_out <= (today or date.today()):
        raise ValidationError("You cannot cancel a stay that is over.")
    db.cancel_booking(booking_id)

def save_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)

# ==================== Tests (run: python -m unittest rules) ====================

TODAY = date(2026, 11, 15)
DAY = timedelta(days=1)

class TestStayFinder(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")  # a database that only lives in memory
        self.db.save_listings([
            (1, "Sunny flat in Adyar", "Adyar", "Entire home/apt", 3000, 50, 4.9, "A", 13, 80),
            (2, "Quiet room in Adyar", "Adyar", "Private room", 1200, 5, 4.2, "B", 13, 80),
            (3, "Sunny dorm in Egmore", "Egmore", "Shared room", 500, 0, None, "C", 13, 80)])
        self.user = register(self.db, "shreeya", "secret123")

    def test_search_and_sort(self):
        ids = lambda **filters: [listing.id for listing in self.db.search(**filters)]
        self.assertEqual(ids(), [3, 2, 1])
        self.assertEqual(ids(text="sunny"), [3, 1])
        self.assertEqual(ids(area="Adyar", room="Private room"), [2])
        self.assertEqual(ids(max_price=1200, hide_shared=True), [2])
        self.assertEqual(ids(min_rating=4.5, sort="Rating"), [1])
        self.assertEqual(self.db.get_choices("neighbourhood"), ["Adyar", "Egmore"])
        self.assertEqual(clean_price("Rs 1,200.00"), 1200)
        self.assertIsNone(clean_price(""))

    def test_accounts_and_favorites(self):
        self.assertNotIn("secret123", self.user.password_hash)  # the password is hashed
        self.assertEqual(login(self.db, "shreeya", "secret123").id, self.user.id)
        self.assertRaises(ValidationError, login, self.db, "shreeya", "wrong")
        self.assertRaises(ValidationError, register, self.db, "ab", "secret1")  # too short
        self.assertRaises(ValidationError, register, self.db, "asha", "12345")  # too short
        self.assertRaises(ValidationError, register, self.db, "shreeya", "secret1")  # taken
        self.db.add_favorite(self.user.id, 1)
        self.assertEqual([l.id for l in self.db.get_favorites(self.user.id)], [1])

    def test_booking_rules(self):
        listing = self.db.get_listing(1)
        self.assertEqual(total_price(3000, TODAY, TODAY + 3 * DAY), 9000)
        self.assertRaises(ValidationError, check_booking, self.db, 1, TODAY - DAY, TODAY)
        self.assertRaises(ValidationError, check_booking, self.db, 1, TODAY, TODAY, TODAY)
        self.assertRaises(ValidationError, make_date, "2027", "2", "30")
        self.assertRaises(ValidationError, read_guests, "0")
        start, end = TODAY + 5 * DAY, TODAY + 10 * DAY
        book(self.db, self.user, listing, start, end, 2, TODAY)
        self.assertRaises(ValidationError, book, self.db, self.user, listing,  # overlap
                          end - DAY, end + DAY, 2, TODAY)
        book(self.db, self.user, listing, end, end + DAY, 2, TODAY)  # arrive as they leave
        first = self.db.get_bookings(self.user.id)[1]
        cancel(self.db, self.user, first.id, TODAY)
        book(self.db, self.user, listing, start, end, 2, TODAY)  # dates are free again
