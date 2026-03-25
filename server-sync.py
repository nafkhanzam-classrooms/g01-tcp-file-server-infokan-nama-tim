import socket
import os

HOST = '127.0.0.1'
PORT = 8080
HEADER_SIZE = 128
SERVER_DIR = 'server_data'

os.makedirs(SERVER_DIR, exist_ok=True)

def create_header(command, arg1="", arg2=""):
    return f"{command}|{arg1}|{arg2}".ljust(HEADER_SIZE).encode()

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

if __name__ == "__main__":
    main()