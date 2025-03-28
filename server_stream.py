from flask import Flask, render_template, Response, redirect, request
import time
from datetime import datetime
import os
import json
from utils import Utils

from dotenv import load_dotenv, dotenv_values

load_dotenv()

env_vars = dotenv_values(".env")

utils = Utils(__name__, Flask)
app = utils.get_app()

@app.route('/')
def root():
    return redirect('/big')

@app.route('/big')
def big_room():
    room = "Большая"
    date = datetime.now().strftime("%d.%m.%Y")
    bookings = utils.get_bookings(room, date)
    status = utils.get_status(room, date)
    display_name = "Большая переговорная (21 кабинет)"
    return render_template('index.html', room=room, display_name=display_name, date=date, bookings=bookings, status=status)

@app.route('/small')
def small_room():
    room = "Маленькая"
    date = datetime.now().strftime("%d.%m.%Y")
    bookings = utils.get_bookings(room, date)
    status = utils.get_status(room, date)
    display_name = "Малая переговорная (7 каб)"
    return render_template('index.html', room=room, display_name=display_name, date=date, bookings=bookings, status=status)

@app.route('/graf')
def graf():
    date = datetime.now().strftime("%d.%m.%Y")
    big_room_bookings = utils.get_bookings("Большая", date)
    small_room_bookings = utils.get_bookings("Маленькая", date)
    return render_template('graf.html', date=date, big_room_bookings=big_room_bookings, small_room_bookings=small_room_bookings)

@app.route('/stream/big')
def stream_big():
    return stream_room("Большая")

@app.route('/stream/small')
def stream_small():
    return stream_room("Маленькая")

#############################################################
#############################################################
#############################################################

@app.route('/api/add_record', methods=['POST'])
def add_record():
    data = request.get_json()
    
    values = {
        "Переговорная": "Большая",
        "Кабинет №7": "Маленькая"
    }
    
    if utils.is_time_available(data.get('room', ''), data.get('date', ''), data.get('time', '')) and data.get('api_key', '') == env_vars['API_KEY_DEFAULT']:
        try:
            Utils.record_booking(data={
                "room": values.get(data.get('room', ''), ''),
                "date": data.get('date', ''),
                "time": data.get('time', ''),
                "event_name": data.get('event_name', ''),
                "company": data.get('company', ''),
                "status": data.get('status', ''),
            })
            
            return {"status": "success"}
        except:
            return {"status": "failed"}
        
    # ДОПОЛНИТЕЛЬНАЯ ЛОГИКА ДЛЯ УДАЛЕНИЯ ЗАПИСЕЙ НА РУКОВОДИТЕЛЕ (КОГДА ДАТА И ВРЕМЯ УЖЕ ЕСТЬ В БАЗЕ ДАННЫХ, ТО СРАБАТЫВАЕТ.
    # НУЖЕН API КЛЮЧ, ПАРОЛЬ, ЮЗЕРНЕЙМ ДЛЯ РАБОТЫ В .env ФАЙЛЕ)
    
    # else:
    #     params = {
    #         'key': env_vars.get('API_KEY_RUKOVODITEL'),           
    #         'username': env_vars.get('USERNAME_RUKOVODITEL'),                                
    #         'password': env_vars.get('PASSWORD_RUKOVODITEL'),                                
    #         'action': 'delete',                                          
    #         'entity_id': 231,                                           
    #         'delete_by_field': {'id': int(data.get('record_id'))
    #     }
        
    #     requests.post(
    #         url="https://btg-sped.ru/crm/api/rest.php", 
    #         json=params
    #     )
    #     return {"status": "failed"}

#############################################################
#############################################################
#############################################################

def stream_room(room):
    def event_stream():
        last_modified = os.path.getmtime(utils.DB_PATH)
        while True:
            current_modified = os.path.getmtime(utils.DB_PATH)
            if current_modified != last_modified:
                last_modified = current_modified
                date = datetime.now().strftime("%d.%m.%Y")
                bookings = utils.get_bookings(room, date)
                status = utils.get_status(room, date)
                yield f"data: {json.dumps({'bookings': bookings, 'status': status})}\n\n"
            time.sleep(1)
    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)