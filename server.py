import socket
import threading
import struct
import time
import random

# Configuration Constants
MAGIC_COOKIE = 0xabcddcba
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4
UDP_PAYLOAD_SIZE = 1024
UDP_ANNOUNCE_INTERVAL = 1  # Broadcast interval in seconds
UDP_PORT = 13117
TCP_PORT = 5001  # Default TCP port

# ANSI Colors for Logging
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

# Helper Function: Print Colored Messages
def log(message, color=RESET):
    print(f"{color}{message}{RESET}")

# Function to Send UDP Broadcast Offers
def send_offers():
    """
    Broadcasts UDP offers to potential clients at regular intervals.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            try:
                message = struct.pack("!I B H H", MAGIC_COOKIE, OFFER_TYPE, UDP_PORT, TCP_PORT)
                udp_socket.sendto(message, ("<broadcast>", UDP_PORT))
                log("Offer broadcast sent.", CYAN)
                time.sleep(UDP_ANNOUNCE_INTERVAL)
            except Exception as e:
                log(f"[ERROR] Failed to send offer broadcast: {e}", RED)

# Function to Handle a Single TCP Connection
def handle_tcp_connection(client_socket, address):
    """
    Handles a single TCP client connection for file transfer.
    """
    try:
        log(f"TCP connection established with {address}.", GREEN)
        request = client_socket.recv(1024).decode("utf-8").strip()
        file_size = int(request)
        log(f"TCP request received for file size: {file_size} bytes.", CYAN)

        start_time = time.time()
        client_socket.sendall(b"0" * file_size)
        elapsed_time = time.time() - start_time
        speed = file_size / max(elapsed_time, 1e-6)

        log(
            f"Sent {file_size} bytes over TCP to {address} in {elapsed_time:.2f}s ({speed:.2f} bytes/sec).",
            CYAN,
        )
    except Exception as e:
        log(f"[ERROR] TCP handling error: {e}", RED)
    finally:
        client_socket.close()

# Function to Handle UDP Requests
def handle_udp_connection(udp_socket):
    """
    Handles incoming UDP requests and responds with file segments.
    """
    while True:
        try:
            data, client_address = udp_socket.recvfrom(1024)
            if len(data) < 13:
                continue

            # Parse and validate the UDP request
            magic_cookie, message_type, file_size = struct.unpack("!I B Q", data[:13])
            if magic_cookie != MAGIC_COOKIE or message_type != REQUEST_TYPE:
                log(f"[ERROR] Invalid UDP request from {client_address}.", RED)
                continue

            log(
                f"Valid UDP request from {client_address} for file size: {file_size} bytes.", GREEN
            )

            total_segments = file_size // UDP_PAYLOAD_SIZE + (file_size % UDP_PAYLOAD_SIZE > 0)
            start_time = time.time()

            for segment in range(total_segments):
                payload = struct.pack(
                    "!I B Q Q", MAGIC_COOKIE, PAYLOAD_TYPE, total_segments, segment
                )
                udp_socket.sendto(
                    payload + b"0" * (UDP_PAYLOAD_SIZE - len(payload)), client_address
                )

            elapsed_time = time.time() - start_time
            total_bytes_sent = file_size
            speed = total_bytes_sent / max(elapsed_time, 1e-6)

            log(
                f"Sent {total_segments} segments ({total_bytes_sent} bytes) to {client_address} in {elapsed_time:.2f}s ({speed:.2f} bytes/sec).",
                CYAN,
            )
        except Exception as e:
            log(f"[ERROR] UDP handling error: {e}", RED)

# Main Server Function
def main():
    """
    Entry point for the server application.
    """
    log(
        f"Server started, listening on UDP port {UDP_PORT} and TCP port {TCP_PORT}.", CYAN
    )

    # Start UDP offer broadcast thread
    threading.Thread(target=send_offers, daemon=True).start()

    # Start UDP server
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_socket.bind(("", UDP_PORT))
        threading.Thread(target=handle_udp_connection, args=(udp_socket,), daemon=True).start()

        # Start TCP server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tcp_socket.bind(("", TCP_PORT))
            tcp_socket.listen()

            while True:
                try:
                    client_socket, address = tcp_socket.accept()
                    threading.Thread(
                        target=handle_tcp_connection, args=(client_socket, address), daemon=True
                    ).start()
                except Exception as e:
                    log(f"[ERROR] Error accepting TCP connection: {e}", RED)

if __name__ == "__main__":
    main()