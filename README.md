[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/mRmkZGKe)
# Network Programming - Assignment G01

## Anggota Kelompok
| Nama           | NRP        | Kelas     |
| ---            | ---        | ----------|
|Rendy Tanuwijaya|5025241099|D|

## Link Youtube (Unlisted)
Link ditaruh di bawah ini
```
https://youtu.be/79xwhK8xgEs
```

## Penjelasan Program

Setiap kode di bawah ini akan berpacu kepada header, dan ini adalah fungsi header yang digunakan untuk semuanya
```
def create_header(command, arg1="", arg2=""):
    return f"{command}|{arg1}|{arg2}".ljust(HEADER_SIZE).encode()
```

Ini juga merupakan konstanta yang digunakan untuk semua kode di bawahnya.
CLIENT_DIR dan SERVER_DIR untuk direktori mana
PORT konstan 8080 untuk semua server
HOST adalah localhost 127.0.0.1
HEADER_SIZE selalu sama dengan max 128 bytes
```
HOST = '127.0.0.1'
PORT = 8080
HEADER_SIZE = 128
CLIENT_DIR = 'client_data'
SERVER_DIR = 'server_data'
```

Client.py

Kode di bawah ini merupakan kode socket programming buat connect dari client ke server
```
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((HOST, PORT))
    except ConnectionRefusedError:
        print("Server is not running.")
        sys.exit()
```

Selanjutnya di client ada penggunaan multithreading, thread satu untuk mendapatkan respon apapun dari server
fungsi receive_messages akan mengubah header menjadi command dan data atribut dari file (untuk download) atau pesan dari server (MSG/RES)
```
    threading.Thread(target=receive_messages, args=(client,), daemon=True).start()


def receive_messages(sock):
    while True:
        try:
            header = sock.recv(HEADER_SIZE).decode().strip()
            if not header:
                print("\n[Disconnected from server]")
                break
            
            parts = header.split('|')
            command = parts[0]

            if command == "MSG" or command == "RES":
                print(f"\n{parts[1]}")
            
            elif command == "FILE":
                filename, filesize = parts[1], int(parts[2]) # Mendapatkan filename dan filesize
                filepath = os.path.join(CLIENT_DIR, filename) # Mendapatkan absolute path ke file
                
                print(f"\n[Downloading] {filename} ({filesize} bytes)...")
                with open(filepath, 'wb') as f: # Untuk mendownload file dengan filepath dan receive
                    bytes_received = 0
                    while bytes_received < filesize:
                        chunk = sock.recv(min(4096, filesize - bytes_received))
                        if not chunk: break
                        f.write(chunk)
                        bytes_received += len(chunk)
                print(f"[Success] Saved to {filepath}")

        except Exception:
            break
```


Thread 2 untuk mendapatkan user input dan mengirim ke server
```
        try:
            msg = input()
            if not msg: continue
                
            if msg == '/list': # Untuk setiap tipe command akan ada "Fungsi"-nya sendiri
                client.sendall(create_header("LIST"))
            elif msg.startswith('/upload '):
                filename = msg.split(' ', 1)[1]
                filepath = os.path.join(CLIENT_DIR, filename)
                if not os.path.exists(filepath):
                    print(f"File not found: {filepath}")
                    continue
                filesize = os.path.getsize(filepath)
                client.sendall(create_header("UPLOAD", filename, str(filesize))) # Mengirim header upload ke server beserta nama file dan besar filenya
                with open(filepath, 'rb') as f:
                    while (chunk := f.read(4096)): client.sendall(chunk)
                print("Upload complete.")
            elif msg.startswith('/download '):
                client.sendall(create_header("DOWNLOAD", msg.split(' ', 1)[1])) # Request untuk download dengan nama filenya
            else:
                client.sendall(create_header("MSG", msg)) # Untuk message apapun yang tersisa akan dianggap message text
        except KeyboardInterrupt: # untuk ctrl+c akan close connection
            client.close()
            break
```

server-thread.py

Kode di bawah adalah aktivasi server dengan listen untuk client dan menambahkan thread untuk setiap client yang ada
```
def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[THREAD] Listening on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
```

server-thread memiliki arsitektur yang hampir mirip dengan client tetapi bedanya setiap client memiliki channel sendiri dalam bentuk thread pada server
Bagian di bawah ini hampir sama dengan client.py
```
def handle_client(conn, addr):
    clients.append(conn)
    while True:
        try:
            header = conn.recv(HEADER_SIZE).decode().strip()
            if not header: break
            
            parts = header.split('|')
            command = parts[0]

            if command == "MSG":
                broadcast(create_header("MSG", f"[User-{addr[1]}]: {parts[1]}"), conn)
            elif command == "LIST":
                files = ", ".join(os.listdir(SERVER_DIR)) or "No files."
                conn.sendall(create_header("RES", f"[Server]: {files}"))
            elif command == "UPLOAD":
                filename, filesize = parts[1], int(parts[2])
                with open(os.path.join(SERVER_DIR, filename), 'wb') as f:
                    bytes_received = 0
                    while bytes_received < filesize:
                        chunk = conn.recv(min(4096, filesize - bytes_received))
                        if not chunk: break
                        f.write(chunk)
                        bytes_received += len(chunk)
                broadcast(create_header("MSG", f"[Server]: User-{addr[1]} uploaded {filename}"), conn)
            elif command == "DOWNLOAD":
                filepath = os.path.join(SERVER_DIR, parts[1])
                if os.path.exists(filepath):
                    conn.sendall(create_header("FILE", parts[1], str(os.path.getsize(filepath))))
                    with open(filepath, 'rb') as f:
                        while (chunk := f.read(4096)): conn.sendall(chunk)
                else:
                    conn.sendall(create_header("RES", "[Server]: File not found."))
        except Exception:
            break
    
    if conn in clients: clients.remove(conn)
    conn.close()
```

Fungsi broadcast untuk mengirim ke semua client kecuali sender sendiri
```
def broadcast(header, sender):
    for c in clients:
        if c != sender:
            try: c.sendall(header)
            except: pass

```

server-sync.py
server ini adalah client yang diubah agar dapat menampung file dan merespon. Inti dari arsitekturnya adalah client
```
def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SYNC] Listening on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        print(f"[NEW CONNECTION] {addr} connected. Others are blocked.")
        
        while True:
            try:
                header = conn.recv(HEADER_SIZE).decode().strip()
                if not header: break 
                
                parts = header.split('|')
                command = parts[0]

                if command == "MSG":
                    conn.sendall(create_header("MSG", f"[Server Echo]: {parts[1]}"))
                elif command == "LIST":
                    files = ", ".join(os.listdir(SERVER_DIR)) or "No files."
                    conn.sendall(create_header("RES", f"[Server]: {files}"))
                elif command == "UPLOAD":
                    filename, filesize = parts[1], int(parts[2])
                    with open(os.path.join(SERVER_DIR, filename), 'wb') as f:
                        bytes_received = 0
                        while bytes_received < filesize:
                            chunk = conn.recv(min(4096, filesize - bytes_received))
                            if not chunk: break
                            f.write(chunk)
                            bytes_received += len(chunk)
                    conn.sendall(create_header("RES", "[Server]: Upload complete."))
                elif command == "DOWNLOAD":
                    filepath = os.path.join(SERVER_DIR, parts[1])
                    if os.path.exists(filepath):
                        conn.sendall(create_header("FILE", parts[1], str(os.path.getsize(filepath))))
                        with open(filepath, 'rb') as f:
                            while (chunk := f.read(4096)): conn.sendall(chunk)
                    else:
                        conn.sendall(create_header("RES", "[Server]: File not found."))
            except ConnectionResetError:
                break
        print(f"[DISCONNECT] {addr} left. Ready for a new client.")
        conn.close()
```


Server-select.py
Server ini memiliki arsitektur yang berbeda dengan client, server ini dapat memiliki koneksi kepada banyak client dengan mengiterasi pada setiap client dengan membuat array untuk setiap koneksi ke client
```
def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setblocking(0)
    server.bind((HOST, PORT))
    server.listen()

    inputs = [server]
    clients_data = {} # Tracks the buffer for each socket

    print(f"[SELECT] Listening on {HOST}:{PORT}")

    while inputs:
        readable, _, exceptional = select.select(inputs, [], inputs) # Kode ini untuk menunggu ada input dari client manapun dan exceptional bila ada masalah apapun akan ke kirim ke exceptional

        for s in exceptional: # Disconnect client yang mungkin bermaslaah
            disconnect(s, inputs, clients_data)
```

Kode untuk ada input dan server menemukan ada client baru yang dapat connect.
```
        for s in readable:
            if s is server:
                conn, addr = s.accept()
                conn.setblocking(0)
                inputs.append(conn)
                clients_data[conn] = {'buffer': b'', 'file_info': None} #memberikan informasi kalau client sedang tidak idle
```

Kode di bawah untuk client yang memberikan input
```
            else:
                try:
                    data = s.recv(4096)
                    if data:
                        state = clients_data[s]
                        state['buffer'] += data

                        # If we aren't currently receiving a file, look for a header
                        if not state['file_info']: # Kalau client lagi idle
                            if len(state['buffer']) >= HEADER_SIZE:  # Kalau request dari client tidak memenuhi header_size maka diabaikan
                                header_bytes = state['buffer'][:HEADER_SIZE]
                                state['buffer'] = state['buffer'][HEADER_SIZE:] # Data yang didapat dipisah menjadi header dan data murni
                                
                                parts = header_bytes.decode().strip().split('|')
                                command = parts[0]
            
                                if command == "MSG": # Kode untuk setiap command seperti sebelumnya
                                    msg = create_header("MSG", f"[User]: {parts[1]}")
                                    for c in inputs:
                                        if c is not server and c is not s: c.sendall(msg)
                                elif command == "LIST":
                                    files = ", ".join(os.listdir(SERVER_DIR)) or "No files."
                                    s.sendall(create_header("RES", f"[Server]: {files}"))
                                elif command == "UPLOAD":
                                    state['file_info'] = {
                                        'name': parts[1], # Nama filenya
                                        'size': int(parts[2]), # Besar filenya
                                        'recv': 0, # Bytes yang diterima
                                        'file': open(os.path.join(SERVER_DIR, parts[1]), 'wb') # Pointer ke filenya
                                    }
                                    # Process any file data already caught in the buffer
                                    process_upload_buffer(s, clients_data)
                                elif command == "DOWNLOAD":
                                    filepath = os.path.join(SERVER_DIR, parts[1])
                                    if os.path.exists(filepath):
                                        s.sendall(create_header("FILE", parts[1], str(os.path.getsize(filepath))))
                                        with open(filepath, 'rb') as f:
                                            while (chunk := f.read(4096)): s.sendall(chunk)
                                    else:
                                        s.sendall(create_header("RES", "[Server]: File not found."))
                        
                        # If we ARE receiving a file, dump buffer into the file
                        else:
                            process_upload_buffer(s, clients_data)
                    else: # Failsafe
                        disconnect(s, inputs, clients_data)
                except ConnectionResetError: # Failsafe
                    disconnect(s, inputs, clients_data)
```

untuk menerima data yang ada di buffer
```
def process_upload_buffer(s, clients_data):
    state = clients_data[s]
    info = state['file_info']
    if state['buffer']:
        needed = info['size'] - info['recv'] # Data yang masih diperlukan
        chunk = state['buffer'][:needed] # Datanya
        info['file'].write(chunk) # Filenya ditambahkan bagian data yang baru diterima
        info['recv'] += len(chunk) # Total data yang didapatkan bertambah
        state['buffer'] = state['buffer'][len(chunk):] # Buffer berkurang dari chunk yang sudah diproses

        if info['recv'] >= info['size']: # Kalau data transfer sudah selesai maka upload dihentikan
            info['file'].close()
            state['file_info'] = None
            s.sendall(create_header("RES", f"[Server]: Upload complete."))

```

Fungsi untuk disconnect client
```
def disconnect(s, inputs, clients_data):
    if s in inputs: inputs.remove(s)
    if s in clients_data:
        if clients_data[s]['file_info']: clients_data[s]['file_info']['file'].close()
        del clients_data[s]
    s.close()
```

Server-poll.py
Arsitektur server ini merujuk kepada server-select yang dioptimisiasi dengan mengiterasi ke client yang memberikan input daripada ke semua client menggunakan fungsi built-in OS, Poll.
```
def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setblocking(0)
    server.bind((HOST, PORT))
    server.listen()

    poller = select.poll()
    poller.register(server.fileno(), select.POLLIN) # inisialasasi poll

    # Dictionaries to map the OS integer (fd) back to our Python objects
    fd_to_socket = {server.fileno(): server}
    clients_data = {}

    print(f"[POLL] Listening on {HOST}:{PORT}")
```

Menggunakan Poll untuk menunggu adanya aktifitas dari client
```
      events = poller.poll() # Menunggu event dari poll

        for fd, event in events:
            sock = fd_to_socket[fd] # Sock didapatkan dari file descriptor untuk menjadi file pointer

            if event & (select.POLLHUP | select.POLLERR): # Cek untuk poll memberi event yang bermasalah, maka akan di disconnect
                disconnect(fd, poller, fd_to_socket, clients_data)
                continue

            if event & select.POLLIN:
                if sock is server: # Server yang meiliki event berarti ada client yang bisa di accept
                    conn, addr = server.accept()
                    conn.setblocking(0)
                    poller.register(conn.fileno(), select.POLLIN)
                    fd_to_socket[conn.fileno()] = conn
                    clients_data[conn.fileno()] = {'buffer': b'', 'file_info': None}
```

Selanjutnya memiliki kode yang sama dan penjelasan yang sama dengan server-select.py
```
                else:
                    try:
                        data = sock.recv(4096)
                        if data:
                            state = clients_data[fd]
                            state['buffer'] += data

                            if not state['file_info']:
                                if len(state['buffer']) >= HEADER_SIZE:
                                    header_bytes = state['buffer'][:HEADER_SIZE]
                                    state['buffer'] = state['buffer'][HEADER_SIZE:]
                                    
                                    parts = header_bytes.decode().strip().split('|')
                                    command = parts[0]

                                    if command == "MSG":
                                        msg = create_header("MSG", f"[User]: {parts[1]}")
                                        for c_fd, c_sock in fd_to_socket.items():
                                            if c_sock is not server and c_fd != fd:
                                                c_sock.sendall(msg)
                                    elif command == "LIST":
                                        files = ", ".join(os.listdir(SERVER_DIR)) or "No files."
                                        sock.sendall(create_header("RES", f"[Server]: {files}"))
                                    elif command == "UPLOAD":
                                        state['file_info'] = {
                                            'name': parts[1],
                                            'size': int(parts[2]),
                                            'recv': 0,
                                            'file': open(os.path.join(SERVER_DIR, parts[1]), 'wb')
                                        }
                                        process_upload_buffer(fd, sock, clients_data)
                                    elif command == "DOWNLOAD":
                                        filepath = os.path.join(SERVER_DIR, parts[1])
                                        if os.path.exists(filepath):
                                            sock.sendall(create_header("FILE", parts[1], str(os.path.getsize(filepath))))
                                            with open(filepath, 'rb') as f:
                                                while (chunk := f.read(4096)): sock.sendall(chunk)
                                        else:
                                            sock.sendall(create_header("RES", "[Server]: File not found."))
                            else:
                                process_upload_buffer(fd, sock, clients_data)
                        else:
                            disconnect(fd, poller, fd_to_socket, clients_data)
                    except ConnectionResetError:
                        disconnect(fd, poller, fd_to_socket, clients_data)

def process_upload_buffer(fd, sock, clients_data):
    state = clients_data[fd]
    info = state['file_info']
    if state['buffer']:
        needed = info['size'] - info['recv']
        chunk = state['buffer'][:needed]
        info['file'].write(chunk)
        info['recv'] += len(chunk)
        state['buffer'] = state['buffer'][len(chunk):]

        if info['recv'] >= info['size']:
            info['file'].close()
            state['file_info'] = None
            sock.sendall(create_header("RES", f"[Server]: Upload complete."))

def disconnect(fd, poller, fd_to_socket, clients_data):
    poller.unregister(fd)
    sock = fd_to_socket.pop(fd)
    if fd in clients_data:
        if clients_data[fd]['file_info']: clients_data[fd]['file_info']['file'].close()
        del clients_data[fd]
    sock.close()
```


## Screenshot Hasil

<img width="1709" height="766" alt="image" src="https://github.com/user-attachments/assets/af435853-83cf-4781-9c24-750c996e2098" />

<img width="1903" height="994" alt="image" src="https://github.com/user-attachments/assets/87ddf3c1-a9bd-4b13-968d-a5c0530aaf1a" />



<img width="1917" height="996" alt="image" src="https://github.com/user-attachments/assets/707fc0e3-7f2c-4f47-9fe8-e4722ce9a1d8" />


<img width="1916" height="1001" alt="image" src="https://github.com/user-attachments/assets/41dc60dd-d24a-4603-94be-b33602652dfe" />


<img width="1910" height="997" alt="image" src="https://github.com/user-attachments/assets/0b9c8353-b4e3-49a7-b5a7-1977526091e3" />


