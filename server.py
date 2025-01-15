# server.py
import socket
import struct
import threading
import time

# ANSI colors
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def send_offers(udp_port, tcp_port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        offer_message = struct.pack('!IBHH', 0xabcddcba, 0x2, udp_port, tcp_port)

        while True:
            sock.sendto(offer_message, ('<broadcast>', 13117))  # Fixed broadcast port
            print(f"{Colors.OKCYAN}Offer sent to UDP port 13117{Colors.ENDC}")
            time.sleep(1)

def handle_tcp_client(connection, address):
    try:
        print(f"{Colors.OKGREEN}TCP connection established with {address}{Colors.ENDC}")
        file_size = int(connection.recv(1024).decode().strip())
        print(f"{Colors.OKBLUE}Requested file size: {file_size} bytes{Colors.ENDC}")

        # Send the requested file size worth of data
        data = b'0' * file_size
        connection.sendall(data)
        print(f"{Colors.OKGREEN}File sent to {address}{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}Error handling TCP client: {e}{Colors.ENDC}")
    finally:
        connection.close()

def handle_udp_client(udp_port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(('', udp_port))
        print(f"{Colors.OKCYAN}Listening for UDP requests on port {udp_port}{Colors.ENDC}")

        while True:
            try:
                request, client_address = sock.recvfrom(1024)
                cookie, msg_type, file_size = struct.unpack('!IBQ', request)

                if cookie != 0xabcddcba or msg_type != 0x3:
                    print(f"{Colors.FAIL}Invalid UDP request from {client_address}{Colors.ENDC}")
                    continue

                print(f"{Colors.OKGREEN}Valid UDP request from {client_address}, file size: {file_size} bytes{Colors.ENDC}")

                segment_count = (file_size // 1024) + (1 if file_size % 1024 != 0 else 0)
                for i in range(segment_count):
                    payload = struct.pack('!IBQQ', 0xabcddcba, 0x4, segment_count, i) + b'0' * min(1024, file_size - i * 1024)
                    sock.sendto(payload, client_address)
                    time.sleep(0.01)  # Small delay to avoid busy-waiting
            except Exception as e:
                print(f"{Colors.FAIL}Error handling UDP client: {e}{Colors.ENDC}")

if __name__ == '__main__':
    TCP_PORT = 12345
    UDP_PORT = 54321

    print(f"{Colors.HEADER}Server starting...{Colors.ENDC}")
    print(f"{Colors.OKCYAN}Listening on UDP port {UDP_PORT} and TCP port {TCP_PORT}{Colors.ENDC}")

    threading.Thread(target=send_offers, args=(UDP_PORT, TCP_PORT), daemon=True).start()
    threading.Thread(target=handle_udp_client, args=(UDP_PORT,), daemon=True).start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.bind(('', TCP_PORT))
        tcp_socket.listen()

        while True:
            conn, addr = tcp_socket.accept()
            threading.Thread(target=handle_tcp_client, args=(conn, addr), daemon=True).start()
