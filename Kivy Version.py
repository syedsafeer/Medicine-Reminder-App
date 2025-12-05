import kivy

kivy.require('2.2.1')

import sqlite3
import time
import threading
from datetime import datetime
from plyer import notification

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.properties import StringProperty, ListProperty, NumericProperty, ColorProperty
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle

from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.label import MDLabel
from kivymd.uix.gridlayout import MDGridLayout

# ----------------- DATABASE SETUP -----------------
DB_NAME = "medicine_reminder.db"


def setup_database():
    try:
        conn = sqlite3.connect(DB_NAME)
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
    except Exception as e:
        print(f"Database setup error: {e}")
    finally:
        if conn:
            conn.close()


setup_database()

# ----------------- KIVY UI DEFINITION (KV Language) -----------------
KV = """
<ReminderScreen>:
    orientation: 'vertical'
    padding: dp(15)
    spacing: dp(15)
    size_hint_y: 1 
    height: self.minimum_height 

    MDLabel:
        text: '💊 Medicine Reminder App ⏰'
        font_style: 'H5'
        halign: 'center'
        size_hint_y: None
        height: self.texture_size[1]
        color: 0.1, 0.5, 0.8, 1

    MDGridLayout:
        cols: 2
        spacing: dp(10)
        size_hint_y: None
        height: dp(250)

        MDLabel:
            text: 'Medicine Name:'
            size_hint_x: None
            width: dp(120)

        TextInput:
            id: name_input
            text: root.medicine_name
            on_text: root.medicine_name = self.text
            multiline: False
            background_color: 1, 1, 1, 1

        MDLabel:
            text: 'Date (YYYY-MM-DD):'

        Button:
            text: root.selected_date if root.selected_date else 'Select Date'
            on_release: root.show_date_picker()
            background_color: 0.2, 0.6, 0.8, 1

        MDLabel:
            text: 'Time (HH:MM AM/PM):'

        TextInput:
            id: time_input
            hint_text: 'e.g., 08:30 AM'
            text: root.time_input
            on_text: root.time_input = self.text
            multiline: False

    MDGridLayout:
        cols: 2
        spacing: dp(10)
        size_hint_y: None
        height: dp(100)
        padding: [0, dp(10), 0, dp(10)]

        Button:
            text: '➕ Add Medicine'
            on_release: root.add_medicine()
            background_color: 0.2, 0.8, 0.2, 1

        Button:
            text: '🔄 Update Selected'
            on_release: root.update_medicine()
            background_color: 0.8, 0.6, 0.2, 1

        Button:
            text: '🗑️ Delete Selected'
            on_release: root.delete_medicine()
            background_color: 0.8, 0.2, 0.2, 1

        Button:
            text: 'Refresh List'
            on_release: root.refresh_reminder_view()
            background_color: 0.5, 0.5, 0.5, 1

    MDLabel:
        text: 'Upcoming Reminders:'
        size_hint_y: None
        height: self.texture_size[1]

    GridLayout:
        cols: 4
        spacing: dp(1)
        size_hint_y: None
        height: dp(35)
        padding: dp(5)

        MDLabel:
            text: 'ID'
            bold: True
            size_hint_x: 0.1
        MDLabel:
            text: 'Name'
            bold: True
        MDLabel:
            text: 'Date'
            bold: True
        MDLabel:
            text: 'Time'
            bold: True

    ScrollView:
        size_hint: (1, 1)
        do_scroll_x: False
        GridLayout:
            id: reminder_list
            cols: 1 
            spacing: dp(1) 
            size_hint_y: None 
            height: self.minimum_height 
            padding: dp(5)

<ReminderRow>:
    cols: 4 
    size_hint_y: None
    height: dp(35)

    row_color: (1, 1, 1, 1) 

    canvas.before:
        Color:
            rgba: self.row_color
        Rectangle:
            pos: self.pos
            size: self.size

    on_touch_down: self.parent.parent.parent.select_row(self) if self.collide_point(*args[1].pos) else None

    MDLabel:
        id: row_id
        text: str(root.item_id)
        size_hint_x: 0.1
    MDLabel:
        id: row_name
        text: root.item_name
        text_size: self.size
    MDLabel:
        id: row_date
        text: root.item_date
    MDLabel:
        id: row_time
        text: root.item_time

"""

Builder.load_string(KV)


# ----------------- KIVY WIDGET CLASSES -----------------

class ReminderRow(GridLayout):
    item_id = NumericProperty(0)
    item_name = StringProperty('')
    item_date = StringProperty('')
    item_time = StringProperty('')
    row_color = ColorProperty([1, 1, 1, 1])

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            parent = self.parent.parent.parent
            parent.select_row(self)
        return super().on_touch_down(touch)


class ReminderScreen(BoxLayout):
    medicine_name = StringProperty('')
    selected_date = StringProperty('')
    time_input = StringProperty('')

    selected_reminder_id = NumericProperty(0)
    selected_row_widget = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.start_reminder_checker()
        Clock.schedule_once(lambda dt: self.refresh_reminder_view(), 0)

    def show_popup(self, title, message):
        popup = Popup(
            title=title,
            content=Label(text=message),
            size_hint=(0.7, 0.3),
            auto_dismiss=True
        )
        popup.open()

    def show_date_picker(self):
        try:
            initial_date = datetime.strptime(self.selected_date, "%Y-%m-%d").date()
        except ValueError:
            initial_date = datetime.now().date()

        date_dialog = MDDatePicker(
            year=initial_date.year,
            month=initial_date.month,
            day=initial_date.day
        )
        date_dialog.bind(on_save=self.on_date_save)
        date_dialog.open()

    def on_date_save(self, instance, value, date_range):
        self.selected_date = value.strftime("%Y-%m-%d")

    def validate_time(self, time_str):
        try:
            time_obj = datetime.strptime(time_str, "%I:%M %p")
            return time_obj.strftime("%I:%M %p")
        except ValueError:
            return None

    def add_medicine(self):
        name = self.medicine_name.strip()
        date = self.selected_date.strip()
        time_12 = self.validate_time(self.time_input.strip())

        if not name or not date or not time_12:
            self.show_popup("Error", "Please fill out all fields and use HH:MM AM/PM format.")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO medicines (name, date, time) VALUES (?, ?, ?)", (name, date, time_12))
            conn.commit()
            self.show_popup("Success", "Medicine added successfully!")

            self.medicine_name = ''
            self.time_input = ''
            self.selected_date = ''
            self.selected_reminder_id = 0
            self.unselect_row()

            self.refresh_reminder_view()
        except Exception as e:
            self.show_popup("Database Error", f"Could not add medicine: {e}")
        finally:
            conn.close()

    def update_medicine(self):
        if self.selected_reminder_id == 0:
            self.show_popup("Error", "Please select a medicine from the list to update.")
            return

        id = self.selected_reminder_id
        name = self.medicine_name.strip()
        date = self.selected_date.strip()
        time_12 = self.validate_time(self.time_input.strip())

        if not name or not date or not time_12:
            self.show_popup("Error", "Please fill out all fields and use HH:MM AM/PM format.")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE medicines SET name = ?, date = ?, time = ? WHERE id = ?", (name, date, time_12, id))
            conn.commit()
            self.show_popup("Success", "Medicine updated successfully!")

            self.medicine_name = ''
            self.time_input = ''
            self.selected_date = ''
            self.selected_reminder_id = 0
            self.unselect_row()

            self.refresh_reminder_view()
        except Exception as e:
            self.show_popup("Database Error", f"Could not update medicine: {e}")
        finally:
            conn.close()

    def delete_medicine(self):
        if self.selected_reminder_id == 0:
            self.show_popup("Error", "Please select a medicine from the list to delete.")
            return

        id = self.selected_reminder_id

        dialog = MDDialog(
            title="Confirm Deletion",
            text=f"Are you sure you want to delete reminder ID {id}?",
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda x: dialog.dismiss()),
                MDFlatButton(text="DELETE", text_color=App.get_running_app().theme_cls.error_color,
                             on_release=lambda x: self._execute_delete(id, dialog)),
            ],
        )
        dialog.open()

    def _execute_delete(self, id, dialog):
        dialog.dismiss()
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM medicines WHERE id = ?", (id,))
            conn.commit()
            self.show_popup("Success", "Medicine deleted successfully!")

            self.medicine_name = ''
            self.time_input = ''
            self.selected_date = ''
            self.selected_reminder_id = 0
            self.unselect_row()

            self.refresh_reminder_view()
        except Exception as e:
            self.show_popup("Database Error", f"Could not delete medicine: {e}")
        finally:
            conn.close()

    def refresh_reminder_view(self):

        list_container = self.ids.reminder_list

        rows_to_remove = [child for child in list_container.children if isinstance(child, ReminderRow)]
        for row in rows_to_remove:
            list_container.remove_widget(row)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medicines ORDER BY date, time")
        rows = cursor.fetchall()
        conn.close()

        for i, row in enumerate(rows):
            row_id, name, date, time = row

            if i % 2 == 0:
                bg_color = [0.95, 0.95, 0.95, 1]
            else:
                bg_color = [1, 1, 1, 1]

            new_row = ReminderRow(
                item_id=row_id,
                item_name=name,
                item_date=date,
                item_time=time,
                row_color=bg_color
            )

            list_container.add_widget(new_row)

        list_container.height = list_container.minimum_height

    def select_row(self, row_widget):
        self.unselect_row()

        row_widget.row_color = [0.1, 0.5, 0.8, 0.5]
        self.selected_row_widget = row_widget

        self.selected_reminder_id = row_widget.item_id
        self.medicine_name = row_widget.item_name
        self.selected_date = row_widget.item_date
        self.time_input = row_widget.item_time

    def unselect_row(self):
        if self.selected_row_widget:

            list_container = self.ids.reminder_list
            rows = [child for child in list_container.children if isinstance(child, ReminderRow)]

            try:
                display_list = rows[::-1]
                idx = display_list.index(self.selected_row_widget)

                if idx % 2 == 0:
                    self.selected_row_widget.row_color = [0.95, 0.95, 0.95, 1]
                else:
                    self.selected_row_widget.row_color = [1, 1, 1, 1]

            except ValueError:
                self.selected_row_widget.row_color = [1, 1, 1, 1]

            self.selected_row_widget = None

    # ----------------- REMINDER THREAD (Adapted) -----------------

    def start_reminder_checker(self):

        reminder_thread = threading.Thread(target=self.check_reminders_loop, daemon=True)
        reminder_thread.start()

    def check_reminders_loop(self):
        while True:
            time.sleep(60)
            current_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM medicines WHERE date || ' ' || time = ?", (current_time,))
            reminders = cursor.fetchall()
            conn.close()

            if reminders:
                for reminder in reminders:
                    medicine_name = reminder[0]
                    self.send_notification(medicine_name)

    def send_notification(self, medicine_name):
        try:
            notification.notify(
                title="Medicine Reminder 💊",
                message=f"Time to take your medicine: {medicine_name}",
                timeout=10
            )
        except Exception as e:
            print(f"Error sending notification via plyer: {e}. (Ensure plyer dependencies are installed for target OS)")
            print(f"REMINDER: {medicine_name} is due now!")


# ----------------- KIVY APPLICATION -----------------

class MedicineReminderApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"

        from kivy.uix.scrollview import ScrollView
        main_scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        main_scroll.add_widget(ReminderScreen())
        return main_scroll


if __name__ == '__main__':
    MedicineReminderApp().run()
