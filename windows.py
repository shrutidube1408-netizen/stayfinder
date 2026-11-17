# StayFinder part 3 of 4 (Person 3): the search tab, the login page and the pop-up windows.
import random
import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox, ttk

from data import SORT_OPTIONS, money
from rules import MAX_GUESTS, ValidationError, book, check_booking, count_nights, login, make_date
from rules import read_guests, register

# ==================== Search tab: filter panel and results table ====================

COLUMNS = [("name", "Name", 340), ("area", "Neighbourhood", 140), ("room", "Room type", 130),
           ("price", "Price per night", 120), ("rating", "Rating", 70), ("reviews", "Reviews", 70)]

def listing_row(l):
    """One row for a listings table: (id, values shown in the columns)."""
    return l.id, (l.name, l.neighbourhood, l.room_type, money(l.price), l.rating_text(), l.reviews)

def make_table(parent, columns, open_row):
    """A Treeview with a scrollbar. Click a heading to sort, double-click a row to open it."""
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show="headings")
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    for key, title, width in columns:
        tree.heading(key, text=title, command=lambda k=key: sort_table(tree, k, False))
        tree.column(key, width=width)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def double_click(event):
        row = tree.identify_row(event.y)
        if row:  # empty if you double-click the heading
            open_row(int(row))
    tree.bind("<Double-1>", double_click)
    return frame, tree

def sort_table(tree, column, reverse):
    rows = [(tree.set(item, column), item) for item in tree.get_children()]
    rows.sort(key=lambda row: sort_key(row[0]), reverse=reverse)
    for position, (value, item) in enumerate(rows):
        tree.move(item, "", position)
    tree.heading(column, command=lambda: sort_table(tree, column, not reverse))  # next click reverses

def sort_key(text):
    """Sort numbers as numbers ('Rs 1,200' -> 1200) and everything else as text."""
    try:
        return (0, float(text.replace("Rs", "").replace(",", "")), "")
    except ValueError:
        return (1, 0, text.lower())

def fill_table(tree, rows):
    """rows is a list of (id, values). The id is used to find the row later."""
    tree.delete(*tree.get_children())
    for row_id, values in rows:
        tree.insert("", "end", iid=row_id, values=values)

class SearchTab:
    def __init__(self, root, notebook, app):
        self.app = app
        self.db = app.db
        self.waiting = None  # the after() job that will refresh the table
        self.top_price = (int(self.db.get_max_price()) // 500 + 1) * 500
        self.search_text, self.area, self.room = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.sort, self.min_rating = tk.StringVar(), tk.StringVar()
        self.max_price, self.hide_shared = tk.IntVar(), tk.BooleanVar()
        self.build_filter_panel(root)
        # the tab itself: a count label and the results table
        self.frame = ttk.Frame(notebook, padding=10)
        self.count_label = ttk.Label(self.frame, style="Big.TLabel")
        self.count_label.pack(anchor="w", pady=(0, 8))
        table_frame, self.tree = make_table(self.frame, COLUMNS, app.open_listing)
        table_frame.pack(fill="both", expand=True)
        self.reset_filters()
        # when any filter changes, refresh the results
        for var in [self.search_text, self.area, self.room, self.sort, self.max_price,
                    self.min_rating, self.hide_shared]:
            var.trace_add("write", self.filters_changed)

    def build_filter_panel(self, root):
        panel = ttk.LabelFrame(root, text="Search and filters", padding=10)
        panel.pack(fill="x", padx=10, pady=(8, 4))
        ttk.Label(panel, text="Search").grid(row=0, column=0, sticky="w")
        self.search_box = ttk.Entry(panel, textvariable=self.search_text, width=34)
        self.search_box.grid(row=0, column=1, columnspan=2, sticky="w", padx=5)
        self.search_box.bind("<Return>", lambda event: self.refresh())
        dropdowns = [("Neighbourhood", self.area, ["All"] + self.db.get_choices("neighbourhood")),
                     ("Room type", self.room, ["All"] + self.db.get_choices("room_type")),
                     ("Sort by", self.sort, list(SORT_OPTIONS))]
        for i, (label, var, values) in enumerate(dropdowns):
            ttk.Label(panel, text=label).grid(row=0, column=3 + i * 2, padx=(15, 5))
            ttk.Combobox(panel, textvariable=var, values=values, state="readonly",
                         width=17).grid(row=0, column=4 + i * 2)
        ttk.Label(panel, text="Max price (Rs)").grid(row=1, column=0, sticky="w")
        self.price_slider = tk.Scale(panel, from_=500, to=self.top_price, resolution=500,
                                     orient="horizontal", variable=self.max_price, length=260)
        self.price_slider.grid(row=1, column=1, columnspan=2, sticky="w", padx=5)
        ttk.Label(panel, text="Min rating").grid(row=1, column=3, padx=(15, 5))
        ratings = ttk.Frame(panel)
        ratings.grid(row=1, column=4, columnspan=2, sticky="w")
        for text, value in [("Any", "0"), ("4.0+", "4.0"), ("4.5+", "4.5")]:
            ttk.Radiobutton(ratings, text=text, value=value, variable=self.min_rating).pack(side="left")
        ttk.Checkbutton(panel, text="Hide shared rooms", variable=self.hide_shared).grid(
            row=1, column=6, padx=(15, 5))
        ttk.Button(panel, text="Reset filters", command=self.reset_filters).grid(row=1, column=7)

    def filters_changed(self, *args):
        # wait a moment so the table does not flicker while you type
        if self.waiting:
            self.frame.after_cancel(self.waiting)
        self.waiting = self.frame.after(300, self.refresh)

    def refresh(self):
        self.waiting = None
        max_price = self.max_price.get()
        if max_price >= self.top_price:
            max_price = None  # slider at the top: show every price
        listings = self.db.search(self.search_text.get(), self.area.get(), self.room.get(), max_price,
                                  float(self.min_rating.get()), self.hide_shared.get(), self.sort.get())
        fill_table(self.tree, [listing_row(l) for l in listings])
        self.count_label.config(text="%d listings found" % len(listings))
        self.app.set_result_count(len(listings))

    def reset_filters(self):
        self.search_text.set("")
        self.area.set("All")
        self.room.set("All")
        self.sort.set("Price (low to high)")
        self.max_price.set(self.top_price)  # the top of the slider means any price
        self.min_rating.set("0")
        self.hide_shared.set(False)
        self.refresh()

# ==================== Login page and pop-up windows ====================

class LoginPage(ttk.Frame):
    """The first page of the app. Log in, or create a new account."""

    def __init__(self, root, app):
        super().__init__(root)
        self.app = app
        self.username, self.password, self.error = tk.StringVar(), tk.StringVar(), tk.StringVar()
        box = ttk.Frame(self, padding=30)
        box.place(relx=0.5, rely=0.45, anchor="center")  # keep it in the middle of the window
        canvas = tk.Canvas(box, width=140, height=100, highlightthickness=0)
        canvas.grid(row=0, column=0, columnspan=2)
        draw_house(canvas, 7, 140, 100)
        ttk.Label(box, text="StayFinder", style="Title.TLabel").grid(row=1, columnspan=2)
        ttk.Label(box, text="Find and book stays in Chennai").grid(row=2, columnspan=2, pady=(0, 20))
        for row, label, var in [(3, "Username", self.username), (4, "Password", self.password)]:
            ttk.Label(box, text=label).grid(row=row, column=0, sticky="w", pady=4)
            entry = ttk.Entry(box, textvariable=var, width=28, show="*" if row == 4 else "")
            entry.grid(row=row, column=1, pady=4)
            entry.bind("<Return>", lambda event: self.submit("login"))
            if row == 3:
                entry.focus_set()
        ttk.Label(box, textvariable=self.error, style="Error.TLabel", wraplength=320).grid(
            row=5, column=0, columnspan=2, pady=8)
        ttk.Button(box, text="Log in", style="Accent.TButton", command=lambda: self.submit("login")
                   ).grid(row=6, column=0, columnspan=2, sticky="ew")
        ttk.Button(box, text="Create a new account", command=lambda: self.submit("register")
                   ).grid(row=7, column=0, columnspan=2, sticky="ew", pady=6)

    def submit(self, action):
        try:
            if action == "register":
                user = register(self.app.db, self.username.get(), self.password.get())
            else:
                user = login(self.app.db, self.username.get(), self.password.get())
        except ValidationError as error:
            self.error.set(str(error))
            return
        self.app.logged_in(user)  # go to the main page

def draw_house(canvas, seed, w, h):
    """Draw a simple house with shapes. The same seed always gives the same house."""
    rand = random.Random(seed)
    canvas.create_rectangle(0, 0, w, h, fill="#bfe0ee", outline="")  # sky
    canvas.create_oval(w - 45, 10, w - 15, 40, fill="#f2c94c", outline="")  # sun
    canvas.create_rectangle(0, h * 0.82, w, h, fill="#7fa36b", outline="")  # grass
    wall = rand.choice(["#c0674b", "#5d7585", "#6e8a70", "#b28a5c", "#7c6a8c"])
    canvas.create_rectangle(w * 0.3, h * 0.42, w * 0.7, h * 0.85, fill=wall, outline="")
    canvas.create_polygon(w * 0.3 - 10, h * 0.42, w / 2, h * 0.15, w * 0.7 + 10, h * 0.42,
                          fill="#5b3a29")  # roof
    canvas.create_rectangle(w * 0.47, h * 0.65, w * 0.53, h * 0.85, fill="#3b2a20", outline="")
    for x in [w * 0.35, w * 0.58]:  # two windows
        canvas.create_rectangle(x, h * 0.5, x + w * 0.07, h * 0.6, outline="",
                                fill=rand.choice(["#fff3b0", "#dcebf2"]))

class DetailWindow(tk.Toplevel):
    def __init__(self, app, listing):
        super().__init__(app.root)
        self.app, self.listing = app, listing
        self.title(listing.name)
        self.config(bg=app.colors()["bg"])
        canvas = tk.Canvas(self, width=420, height=190, highlightthickness=0)
        canvas.pack(padx=15, pady=15)
        draw_house(canvas, listing.id, 420, 190)
        info = ttk.LabelFrame(self, text="Listing details", padding=10)
        info.pack(fill="x", padx=15)
        facts = [("Name", listing.name), ("Neighbourhood", listing.neighbourhood),
                 ("Room type", listing.room_type), ("Host", listing.host),
                 ("Rating", "%s (%d reviews)" % (listing.rating_text(), listing.reviews)),
                 ("Price", money(listing.price) + " per night"),
                 ("Location", "%s, %s" % (listing.latitude, listing.longitude))]
        for row, (label, value) in enumerate(facts):
            ttk.Label(info, text=label + ":").grid(row=row, column=0, sticky="w")
            ttk.Label(info, text=value).grid(row=row, column=1, sticky="w", padx=10)
        buttons = ttk.Frame(self, padding=15)
        buttons.pack(anchor="e")
        self.favorite_button = ttk.Button(buttons, command=self.toggle_favorite)
        self.favorite_button.grid(row=0, column=0, padx=8)
        self.book_button = ttk.Button(buttons, text="Book", style="Accent.TButton",
                                      command=lambda: BookingWindow(app, listing))
        self.book_button.grid(row=0, column=1)
        self.booked_label = ttk.Label(buttons, text="You have booked this stay", style="Big.TLabel")
        self.booked_label.grid(row=0, column=1)
        self.update_buttons()

    def toggle_favorite(self):
        self.app.toggle_favorite(self.listing)
        self.update_buttons()

    def update_buttons(self):
        """Set the favorite button text, and hide Book once this stay is booked."""
        saved = self.app.db.is_favorite(self.app.user.id, self.listing.id)
        self.favorite_button.config(text="Remove favorite" if saved else "Add to favorites")
        if self.app.db.has_booked(self.app.user.id, self.listing.id):
            self.book_button.grid_remove()
            self.booked_label.grid()
        else:
            self.booked_label.grid_remove()
            self.book_button.grid()

class BookingWindow(tk.Toplevel):
    def __init__(self, app, listing):
        super().__init__(app.root)
        self.app, self.listing = app, listing
        self.title("Book a stay")
        self.config(bg=app.colors()["bg"])
        self.grab_set()  # you must finish or close this window before using the main window
        frame = ttk.Frame(self, padding=20)
        frame.pack()
        ttk.Label(frame, text=listing.name, style="Big.TLabel").grid(row=0, columnspan=4, sticky="w")
        ttk.Label(frame, text=money(listing.price) + " per night. Dates are day / month / year."
                  ).grid(row=1, columnspan=4, sticky="w", pady=(0, 10))
        tomorrow = date.today() + timedelta(days=1)
        self.check_in = self.date_row(frame, 3, "Check-in", tomorrow)
        self.check_out = self.date_row(frame, 4, "Check-out", tomorrow + timedelta(days=2))
        ttk.Label(frame, text="Guests").grid(row=5, column=0, sticky="w", pady=4)
        self.guests = tk.StringVar(value="1")
        ttk.Spinbox(frame, from_=1, to=MAX_GUESTS, textvariable=self.guests,
                    width=5).grid(row=5, column=1)
        self.total, self.error = tk.StringVar(), tk.StringVar()
        for row, var, style in [(6, self.total, "Big.TLabel"), (7, self.error, "Error.TLabel")]:
            ttk.Label(frame, textvariable=var, style=style).grid(row=row, columnspan=4, sticky="w",
                                                                 pady=(6, 0))
        ttk.Button(frame, text="Cancel", command=self.destroy).grid(row=8, column=2, pady=(12, 0))
        self.confirm_button = ttk.Button(frame, text="Confirm", style="Accent.TButton",
                                         command=self.confirm)
        self.confirm_button.grid(row=8, column=3, pady=(12, 0))
        for var in self.check_in + self.check_out + [self.guests]:
            var.trace_add("write", self.update_total)  # new total whenever a field changes
        self.update_total()

    def date_row(self, frame, row, label, start):
        """Three Spinboxes for the day, month and year. Returns their StringVars."""
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10))
        variables = []
        for column, value, low, high in [(1, start.day, 1, 31), (2, start.month, 1, 12),
                                         (3, start.year, start.year, start.year + 2)]:
            variables.append(tk.StringVar(value=value))
            ttk.Spinbox(frame, from_=low, to=high, textvariable=variables[-1],
                        width=5).grid(row=row, column=column, padx=2, pady=4)
        return variables

    def read_form(self):
        """Check the form. Returns (check_in, check_out, guests) or raises ValidationError."""
        day, month, year = [var.get() for var in self.check_in]
        check_in = make_date(year, month, day)
        day, month, year = [var.get() for var in self.check_out]
        check_out = make_date(year, month, day)
        guests = read_guests(self.guests.get())
        check_booking(self.app.db, self.listing.id, check_in, check_out)
        return check_in, check_out, guests

    def update_total(self, *args):
        """Show the total, or what is wrong. Confirm only works when the form is OK."""
        try:
            check_in, check_out, guests = self.read_form()
        except ValidationError as error:
            self.error.set(str(error))
            self.total.set("Total: -")
            self.confirm_button.state(["disabled"])
            return
        nights = count_nights(check_in, check_out)
        self.error.set("")
        self.total.set("Total: %d nights x %s = %s" % (nights, money(self.listing.price),
                                                       money(nights * self.listing.price)))
        self.confirm_button.state(["!disabled"])

    def confirm(self):
        try:
            check_in, check_out, guests = self.read_form()
            total = book(self.app.db, self.app.user, self.listing, check_in, check_out, guests)
        except ValidationError as error:
            messagebox.showerror("Cannot book", str(error), parent=self)
            return
        self.destroy()
        self.app.refresh_bookings()
        messagebox.showinfo("Booking confirmed", "%s\n%s to %s\nTotal: %s" % (
            self.listing.name, check_in, check_out, money(total)))

TEXTS = {"help": ("How to Use", """How to use StayFinder

1. Type in the search box, or use the dropdowns, price slider and rating buttons.
2. Click a column heading to sort by it, and click again to reverse.
3. Double-click a listing to see it. Then add it to favorites or book it.
4. File > Export saves your favorites or bookings as a CSV file.

Shortcuts: Ctrl+F search, Ctrl+R reset filters, F1 help, Ctrl+Q quit"""),
         "about": ("About StayFinder", """StayFinder lets you search and book stays in Chennai.
Prices are in Indian rupees (Rs) per night. Built with Python, tkinter and SQLite.

Data credits: the listing columns follow the free data files from Inside Airbnb
(insideairbnb.com, CC BY 4.0). Inside Airbnb has no data for Chennai, so the listings
here are made up (the area names are real). StayFinder is not part of Airbnb.""")}

class TextWindow(tk.Toplevel):
    """The Help and About windows: some text and a Close button."""

    def __init__(self, app, which):
        super().__init__(app.root)
        title, text = TEXTS[which]
        self.title(title)
        self.config(bg=app.colors()["bg"])
        ttk.Label(self, text=text, padding=20, justify="left").pack()
        ttk.Button(self, text="Close", command=self.destroy).pack(pady=(0, 15))
