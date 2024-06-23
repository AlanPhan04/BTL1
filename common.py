import socket
from enum import Enum

PIECE_SIZE = 150
CODE = 'utf-8'
"""
this function would first try to connect to a random IP address
this behavior could be successul or not, however, the function would try to
choose the appropriate interface for the connection
therefore, checking the first argument in this socket after trying to connect
the result would be the IP address of the interface that is used for the connection in the network
"""
def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

"""
    define the type of messages that could be sent
    between the server and the client or client and client
"""
class mess_type(Enum):
    HANDSHAKE = 1
    REQUEST = 2
    RESPONSE = 3
    PEER_REQUEST = 4
    PEER_RESPONSE = 5
    PEER_UPDATE_REQUEST = 6
    PEER_UPDATE_RESPONSE = 7
    SERVER_UPDATE_REQUEST = 8
    SERVER_UPDATE_RESPONSE = 9
    CLOSE = 10
    

