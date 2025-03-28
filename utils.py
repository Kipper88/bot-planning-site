from flask import Flask
import sqlite3
from datetime import datetime

class Utils:
    def __init__(self, name, flask):
        self.app = flask(name)
        self.DB_PATH = "bookings.db"
        
    def get_app(self) -> Flask:
        return self.app

    def get_bookings(self, room, date):
        conn = sqlite3.connect(self.DB_PATH)
        c = conn.cursor()
        c.execute("SELECT time, company, event_name FROM bookings WHERE room=? AND date=? AND status='Занято'", (room, date))
        bookings = c.fetchall()
        conn.close()
        return bookings

    def get_status(self, room, date):
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        bookings = self.get_bookings(room, date)
        for booking in bookings:
            start, end = booking[0].split('-')
            if start <= current_time <= end:
                return "Занято"
        return "Свободно"

    def is_time_available(self, room, date, time) -> bool:
        try:
            with sqlite3.connect('bookings.db') as conn:
                c = conn.cursor()
                c.execute("SELECT time FROM bookings WHERE room=? AND date=? AND status='Занято'", (room, date))
                booked_times = c.fetchall()

            if not booked_times:
                return True

            new_start, new_end = time.split('-')
            new_start_hour, new_start_min = map(int, new_start.split(':'))
            new_end_hour, new_end_min = map(int, new_end.split(':'))
            new_start_minutes = new_start_hour * 60 + new_start_min
            new_end_minutes = new_end_hour * 60 + new_end_min

            for booked_time in booked_times:
                booked_start, booked_end = booked_time[0].split('-')
                booked_start_hour, booked_start_min = map(int, booked_start.split(':'))
                booked_end_hour, booked_end_min = map(int, booked_end.split(':'))
                booked_start_minutes = booked_start_hour * 60 + booked_start_min
                booked_end_minutes = booked_end_hour * 60 + booked_end_min

                if not (new_end_minutes <= booked_start_minutes or new_start_minutes >= booked_end_minutes):
                    return False
            return True
        except sqlite3.Error as e:
            return False
        
    def record_booking(data):
        try:
            with sqlite3.connect('bookings.db') as conn:
                c = conn.cursor()
                c.execute(
                    "INSERT INTO bookings (room, company, date, time, event_name, status, user_id) VALUES (?, ?, ?, ?, ?, 'Занято', ?)",
                    (data['room'], data['company'], data['date'],
                     data['time'], data['event_name'], str(1234567890)))
                conn.commit()
        except sqlite3.Error as e:
            raise str(e)