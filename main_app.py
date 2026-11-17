# StayFinder part 4 of 4 (Person 4): the main window, menus, themes and starting the app.
# Start the app with:  python main_app.py   Log in: username APPisfav, password fullmarks
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from data import Database, money
from rules import ValidationError, cancel, load_fake_listings, register, save_csv
from windows import COLUMNS, DetailWindow, LoginPage, SearchTab, TextWindow, fill_table, listing_row, make_table

THEMES = {"light": {"bg": "#eef2f5", "fg": "#1d2b36", "field": "#ffffff", "accent": "#1f7a8c",
                    "accent_fg": "#ffffff", "button": "#d9e2e8"},
          "dark": {"bg": "#22303a", "fg": "#e8eef2", "field": "#2f404c", "accent": "#4fb3c8",
                   "accent_fg": "#10232b", "button": "#3a4d5a"}}
BOOKING_COLUMNS = [("name", "Listing", 300), ("in", "Check-in", 100), ("out", "Check-out", 100),
                   ("nights", "Nights", 70), ("guests", "Guests", 70), ("total", "Total", 110),
                   ("status", "Status", 100)]

class App:
    def __init__(self, root, db):
        self.root, self.db = root, db
        self.user = None
        self.message_job = None
        self.theme = tk.StringVar(value="light")
        self.style = ttk.Style()
        self.style.theme_use("clam")
        root.title("StayFinder - stays in Chennai")
        root.geometry("1150x680")
        root.protocol("WM_DELETE_WINDOW", self.quit)  # ask before closing
        # keyboard shortcuts (Ctrl+F and Ctrl+R only work after you log in)
        root.bind("<Control-q>", lambda event: self.quit())
        root.bind("<Control-f>", lambda event: self.user and self.focus_search())
        root.bind("<Control-r>", lambda event: self.user and self.search.reset_filters())
        root.bind("<F1>", lambda event: TextWindow(self, "help"))
        self.apply_theme()
        self.show_login_page()

    # ----- switching between the login page and the main page -----
    def clear_window(self):
        if self.message_job:
            self.root.after_cancel(self.message_job)
            self.message_job = None
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.config(menu="")

    def show_login_page(self):
        self.clear_window()
        LoginPage(self.root, self).pack(fill="both", expand=True)

    def logged_in(self, user):
        """The login page calls this when the username and password are right."""
        self.user = user
        self.clear_window()
        self.build_main_page()
        self.show_message("Welcome, %s!" % user.username)

    def log_out(self):
        if messagebox.askyesno("Log out", "Log out of StayFinder?"):
            self.user = None
            self.show_login_page()

    # ----- main page -----
    def build_main_page(self):
        status = ttk.Frame(self.root, padding=(10, 4))  # status bar at the bottom
        status.pack(side="bottom", fill="x")
        self.count_label = ttk.Label(status)
        self.count_label.pack(side="left")
        ttk.Label(status, text="Logged in as " + self.user.username).pack(side="right")
        self.message_label = ttk.Label(status)
        self.message_label.pack()
        self.tabs = ttk.Notebook(self.root)
        self.search = SearchTab(self.root, self.tabs, self)  # also adds the filter panel
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.tabs.add(self.search.frame, text="Search")
        self.favorites_tab, self.favorites_table = self.make_tab(
            "Favorites", COLUMNS, self.open_listing, "Remove", self.remove_favorite)
        self.bookings_tab, self.bookings_table = self.make_tab(
            "Bookings", BOOKING_COLUMNS, self.open_booked_listing, "Cancel booking",
            self.cancel_booking)
        self.build_menu()
        self.apply_theme()
        self.refresh_favorites()
        self.refresh_bookings()

    def make_tab(self, title, columns, open_row, button_text, button_command):
        tab = ttk.Frame(self.tabs, padding=10)
        ttk.Label(tab, text="Double-click a row to open the listing.").pack(anchor="w")
        table_frame, table = make_table(tab, columns, open_row)
        table_frame.pack(fill="both", expand=True, pady=8)
        ttk.Button(tab, text=button_text, command=button_command).pack(side="right")
        self.tabs.add(tab, text=title)
        return tab, table

    def build_menu(self):
        # each menu is a list of (label, command, shortcut). None means a separator.
        menus = {
            "File": [("Export favorites", lambda: self.export(self.favorites_table), ""),
                     ("Export bookings", lambda: self.export(self.bookings_table), ""), None,
                     ("Log out", self.log_out, ""), ("Quit", self.quit, "Ctrl+Q")],
            "View": [None, ("Search", self.focus_search, "Ctrl+F"),
                     ("Reset filters", self.search.reset_filters, "Ctrl+R")],
            "Account": [("Log in as someone else", self.log_out, ""),
                        ("Register a new account", self.log_out, ""), None,
                        ("My bookings", lambda: self.tabs.select(self.bookings_tab), ""),
                        ("My favorites", lambda: self.tabs.select(self.favorites_tab), "")],
            "Help": [("How to Use", lambda: TextWindow(self, "help"), "F1"),
                     ("About and data credits", lambda: TextWindow(self, "about"), "")]}
        menubar = tk.Menu(self.root)
        for title, items in menus.items():
            menu = tk.Menu(menubar, tearoff=0)
            if title == "View":  # the View menu also has a Theme cascade and a checkbutton
                theme_menu = tk.Menu(menu, tearoff=0)
                for name in THEMES:
                    theme_menu.add_radiobutton(label=name.title(), value=name, variable=self.theme,
                                               command=self.apply_theme)
                menu.add_cascade(label="Theme", menu=theme_menu)
                menu.add_checkbutton(label="Hide shared rooms", variable=self.search.hide_shared)
            for item in items:
                if item is None:
                    menu.add_separator()
                else:
                    menu.add_command(label=item[0], command=item[1], accelerator=item[2])
            menubar.add_cascade(label=title, menu=menu)
        self.root.config(menu=menubar)

    # ----- theme and status bar -----
    def colors(self):
        return THEMES[self.theme.get()]

    def apply_theme(self):
        c = self.colors()
        self.style.configure(".", background=c["bg"], foreground=c["fg"], fieldbackground=c["field"])
        self.style.configure("Treeview", background=c["field"], rowheight=24)
        self.style.map("Treeview", background=[("selected", c["accent"])],
                       foreground=[("selected", c["accent_fg"])])
        self.style.configure("TButton", background=c["button"])
        self.style.configure("Treeview.Heading", background=c["button"])
        self.style.map("TCombobox", fieldbackground=[("readonly", c["field"])],
                       foreground=[("readonly", c["fg"])])
        self.style.configure("TNotebook.Tab", background=c["button"], padding=(14, 4))
        self.style.map("TNotebook.Tab", background=[("selected", c["bg"])])
        self.style.configure("Accent.TButton", background=c["accent"], foreground=c["accent_fg"])
        self.style.configure("Big.TLabel", font=("Arial", 12, "bold"))
        self.style.configure("Title.TLabel", font=("Arial", 24, "bold"))
        self.style.configure("Error.TLabel", foreground="#d64545")
        self.root.config(bg=c["bg"])
        if self.user:  # tk.Scale is not a ttk widget, so we colour it by hand
            self.search.price_slider.config(bg=c["bg"], fg=c["fg"], troughcolor=c["field"],
                                            highlightthickness=0)

    def set_result_count(self, count):
        self.count_label.config(text="%d results" % count)

    def show_message(self, text):
        """Show a message in the status bar. After 3 seconds it fades to grey, then goes."""
        if self.message_job:
            self.root.after_cancel(self.message_job)
        self.message_label.config(text=text, foreground=self.colors()["fg"])
        self.message_job = self.root.after(3000, self.fade_message)

    def fade_message(self):
        self.message_label.config(foreground="#999999")
        self.message_job = self.root.after(600, lambda: self.message_label.config(text=""))

    def focus_search(self):
        self.tabs.select(self.search.frame)
        self.search.search_box.focus_set()

    # ----- listings, favorites and bookings -----
    def open_listing(self, listing_id):
        DetailWindow(self, self.db.get_listing(listing_id))

    def open_booked_listing(self, booking_id):
        self.open_listing(self.db.get_booking(booking_id).listing_id)

    def toggle_favorite(self, listing):
        if self.db.is_favorite(self.user.id, listing.id):
            self.db.remove_favorite(self.user.id, listing.id)
            self.show_message("Removed from favorites")
        else:
            self.db.add_favorite(self.user.id, listing.id)
            self.show_message("Added to favorites")
        self.refresh_favorites()

    def refresh_favorites(self):
        fill_table(self.favorites_table, [listing_row(l) for l in self.db.get_favorites(self.user.id)])

    def refresh_bookings(self):
        fill_table(self.bookings_table, [
            (b.id, (b.listing_name, b.check_in, b.check_out, b.nights(), b.guests, money(b.total),
                    b.status_text())) for b in self.db.get_bookings(self.user.id)])
        for window in self.root.winfo_children():  # open listings show or hide their Book button
            if isinstance(window, DetailWindow):
                window.update_buttons()

    def selected_id(self, table):
        if not table.selection():
            messagebox.showinfo("Nothing selected", "Please click a row first.")
            return None
        return int(table.selection()[0])

    def remove_favorite(self):
        listing_id = self.selected_id(self.favorites_table)
        if listing_id:
            self.db.remove_favorite(self.user.id, listing_id)
            self.refresh_favorites()
            self.show_message("Removed from favorites")

    def cancel_booking(self):
        booking_id = self.selected_id(self.bookings_table)
        if not booking_id or not messagebox.askyesno("Cancel booking", "Cancel this booking?"):
            return
        try:
            cancel(self.db, self.user, booking_id)
        except ValidationError as error:
            messagebox.showerror("Cannot cancel", str(error))
            return
        self.refresh_bookings()
        self.show_message("Booking cancelled")

    def export(self, table):
        """Save what a table shows (favorites or bookings) to a CSV file."""
        rows = [table.item(item, "values") for item in table.get_children()]
        if not rows:
            messagebox.showinfo("Export", "There is nothing to export yet.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV files", "*.csv")])
        if path:
            save_csv(path, [table.heading(c, "text") for c in table["columns"]], rows)
            self.show_message("Saved %d rows to a CSV file" % len(rows))

    def quit(self):
        if messagebox.askyesno("Quit", "Do you want to quit StayFinder?"):
            self.db.close()
            self.root.destroy()

def main():
    db = Database()
    if db.count_listings() == 0:  # the first time, the database is empty, so fill it
        load_fake_listings(db)
    if db.get_user("APPisfav") is None:  # the ready-made account for logging in
        register(db, "APPisfav", "fullmarks")
    root = tk.Tk()
    App(root, db)
    root.mainloop()

if __name__ == "__main__":
    main()
