import socket
import select
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
    server.setblocking(0)
    server.bind((HOST, PORT))
    server.listen()

    inputs = [server]
    clients_data = {} # Tracks the buffer for each socket

    print(f"[SELECT] Listening on {HOST}:{PORT}")

    while inputs:
        readable, _, exceptional = select.select(inputs, [], inputs)

        for s in readable:
            if s is server:
                conn, addr = s.accept()
                conn.setblocking(0)
                inputs.append(conn)
                clients_data[conn] = {'buffer': b'', 'file_info': None}
            else:
                try:
                    data = s.recv(4096)
                    if data:
                        state = clients_data[s]
                        state['buffer'] += data

                        # If we aren't currently receiving a file, look for a header
                        if not state['file_info']:
                            if len(state['buffer']) >= HEADER_SIZE:
                                header_bytes = state['buffer'][:HEADER_SIZE]
                                state['buffer'] = state['buffer'][HEADER_SIZE:]
                                
                                parts = header_bytes.decode().strip().split('|')
                                command = parts[0]

                                if command == "MSG":
                                    msg = create_header("MSG", f"[User]: {parts[1]}")
                                    for c in inputs:
                                        if c is not server and c is not s: c.sendall(msg)
                                elif command == "LIST":
                                    files = ", ".join(os.listdir(SERVER_DIR)) or "No files."
                                    s.sendall(create_header("RES", f"[Server]: {files}"))
                                elif command == "UPLOAD":
                                    state['file_info'] = {
                                        'name': parts[1],
                                        'size': int(parts[2]),
                                        'recv': 0,
                                        'file': open(os.path.join(SERVER_DIR, parts[1]), 'wb')
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
                    else:
                        disconnect(s, inputs, clients_data)
                except ConnectionResetError:
                    disconnect(s, inputs, clients_data)

        for s in exceptional:
            disconnect(s, inputs, clients_data)

def process_upload_buffer(s, clients_data):
    state = clients_data[s]
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
            s.sendall(create_header("RES", f"[Server]: Upload complete."))

def disconnect(s, inputs, clients_data):
    if s in inputs: inputs.remove(s)
    if s in clients_data:
        if clients_data[s]['file_info']: clients_data[s]['file_info']['file'].close()
        del clients_data[s]
    s.close()

if __name__ == "__main__":
    main()