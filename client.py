import socket
import threading
import os
import sys

HOST = '127.0.0.1'
PORT = 8080
HEADER_SIZE = 128
CLIENT_DIR = 'client_data'

os.makedirs(CLIENT_DIR, exist_ok=True)

def create_header(command, arg1="", arg2=""):
    return f"{command}|{arg1}|{arg2}".ljust(HEADER_SIZE).encode()

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
                filename, filesize = parts[1], int(parts[2])
                filepath = os.path.join(CLIENT_DIR, filename)
                
                print(f"\n[Downloading] {filename} ({filesize} bytes)...")
                with open(filepath, 'wb') as f:
                    bytes_received = 0
                    while bytes_received < filesize:
                        chunk = sock.recv(min(4096, filesize - bytes_received))
                        if not chunk: break
                        f.write(chunk)
                        bytes_received += len(chunk)
                print(f"[Success] Saved to {filepath}")

        except Exception:
            break

def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((HOST, PORT))
    except ConnectionRefusedError:
        print("Server is not running.")
        sys.exit()

    threading.Thread(target=receive_messages, args=(client,), daemon=True).start()
    print("Commands: /list, /upload <file>, /download <file>, or just type to chat.")
    
    while True:
        try:
            msg = input()
            if not msg: continue

            if msg == '/list':
                client.sendall(create_header("LIST"))
            elif msg.startswith('/upload '):
                filename = msg.split(' ', 1)[1]
                filepath = os.path.join(CLIENT_DIR, filename)
                if not os.path.exists(filepath):
                    print(f"File not found: {filepath}")
                    continue
                filesize = os.path.getsize(filepath)
                client.sendall(create_header("UPLOAD", filename, str(filesize)))
                with open(filepath, 'rb') as f:
                    while (chunk := f.read(4096)): client.sendall(chunk)
                print("Upload complete.")
            elif msg.startswith('/download '):
                client.sendall(create_header("DOWNLOAD", msg.split(' ', 1)[1]))
            else:
                client.sendall(create_header("MSG", msg))
        except KeyboardInterrupt:
            client.close()
            break

if __name__ == "__main__":
    main()