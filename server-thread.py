import socket
import threading
import os

HOST = '127.0.0.1'
PORT = 8080
HEADER_SIZE = 128
SERVER_DIR = 'server_data'

os.makedirs(SERVER_DIR, exist_ok=True)
clients = []

def create_header(command, arg1="", arg2=""):
    return f"{command}|{arg1}|{arg2}".ljust(HEADER_SIZE).encode()

def broadcast(header, sender):
    for c in clients:
        if c != sender:
            try: c.sendall(header)
            except: pass

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

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[THREAD] Listening on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()