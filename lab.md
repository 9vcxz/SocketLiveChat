# Implementacja prostego livechatu z SocketIO
<br>

## Wstęp

<!-- ### Czym jest socket? -->
**Socket**, z języka angielskiego "gniazdo", to pewna abstrakcja implementowana na poziomie software'u. Wykorzystuje ona narzędzia zapewnione przez system, do ustanowienia dwukierunkowej komunikacji pomiędzy procesami. Mogą to być procesy lokalne działające na tej samej maszynie, lub komunikujące się przez sieć.
Typowo sockety są wykorzystywane w czatach, grach multiplayer, komunikatorach głosowych/wideo, czy do zapewnienia pewnych rodzajów interaktywności na stronach internetowych np. wysyłanie powiadomień, czy aktualizowanie danych na żywo (giełda).

**WebSocket** to protokół warstwy aplikacji wykorzystujący sockety TCP w kontekście komunikacji klient (zwykle przeglądarka) <-> serwer. Jest do alternatywa do cyklicznych odpytań serwera (polling), które tworzy większe obciążenie, oraz wyższe opóźnienia. Połączenie zaczyna się od handshake'u HTTP, jeśli się powiedzie, to znaczy że klient i serwer zgodzili się na używanie połączenia TCP (ustanowionego dla handshake'a), jako połączenia WebSocket. 
Sama implementacja WebSocketu sprowadza się do utworzenia specjalnych endpointów w backendzie obsługujących ten protokół, oraz otwarcia połączenia po stronie klienta, gdzie nasłuchuje się zdarzeń (i odpowiednio na nie reaguje) oraz wysyła dane do backendu. 

Kolejną warstwą abstrakcji jest biblioteka **SocketIO**, która do komunikacji używa swojego protokołu wykorzystującego WebSocket, oraz zapewnia opcje takie jak: automatyczne odnowienie połączenia, mechanizmy fallback (np. przełączenie się na polling), czy wsparcie dla pokoi (wysyłanie danych dla konkretnych grup użytkowników). Generalnie, razem z SocketIO dostajemy do dyspozycji zestaw gotowych funkcji, które w nisko-poziomowym podejściu wykorzystującym czyste WebSockety (np. biblioteka websockets w Pythonie) musielibyśmy implementować sami.

## Lab

Podczas tego laboratorium zajmiemy się implementacją prostego czatu przy użyciu Flaska i SocketIO. 
#### Ogólny zarys projektu obejmuje:
- brak systemu logowania, użytkownicy są rozpoznawani korzystając z mechanizmu `session`, pseudonimy są unikatowe
- wsparcie dla pokojów (chatroomów), gdzie użytkownicy mogą je tworzyć, wchodzić do nich i z nich wychodzić, gdy wszyscy opuszczą dany pokój, jest on kasowany.
- nowi użytkownicy dołączający do istniejącego pokoju widzą wiadomości wysłane przed ich dotarciem

#### Struktura plików:
```
./
├── templates/
│   ├── base.html
│   ├── chatroom.html
│   └── landing_page.html
└── main.py
```
---
Zacznijmy od stworzenia wirtualnego środowiska: `python3 -m venv .venv`, aktywowania go: `source .venv/bin/activate` oraz instalacji Flaska i Flaskowej implementacji SocketIO `pip install flask flask-socketio`

Do pliku `main.py` wklej poniższy kod. Zawiera on utworzenie instancji Flaska, która jest rozszerzona o obsługe protokołu SocketIO, do tego od razu importujemy wszystkie funkcje, z których będziemy korzystać.
```
from flask import Flask, render_template, request, session, url_for, redirect
from flask_socketio import SocketIO, send, join_room, leave_room, emit
from datetime import datetime
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'SECRETKEY'
socketio = SocketIO(app)

if __name__ == '__main__':
    socketio.run(app, debug=True)
```
Ze strony frontendu, wklej poniższy kod do `base.html`. Dołączamy do niego SocketIO i Boostrap przez CDN.
```
<!DOCTYPE html>
<html lang="en">
<head>
    <title>LiveChat</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script 
        src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js" 
        integrity="sha512-q/dWJ3kcmjBLU4Qc47E4A9kTB4m3wuTY7vkFJDTZKjTs8jhyGQnaUrxa0Ytd0ssMZhbNua9hE+E7Qv1j+DyZwA==" 
        crossorigin="anonymous"
    ></script>
    <link 
        href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" 
        rel="stylesheet" 
        integrity="sha384-EVSTQN3/azprG1Anm3QDgpJLIm9Nao0Yz1ztcQTwFspd3yD65VohhpuuCOmLASjC" 
        crossorigin="anonymous"
    >
    <script 
        src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/js/bootstrap.bundle.min.js" 
        integrity="sha384-MrcW6ZMFYlzcLA8Nl+NtUVF0sA7MsXsP1UyJoMp4YLEuNSfAP+JcXn/tWtIaxVXM" 
        crossorigin="anonymous"
    ></script>
</head>
<body>
    <div class="container-lg" style="background-color:rgb(255,255,255);">
        <div class="row my-5">
            {% block content %}{% endblock %}
        </div>
    </div>
</body>
</html>
```
Strona `landing_page.html` będzie naszą stroną główną. Tam użytkownik będzie mógł wybrać swój unikalny nickname, oraz dołączyć do istniejącego pokoju, lub utworzyć nowy. Strona `chatroom.html`, jak sama nazwa na to wskazuje, będzie odpowiedzialna za wyświetlanie czatu, więc to tam za pomocą JS'a będziemy nasłuchiwać wydarzenia i wysyłać wiadomości. 
**Rozszerz `main.py` o obsługę tych dwóch endpointów. Pamiętaj o obsłudze metod GET i POST przez landing_page.**


Do uzupełnienia `landing_page.html`, możesz wykorzystać kod znajdujący się poniżej.
```
{% extends "base.html"%}
{% block content %}
<div class="row justify-content-center">
    <div class="card col-6 justify-content-center">
        <form method="POST">
            {% if error %}
                <div class="alert alert-warning my-2" role="alert">
                    {{ error }}
                </div>
            {% endif %}
            <div class="row">
                <div class="col my-2">
                    <input type="text" class="form-control" name="nickname" placeholder="Nickname" value={{nickname}}>
                </div>
            </div>
            <div class="row">
                <div class="col my-2">
                    <div class="input-group mb">
                        <input type="text" class="form-control" name="room-id" placeholder="Room ID" value={{room_id}}>
                        <button class="btn btn-outline-primary" type="submit" name="join-room">Join existing room</button>
                    </div>
                </div>
            </div>
            <div class="row">
                <div class="col my-2">
                    <button type="submit" class="btn w-100 btn-outline-primary" name="create-room">Create new room</button>
                </div>
            </div>
        </form>
    </div>
</div>
{% endblock content %}
```
Z kolei do `chatroom.html`:
```
{% extends "base.html" %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-8">
        <div class="card">
            <p class="text-center h3 my-2">Chatroom {{ room_id }}</p>
        </div>
        <div class="card my-2 d-flex flex-column-reverse overflow-auto" style="height: 480px;">
            <div id="room-messages"></div>
        </div>
        <div class="row">
            <div class="col my-2">
                <div class="input-group mb">
                    <input type="text" class="form-control" id="message" placeholder="Message">
                    <button class="btn btn-outline-primary" type="button" name="send-message">Send</button>
                    <button class="btn btn-outline-danger" type="button" name="disconnect">Disconnect</button>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock content %}
```

---

Wiemy, że użytkownik będzie rozpoznawany po ID swojej sesji `request.sid`, jednak zgodnie z założeniami chcemy, aby pseudonimy były unikalne. Tym zajmiemy się nieco później, narazie skupmy się na walidacji treści, którą użytkownik przesyła na stronie startowej. Chcemy, żeby:
- nick nie był pusty
- jeżeli użytkownik chce dołączyć do istniejącego pokoju, to jego ID nie może być puste i pokój o danym ID musi istnieć
- użytkownik chcący stworzyć nowy pokój - stworzy pokój o <u>unikalnym</u> ID
- jeżeli wszystko będzie się zgadzać, to użytkownik zostanie przekierowany na stronę czatrooomu, a do jego sesji zostanie przypisane ID pokoju i jego nickname.

Same pokoje będziemy przechowywać w słowniku o strukturze: `rooms[room_id] = {"messages": [], "users": []}`, więc każdy pokój będzie wiedział kto w nim jest, oraz będzie przechowywać wszystkie wiadomości, które zostały w nim wysłane.

**Stwórz pusty słownik `rooms`, oraz w endpoincie odpowiedzialnym za stronę główną wklej na samym początku: `session.clear()`, aby po każdym otwarciu strony głównej sesja się resetowała. Do tego zapewnij w tym endpoincie takie warunki, aby powyższe 4 podpunkty zostały spełnione. Użytkownik powienien wiedzieć co poszło źle, więc przy niepowodzeniach wygeneruj alert w `landing_page.html` ze stosownym komunikatem.**

<u>Protip</u>: żeby sprawdzić, który guzik został wciśnięty możesz użyć: `join_room = request.form.get("join-room", False)`, tym sposobem, jeżeli warunek: `if join_room is not False:` jest spełniony, to znaczy, że użytkownik kliknął guzik z nazwą _join-room_.

<u>Protip2</u>: do sesji można przypisywać własne zmienne np.: `session["room_id"] = room_id`.

**Uzupełniając endpoint chatroomu, wykorzystamy informację o ID pokoju, do którego dołączył użytkownik, zawartą w jego sesji `session.get()` i na jej podstawie, wstrzykniemy do templatki niezbędne dane:**
```
return render_template(
        "chatroom.html", 
        room_id=room_id, 
        messages=rooms[room_id]["messages"],
        users=rooms[room_id]["users"]
    )
```
**Oprócz tego, jeśli użytkownik nie posiada pseudonimu lub ID pokoju w swojej sesji, przekieruj go na stronę główną przy użyciu `redirect()`.**

Teraz obok napisu _Chatroom_ w na stronie czatu, powinno się znaleźć ID pokoju.

---

Biblioteka SocketIO zawiera predefiniowane eventy, jednym z nich jest _connect_, kiedy to klient ustanawia połączenie z serwerem. Przejdźmy więc do `chatroom.html` i stwórzmy instancję SocketIO po stronie klienta: `var socketio = io();`. Po dołączeniu użytkownika możemy przechwycić ten event we frontendzie: 
```
    socketio.on('connect', () => {
        
    });
```
Oraz w backendzie:
```
@socketio.on("connect")
def connect(): ...
```
Są to wcześniej wspomniane "specjalne" endpointy do komunikacji w czasie rzeczywistym.

Wracając do sprawy z unikalnością nicków - **w `main.py` stwórz pusty słownik `connected_users = {}`, następnie stwórz endpoint, który będzie się uaktywniał podczas dołączenia nowego użytkownika:**
```
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

    # tu_wklej

    connected_users.update({request.sid: {"nickname": nickname, "room_id": room_id}})
    print(f'Connected users: {connected_users}')
```
Teraz po każdym dołączeniu użytkownika (nowa karta w przeglądarce) powinieneś widzieć wyprintowany komunikat o aktualnie połączonych użytkownikach. Jednak żeby połączyć się do pokoju zapewnianego przez SocketIO, należy użyć funkcji `join_room()`, analogicznie rozłącza się przez `leave_room()`. Dołącz poniższy fragment kodu w miejsce komentarza.
```
join_room(room_id)
if nickname not in rooms[room_id]["users"]:
    rooms[room_id]["users"].append(nickname)
```

Domykając kwestię indywidualnych nicków - skorzystaj z poniższej funkcji do walidacji w endpoincie odpowiedzialnym za stronę główną.
```
def is_nickname_unique(nickname):
    if not connected_users:
        return True
    
    for sid in connected_users:
        temp_name = connected_users[sid]['nickname']
        if nickname == temp_name:
            return False
        
    return True
```

---
Przejdźmy teraz do mechanizmu wysyłania wiadomości.

```
const sendMessage = () => {
    const message = document.getElementById("message");
    if (message.value == "") return;
    socketio.emit("message", {msg: message.value});
    message.value = "";
};
```
Powyższy fragment, przy wywołaniu funkcji powoduje przesłanie naszej wiadomości (tekstu znajdującego się w formie) do backendu przez `socketio.emit()`. **Nie zapomnij dodać atrybut onclick do guzika**. Aby ją odebrać, tworzymy kolejny "specjalny" endpoint w naszym backendzie, zgodny z nazwą pierwszego argumentu metody `emit()`.
```
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
```
Oprócz dołączenia wiadomości do listy w słowniku `rooms`, używając funkcji `send()` z powrotem wysyłamy wiadomość do frontendu, ale nie tylko tego klienta, który ją wysłał, lecz do wszystkich znajdujących się w danym pokoju. Używając funkcji `send()`, możemy ją przechwycić po stronie klienta używając `socketio.on()`, analogicznie jak było to w przypadku eventu "connect", jednak w tym przypadku stosując argument "message".

**Przechwyć wiadomość po stronie klienta, po czym skorzystaj z poniższej funkcji, aby wyświetlić w czacie nowe wiadomości.**
```
const createChatMessage = (nickname, message, date) => {
    const messages = document.getElementById("room-messages")
    const content = `
    <div class="d-flex justify-content-between mx-4">
        <div class="p-2">
            <p class="fw-bold text-nowrap">${nickname}&nbsp;:</p>
        </div>
        <div class="p-2 flex-grow-1" style="max-width: 65%;">
            <p class="text-wrap">${message}</p>
        </div>
        <div class="p-2 ml-auto" style="width: 160px;">
            <p class="fw-light text-nowrap">${date}</p>
        </div>
    </div>
    `;
    messages.innerHTML += content;
};
```
Aktualnie, korzystając z dwóch kart przeglądarki, możesz zobaczyć jak wiadomości w czacie aktualizują się na żywo.

---
Użyteczną funkcją SocketIO jest tworzenie swoich eventów. Po stronie backendu można to osiągnąć używając funkcji `emit()`. Wklej poniższy skrawek kodu do funkcji obsługującej endpoint odpowiedzialny za dołączenie nowego użytkownika (connect).
```
join_announcement = {
        "nickname": nickname,
        "message": "has entered the room",
        "date": datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    }
emit("new_user_announcement", join_announcement, to=room_id)
```
Z kolei ten skrawek przejmuje event o konkretnej nazwie i wyświetla stosowny komunikat.
```
const createInfoMessage = (nickname, message, date) => {
    const messages = document.getElementById("room-messages")
    const content = `
    <p class="text-muted fst-italic text-center">
        <strong>${nickname}</strong> ${message} ${date}
    </p>
    `;
    messages.innerHTML += content;
};

socketio.on("new_user_announcement", data => {
    createInfoMessage(data.nickname, data.message, data.date)    
});
```
**Aktualnie nowi użytkownicy wchodzący do pokoju nie są w stanie zobaczyć wcześniej wysłanych wiadomości. Żeby to naprawić, używając funkcji `emit()` w backendowym endpoincie odpowiedzialnym za event dołączenia użytkownika, wyślij konkretnemu użytkownikowi `request.sid` wszystkie poprzednie wiadomości, które pojawiły do tego czasu w tym pokoju, oraz wyświetl je w oknie czatu.**

---
**Ostatnim Twoim zadaniem będzie implementacja mechanizmu wychodzenia z pokoju. W funkcji aktywowanej guzikiem _Disconnect_ użyj: `socketio.disconnect();` oraz `location = "../";`, żeby po rozłączeniu wrócić do strony głównej. W backendzie przejmij event `disconnect` domyślnie wysyłany przez SocketIO, opuść pokój, usuń użytkownika z `connected_users` i `rooms`. Wyślij komunikat o rozłączeniu użytkownika do pozostałych osób w pokoju. Jeżeli wszystkie osoby opuściły pokój,usuń go.**

