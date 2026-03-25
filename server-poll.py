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
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setblocking(0)
    server.bind((HOST, PORT))
    server.listen()

    poller = select.poll()
    poller.register(server.fileno(), select.POLLIN)

    # Dictionaries to map the OS integer (fd) back to our Python objects
    fd_to_socket = {server.fileno(): server}
    clients_data = {}

    print(f"[POLL] Listening on {HOST}:{PORT}")

    while True:
        events = poller.poll()

        for fd, event in events:
            sock = fd_to_socket[fd]

            if event & (select.POLLHUP | select.POLLERR):
                disconnect(fd, poller, fd_to_socket, clients_data)
                continue

            if event & select.POLLIN:
                if sock is server:
                    conn, addr = server.accept()
                    conn.setblocking(0)
                    poller.register(conn.fileno(), select.POLLIN)
                    fd_to_socket[conn.fileno()] = conn
                    clients_data[conn.fileno()] = {'buffer': b'', 'file_info': None}
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

if __name__ == "__main__":
    main()