# client.py
import socket
import struct
import threading
import time
from datetime import datetime

# ANSI colors
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def listen_for_offers():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock.bind(('', 54321))
        print(f"{Colors.OKCYAN}Listening for server offers...{Colors.ENDC}")

        while True:
            data, server_address = sock.recvfrom(1024)
            cookie, msg_type, udp_port, tcp_port = struct.unpack('!IBHH', data)

            if cookie != 0xabcddcba or msg_type != 0x2:
                print(f"{Colors.FAIL}Invalid offer message from {server_address}{Colors.ENDC}")
                continue

            print(f"{Colors.OKGREEN}Received offer from {server_address[0]}, UDP port: {udp_port}, TCP port: {tcp_port}{Colors.ENDC}")
            return server_address[0], udp_port, tcp_port

def perform_tcp_transfer(server_ip, tcp_port, file_size):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((server_ip, tcp_port))
        sock.sendall(f"{file_size}\n".encode())

        start_time = time.time()
        data = sock.recv(file_size)
        end_time = time.time()

        total_time = end_time - start_time
        speed = file_size * 8 / total_time
        print(f"{Colors.OKGREEN}TCP transfer finished. Time: {total_time:.2f}s, Speed: {speed:.2f} bps{Colors.ENDC}")

def perform_udp_transfer(server_ip, udp_port, file_size):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        request = struct.pack('!IBQ', 0xabcddcba, 0x3, file_size)
        sock.sendto(request, (server_ip, udp_port))

        start_time = datetime.now()
        received_data = 0
        expected_segments = 0
        lost_packets = 0

        while True:
            try:
                sock.settimeout(1)
                data, _ = sock.recvfrom(2048)
                cookie, msg_type, total_segments, segment_number = struct.unpack('!IBQQ', data[:20])

                if cookie != 0xabcddcba or msg_type != 0x4:
                    continue

                received_data += len(data) - 20
                expected_segments = total_segments
            except socket.timeout:
                break

        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        lost_packets = (expected_segments - received_data // 1024) if expected_segments else 0
        success_rate = 100 * (1 - lost_packets / expected_segments) if expected_segments else 100
        speed = received_data * 8 / total_time if total_time > 0 else 0

        print(f"{Colors.OKGREEN}UDP transfer finished. Time: {total_time:.2f}s, Speed: {speed:.2f} bps, Success rate: {success_rate:.2f}%{Colors.ENDC}")

if __name__ == '__main__':
    server_ip, udp_port, tcp_port = listen_for_offers()
    file_size = int(input(f"{Colors.OKBLUE}Enter file size in bytes: {Colors.ENDC}"))

    tcp_thread = threading.Thread(target=perform_tcp_transfer, args=(server_ip, tcp_port, file_size))
    udp_thread = threading.Thread(target=perform_udp_transfer, args=(server_ip, udp_port, file_size))

    tcp_thread.start()
    udp_thread.start()

    tcp_thread.join()
    udp_thread.join()

    print(f"{Colors.OKCYAN}All transfers complete.{Colors.ENDC}")
