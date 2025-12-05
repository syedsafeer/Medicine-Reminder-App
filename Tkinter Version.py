import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from tkcalendar import Calendar
import sqlite3
import time
import threading
from datetime import datetime
from plyer import notification  # For cross-platform notifications
# Optional: For Windows, you can use win10toast if plyer doesn't work
# from win10toast import ToastNotifier


# Database Setup
def setup_database():
    conn = sqlite3.connect("medicine_reminder.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()


# Add Medicine to Database
def add_medicine():
    name = name_entry.get()
    date = cal.get_date()
    time_12 = time_entry.get()

    # Validate 12-hour time format
    try:
        time_obj = datetime.strptime(time_12, "%I:%M %p")  # Try parsing in 12-hour format
        time_12 = time_obj.strftime("%I:%M %p")  # Store in 12-hour format
    except ValueError:
        messagebox.showerror("Error", "Invalid time format. Please use HH:MM AM/PM format.")
        return

    if name and date and time_12:
        conn = sqlite3.connect("medicine_reminder.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO medicines (name, date, time) VALUES (?, ?, ?)", (name, date, time_12))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Medicine added successfully!")
        name_entry.delete(0, tk.END)
        time_entry.delete(0, tk.END)
        refresh_calendar_view()
    else:
        messagebox.showerror("Error", "Please fill out all fields.")


# Update Medicine in Database
def update_medicine():
    selected_item = tree.focus()
    if selected_item:
        item = tree.item(selected_item)
        id = item['values'][0]
        name = name_entry.get()
        date = cal.get_date()
        time_12 = time_entry.get()

        # Validate 12-hour time format
        try:
            time_obj = datetime.strptime(time_12, "%I:%M %p")  # Try parsing in 12-hour format
            time_12 = time_obj.strftime("%I:%M %p")  # Store in 12-hour format
        except ValueError:
            messagebox.showerror("Error", "Invalid time format. Please use HH:MM AM/PM format.")
            return

        if name and date and time_12:
            conn = sqlite3.connect("medicine_reminder.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE medicines SET name = ?, date = ?, time = ? WHERE id = ?", (name, date, time_12, id))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Medicine updated successfully!")
            refresh_calendar_view()
        else:
            messagebox.showerror("Error", "Please fill out all fields.")
    else:
        messagebox.showerror("Error", "Please select a medicine to update.")


# Delete Medicine from Database
def delete_medicine():
    selected_item = tree.focus()
    if selected_item:
        item = tree.item(selected_item)
        id = item['values'][0]

        conn = sqlite3.connect("medicine_reminder.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM medicines WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Medicine deleted successfully!")
        refresh_calendar_view()
    else:
        messagebox.showerror("Error", "Please select a medicine to delete.")


# Refresh Calendar View
def refresh_calendar_view():
    for row in tree.get_children():
        tree.delete(row)

    conn = sqlite3.connect("medicine_reminder.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medicines")
    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        tree.insert("", tk.END, values=row)


# Check Reminders
def check_reminders():
    while True:
        current_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")  # Current time in 12-hour format
        print(f"Checking time: {current_time}")  # Debugging log

        conn = sqlite3.connect("medicine_reminder.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM medicines WHERE date || ' ' || time = ?", (current_time,))
        reminders = cursor.fetchall()
        conn.close()

        if reminders:
            for reminder in reminders:
                print(f"Reminder found: {reminder[0]}")  # Debugging log
                send_notification(reminder[0])  # Call the function for sending notification
        else:
            print("No reminder found.")  # Debugging log

        time.sleep(60)  # Check every 60 seconds


# Function for sending notifications
def send_notification(medicine_name):
    try:
        # Use plyer for cross-platform notification
        notification.notify(
            title="Medicine Reminder",
            message=f"Time to take your medicine: {medicine_name}",
            timeout=10
        )
        # Optional: Use win10toast for Windows (uncomment the below lines if you want to use it)
        # toaster = ToastNotifier()
        # toaster.show_toast("Medicine Reminder", f"Time to take your medicine: {medicine_name}", duration=10)
    except Exception as e:
        print(f"Error sending notification: {e}")


# GUI Setup
setup_database()
root = tk.Tk()
root.title("Medicine Reminder App")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

tk.Label(frame, text="Medicine Name:").grid(row=0, column=0, sticky="w")
name_entry = tk.Entry(frame)
name_entry.grid(row=0, column=1)

tk.Label(frame, text="Date:").grid(row=1, column=0, sticky="w")
cal = Calendar(frame, selectmode="day", date_pattern="yyyy-mm-dd")
cal.grid(row=1, column=1)

tk.Label(frame, text="Time (HH:MM AM/PM):").grid(row=2, column=0, sticky="w")
time_entry = tk.Entry(frame)
time_entry.grid(row=2, column=1)

add_button = tk.Button(frame, text="Add Medicine", command=add_medicine)
add_button.grid(row=3, column=0, pady=10)

update_button = tk.Button(frame, text="Update Medicine", command=update_medicine)
update_button.grid(row=3, column=1, pady=10)

delete_button = tk.Button(frame, text="Delete Medicine", command=delete_medicine)
delete_button.grid(row=4, column=0, pady=10)

calendar_button = tk.Button(frame, text="Show Calendar", command=refresh_calendar_view)
calendar_button.grid(row=4, column=1, pady=10)

# Calendar View
tree_frame = tk.Frame(root)
tree_frame.pack(padx=10, pady=10)

tree = ttk.Treeview(tree_frame, columns=("ID", "Name", "Date", "Time"), show="headings")
tree.heading("ID", text="ID")
tree.heading("Name", text="Medicine Name")
tree.heading("Date", text="Date")
tree.heading("Time", text="Time")
tree.column("ID", width=30)
tree.pack(fill=tk.BOTH, expand=True)

refresh_calendar_view()

# Start Reminder Checker in a Separate Thread
reminder_thread = threading.Thread(target=check_reminders, daemon=True)
reminder_thread.start()

root.mainloop()
