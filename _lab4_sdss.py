import sys
import os
import threading
import socket
import uuid
import struct
import time
from datetime import datetime

ANSI_RESET = "\u001B[0m"
ANSI_RED = "\u001B[31m"
ANSI_GREEN = "\u001B[32m"
ANSI_YELLOW = "\u001B[33m"
ANSI_BLUE = "\u001B[34m"

_NODE_UUID = str(uuid.uuid4())[:8]


def print_yellow(msg):
    print(f"{ANSI_YELLOW}{msg}{ANSI_RESET}")


def print_blue(msg):
    print(f"{ANSI_BLUE}{msg}{ANSI_RESET}")


def print_red(msg):
    print(f"{ANSI_RED}{msg}{ANSI_RESET}")


def print_green(msg):
    print(f"{ANSI_GREEN}{msg}{ANSI_RESET}")


def get_broadcast_port():
    return 35498


def get_node_uuid():
    return _NODE_UUID


class NeighborInfo(object):
    def __init__(self, delay, broadcast_count=0, ip=None, tcp_port=None):
        # Ip and port are optional, if you want to store them.
        self.delay = delay
        self.broadcast_count = broadcast_count
        self.ip = ip
        self.tcp_port = tcp_port


##################
# YOUR     CODE  #
##################


# Don't change any variable's name.
# Use this hashmap to store the information of your neighbor nodes.
neighbor_information = {}

# Leave the server socket as global variable.
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Setup the server socket
server.bind(('', 0))
server.listen(20)

# Leave broadcaster as a global variable.
broadcaster = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Setup the UDP socket
broadcaster.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)  # Enabling reusing the port
broadcaster.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enabling broadcasting mode
broadcaster.bind(('', get_broadcast_port()))  # To listen to the broadcasting port


def send_broadcast_thread():
    # get node uuid
    node_uuid = get_node_uuid()

    # get node tcp server port number
    tcp_server_port = server.getsockname()[1]

    # creating the message
    message = '{} ON {}'.format(node_uuid, tcp_server_port)
    message = message.encode('utf-8')

    # broadcasting the message every second
    while True:
        broadcaster.sendto(message, ("255.255.255.255", get_broadcast_port()))
        time.sleep(1)


def receive_broadcast_thread():
    """
    Receive broadcasts from other nodes,
    launches a thread to connect to new nodes
    and exchange timestamps.
    """
    while True:
        # Receive and decode a message
        data, (ip, port) = broadcaster.recvfrom(4096)
        data = data.decode('utf-8').split(' ON ')

        # Ignore broadcast messages sent by me
        if data[0] == get_node_uuid():
            continue

        print_blue(f"RECV: {data} FROM: {ip}:{port}")

        # If node is not in neighbor_information create it
        if data[0] not in neighbor_information:
            neighbor_information[data[0]] = NeighborInfo(0, 0, ip, data[1])

        # If broadcast_count % 10 != 0 : update it and continue
        if neighbor_information[data[0]].broadcast_count % 10 != 0:
            neighbor_information[data[0]].broadcast_count += 1
            continue

        # Update broadcast_count and start exchange_timestamps_thread
        neighbor_information[data[0]].broadcast_count = (neighbor_information[data[0]].broadcast_count + 1) % 10
        daemon_thread_builder(exchange_timestamps_thread, (data[0], ip, data[1])).start()


def tcp_server_thread():
    """
    Accept connections from other nodes and send them
    this node's timestamp once they connect.
    """
    while True:
        neighbor_socket, neighbor_address = server.accept()

        ts = datetime.utcnow().timestamp()
        neighbor_socket.sendto(struct.pack("d", ts), neighbor_address)
        neighbor_socket.close()


def exchange_timestamps_thread(other_uuid: str, other_ip: str, other_tcp_port: int):
    """
    Open a connection to the other_ip, other_tcp_port
    and do the steps to exchange timestamps.
    Then update the neighbor_info map using other node's UUID.
    """
    temp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    temp_socket.connect((other_ip, int(other_tcp_port)))

    print_yellow(f"ATTEMPTING TO CONNECT TO {other_uuid}")

    my_ts = datetime.utcnow().timestamp()
    data = temp_socket.recv(4096)
    other_ts = struct.unpack('d', data)[0]

    delay = abs(other_ts - my_ts)

    neighbor_information[other_uuid].delay = delay

    print_green(f"{other_uuid} DELAY: {str(delay)} SEC")

    temp_socket.close()


def daemon_thread_builder(target, args=()) -> threading.Thread:
    """
    Use this function to make threads. Leave as is.
    """
    th = threading.Thread(target=target, args=args)
    th.setDaemon(True)
    return th


def entrypoint():
    # starting tcp server
    daemon_thread_builder(tcp_server_thread).start()

    # starting sending and receiving broadcast messages
    daemon_thread_builder(send_broadcast_thread).start()

    daemon_thread_builder(receive_broadcast_thread).start()

    # I think we need this here (otherwise the program will terminate and the threads gonna die)
    while True:
        pass

    pass


############################################
############################################


def main():
    """
    Leave as is.
    """
    print("*" * 50)
    print_red("To terminate this program use: CTRL+C")
    print_red("If the program blocks/throws, you have to terminate it manually.")
    print_green(f"NODE UUID: {get_node_uuid()}")
    print("*" * 50)
    time.sleep(2)  # Wait a little bit.
    entrypoint()


if __name__ == "__main__":
    main()
