from flask import Flask, render_template, request, session, url_for, redirect
from flask_socketio import SocketIO, send, join_room, leave_room, emit
from datetime import datetime
import random


app = Flask(__name__)
app.config['SECRET_KEY'] = 'SECRETKEY'
socketio = SocketIO(app)

rooms = {}

def generate_unique_room_id(numbers):
    while True:
        room_id = ""
        for _ in range(numbers):
            room_id += str(random.randint(0, 10))
        if room_id not in rooms:
            break
    return room_id

@app.route("/", methods=["GET", "POST"])
def landing_page():
    session.clear()

    if request.method == "POST":
        nickname = request.form.get("nickname")
        room_id = request.form.get("room-id")
        join_room = request.form.get("join-room", False)
        create_room = request.form.get("create-room", False)

        if not nickname:
            return render_template(
                "landing_page.html", 
                error="Your nickname must contain some characters.",
            )
        # elif nickname in nicknames:
        #     return render_template("landing_page.html", error=f"Nickname: '{nickname}' is already taken, try something else.")

        if join_room is not False and not room_id:
            return render_template(
                "landing_page.html", 
                error="Room ID cannot be empty.",
                nickname=nickname
            )
        elif join_room is not False and room_id not in rooms:
            return render_template(
                "landing_page.html", 
                error=f"Room with ID '{room_id}' does not exist.",
                nickname=nickname,
                room_id=room_id
            )
            
        if create_room is not False:
            room_id = generate_unique_room_id(4)
            print(room_id)
            rooms[room_id] = {"messages": [], "users": []}
        
        session["room_id"] = room_id
        session["nickname"] = nickname

        return redirect(url_for("chatroom"))

    return render_template("landing_page.html")

@app.route("/chatroom")
def chatroom():
    room_id = session.get("room_id")
    nickname = session.get("nickname")
    
    if room_id is None or nickname is None or room_id not in rooms:
        return redirect(url_for("landing_page"))

    return render_template(
        "chatroom.html", 
        room_id=room_id, 
        messages=rooms[room_id]["messages"],
        users=rooms[room_id]["users"]
    )


@socketio.on("connect")
def connect(): 
    room_id = session.get("room_id")
    nickname = session.get("nickname")

    if not room_id or not nickname:
        return
    if room_id not in rooms:
        leave_room(room_id)
        return 
    if nickname in rooms[room_id]["users"]:
        return

    join_room(room_id)
    if nickname not in rooms[room_id]["users"]:
        rooms[room_id]["users"].append(nickname)

    join_announcement = {
        "nickname": nickname,
        "message": "has entered the room",
        "date": datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    }
    emit("new_user_announcement", join_announcement, to=room_id)
    print(f"User {nickname} joined room: {room_id}")

@socketio.on("message")
def message(data):
    room_id = session.get("room_id")
    if room_id not in rooms:
        return
    
    content = {
        "nickname": session.get("nickname"),
        "message": data["msg"],
        "date": datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    }

    send(content, to=room_id)
    rooms[room_id]["messages"].append(content)
    print(f"User {session.get('nickname')} (room: {room_id}) said: {data['msg']}")

@socketio.on("disconnect")
def disconnect():
    room_id = session.get("room_id")
    nickname = session.get("nickname")
    leave_room(room_id)
    dc_announcement = {
        "nickname": nickname,
        "message": "has left the room",
        "date": datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    }
    emit("user_dc_announcement", dc_announcement, to=room_id)
    print(f"User {session.get('nickname')} has left room: {room_id}")

    if room_id in rooms:
        rooms[room_id]["users"].remove(nickname)
        if len(rooms[room_id]["users"]) == 0:
            del rooms[room_id]
            print(f"Room {room_id} has been deleted (no users left)")

    

if __name__ == '__main__':
    socketio.run(app, debug=True)
