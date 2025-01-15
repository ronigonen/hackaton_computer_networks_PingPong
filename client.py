import socket
import threading
import struct
import time
import sys

# Configuration Constants
MAGIC_COOKIE = 0xabcddcba
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4
UDP_PAYLOAD_SIZE = 1024
UDP_TIMEOUT = 1  # Timeout in seconds for receiving UDP packets
BROADCAST_PORT = 13117

# ANSI Colors for Logging
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

# Global Running State
RUNNING = True

# Helper Function: Print Colored Messages
def log(message, color=RESET):
    print(f"{color}{message}{RESET}")

# Function to Receive Offers from Servers
def receive_offers():
    """
    Listens for server broadcast messages offering services.
    Parses offer packets and connects to the server.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_socket.bind(("", BROADCAST_PORT))
        log("Listening for offer requests...", CYAN)

        while RUNNING:
            try:
                data, server_address = udp_socket.recvfrom(1024)
                if len(data) < 8:
                    log("[WARNING] Incomplete offer packet received.", YELLOW)
                    continue

                # Parse and validate offer packet
                magic_cookie, message_type = struct.unpack('!I B', data[:5])
                if magic_cookie != MAGIC_COOKIE or message_type != OFFER_TYPE:
                    log("[ERROR] Invalid offer packet received.", RED)
                    continue

                udp_port, tcp_port = struct.unpack('!H H', data[5:9])
                log(f"Received offer from {server_address[0]} (UDP: {udp_port}, TCP: {tcp_port}).", GREEN)
                handle_server(server_address[0], udp_port, tcp_port)
            except Exception as e:
                log(f"[ERROR] Error receiving offer: {e}", RED)

# Function to Handle a Specific Server Connection
def handle_server(server_ip, udp_port, tcp_port):
    """
    Manages interaction with a specific server, including TCP and UDP file transfers.
    """
    try:
        file_size = int(input("Enter file size in bytes: "))
        tcp_connections = int(input("Enter number of TCP connections: "))
        udp_connections = int(input("Enter number of UDP connections: "))

        threads = []
        stats = {"tcp": [], "udp": []}

        # Create threads for TCP connections
        for i in range(tcp_connections):
            t = threading.Thread(target=handle_tcp_connection, args=(server_ip, tcp_port, file_size, i + 1, stats))
            t.start()
            threads.append(t)

        # Create threads for UDP connections
        for i in range(udp_connections):
            t = threading.Thread(target=handle_udp_connection, args=(server_ip, udp_port, file_size, i + 1, stats))
            t.start()
            threads.append(t)

        # Wait for all threads to complete
        for t in threads:
            t.join()

        print_statistics(stats)
    except ValueError:
        log("[ERROR] Invalid input. Please enter valid numbers.", RED)

# Function to Print Transfer Statistics
def print_statistics(stats):
    """
    Prints detailed statistics for all file transfers.
    """
    log("\nTransfer Statistics:", CYAN)
    for conn_type, results in stats.items():
        for conn_id, result in enumerate(results, 1):
            log(f"{conn_type.upper()} #{conn_id}: {result}", CYAN)
    log("All transfers complete! Listening to offer requests again.", CYAN)

# Function to Handle a Single TCP Connection
def handle_tcp_connection(server_ip, tcp_port, file_size, conn_id, stats):
    """
    Handles a single TCP file transfer connection.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.connect((server_ip, tcp_port))
            tcp_socket.sendall(f"{file_size}\n".encode("utf-8"))
            log(f"TCP request sent for transfer #{conn_id}.", GREEN)

            start_time = time.time()
            total_received = 0

            while total_received < file_size:
                data = tcp_socket.recv(1024)
                if not data:
                    break
                total_received += len(data)

            elapsed_time = time.time() - start_time
            speed = total_received / max(elapsed_time, 1e-6)
            stats["tcp"].append(f"Time: {elapsed_time:.2f}s, Speed: {speed:.2f} bytes/sec")
            log(f"TCP transfer #{conn_id} completed.", CYAN)
    except Exception as e:
        log(f"[ERROR] TCP connection error #{conn_id}: {e}", RED)

# Function to Handle a Single UDP Connection
def handle_udp_connection(server_ip, udp_port, file_size, conn_id, stats):
    """
    Handles a single UDP file transfer connection.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.settimeout(UDP_TIMEOUT)
            request = struct.pack("!I B Q", MAGIC_COOKIE, REQUEST_TYPE, file_size)
            udp_socket.sendto(request, (server_ip, udp_port))
            log(f"UDP request sent for transfer #{conn_id}.", GREEN)

            start_time = time.time()
            total_received = 0
            received_segments = set()
            total_segments = 0

            while True:
                try:
                    data, _ = udp_socket.recvfrom(UDP_PAYLOAD_SIZE)
                    if len(data) < 21:
                        continue

                    # Parse and validate packet
                    magic_cookie, message_type, total_segments, current_segment = struct.unpack("!I B Q Q", data[:21])
                    if magic_cookie != MAGIC_COOKIE or message_type != PAYLOAD_TYPE:
                        continue

                    received_segments.add(current_segment)
                    total_received += len(data) - 21

                except socket.timeout:
                    break

            elapsed_time = time.time() - start_time
            speed = total_received / max(elapsed_time, 1e-6)
            packet_loss = 100 - (len(received_segments) / total_segments * 100 if total_segments > 0 else 0)
            stats["udp"].append(f"Time: {elapsed_time:.2f}s, Speed: {speed:.2f} bytes/sec, Loss: {packet_loss:.2f}%")
            log(f"UDP transfer #{conn_id} completed.", CYAN)
    except Exception as e:
        log(f"[ERROR] UDP connection error #{conn_id}: {e}", RED)

# Main Function
def main():
    """
    Entry point for the client application.
    """
    global RUNNING
    try:
        receive_offers()
    except KeyboardInterrupt:
        RUNNING = False
        log("Client shutting down.", YELLOW)

if __name__ == "__main__":
    main()