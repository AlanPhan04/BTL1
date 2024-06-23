import socket
import threading
import ast
import time

import common
from common import mess_type


SERVER_PORT = 12500
SERVER_IP = common.get_ip_address()
LISTEN_DURATION = 5
RECEIVE_SIZE = 1024
CODE = 'utf-8'

class server:
    def __init__(self):
        # The address including port and ip of sever is defined
        self.port = SERVER_PORT
        self.ip = SERVER_IP
        self.id = SERVER_PORT
        
        # A flag for running state of the server
        self.running = True
        
        # A dictionary for storing the connection of each client(key) and the files they have(value)
        self.client_info = {}
        self.files = {}
        self.lock = threading.Lock()
        
        
        # A socket for listening from every one in the network is created
        self.handle_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.handle_client_socket.bind((self.ip, self.port))
        print(f"a server with IP address {self.ip}, ID {self.id} and port number {self.port} is created")
        
        # A thread for listening to client is created 
        self.listen_client_thread = threading.Thread(target=self.listen_client_channel)
        self.listen_client_thread.start()
        print("start listening....")
        
    def stop(self):
        self.running = False
        # self.listen_client_thread.join()
        
    def create_and_send_message(self, connect_socket : socket.socket, type : mess_type ,filename = {}, peers = []):
        message = ""
        if type == mess_type.HANDSHAKE or type == mess_type.SERVER_UPDATE_REQUEST or type == mess_type.SERVER_UPDATE_RESPONSE:
            message = f"type::{type.value};sid::{self.id};file::{self.files}"
        elif type == mess_type.RESPONSE:
            message = f"type::{type.value};sid::{self.id};file::{filename};peers::{peers}"
        elif type == mess_type.CLOSE:
            message = f"type::{type.value};sid::{self.id}"
        
        # print(message)
        connect_socket.send(message.encode(CODE))
    
    def parse_message(self, message):
        pairs = message.split(";")
        mess_struct = {}
        
        for pair in pairs:
            pair = pair.split("::")
            mess_struct[pair[0]] = pair[1]
            
        mess_struct['type'] = int(mess_struct['type'])
        if mess_struct['type'] == mess_type.HANDSHAKE.value or mess_struct['type'] == mess_type.REQUEST.value or mess_struct['type'] == mess_type.PEER_UPDATE_RESPONSE.value:
            mess_struct['file'] = ast.literal_eval(mess_struct['file'])
            
        print(mess_struct)
        
        return mess_struct

    # first version checked   
    def listen_client_channel(self):
        self.handle_client_socket.listen()
        print("start listening...")
        while self.running:
            # Accept any coming connection from others, 
            # this would last for 5sec if there is no client wanting to connect
            try:
                self.handle_client_socket.settimeout(LISTEN_DURATION)
                client_socket, client_addr = self.handle_client_socket.accept()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"a false in accepting the peer connect request: {e}")
            
            
            # Create a thread for each client accessing the server
            handle_speci_client = threading.Thread(target=self.handle_specific_client, args=(client_socket, client_addr))
            handle_speci_client.start()
            
        self.handle_client_socket.close()
        print("stop listening...")
    
    def update_file_from_one_peer(self, files, client_socket):
        with self.lock:
            for file in files:
                if file not in self.files:
                    self.files[file] = files[file][1]

                if file not in self.client_info[client_socket]:
                    self.client_info[client_socket][file] = files[file][0]
                else:
                    for index in files[file][0]:
                        if index not in self.client_info[client_socket][file]:
                            self.client_info[client_socket][file].append(index)
                
                
                
    def find_peer_have(self, target_file):
        peer_list = []
        for client in self.client_info:
            if target_file in self.client_info[client]:
                ip, port = client.getpeername()
                peer_list.append({"ip": ip, "port": port+1, "indexes": self.client_info[client][target_file]})
        return peer_list    
            
    def handle_specific_client(self, client_socket : socket.socket, client_addr):
        
        print(f"accept connection from the client {client_addr}")
        self.create_and_send_message(client_socket, mess_type.HANDSHAKE)
        
        while self.running: 
            
            try:
                message = client_socket.recv(RECEIVE_SIZE).decode(CODE)
            except Exception as e:
                print(f"a false in receiving from peer: {e}")
            if not message:
                continue
            
            try:
                message = self.parse_message(message) #
            except Exception as e:
                print(f"a false in parse message: {e}")
                
            if message["type"] == mess_type.HANDSHAKE.value:
                self.client_info[client_socket] = {}
                keys = list(message["file"].keys())
                for key in keys:
                    if key not in self.files:
                        self.files[key] = message["file"][key][1]
                    
                    self.client_info[client_socket] = {key: message["file"][key][0]}
                self.update_file_from_one_peer(message["file"], client_socket)#
            elif message["type"] == mess_type.REQUEST.value:
                target_file = message["file"]
                target_file = list(target_file.keys())[0]
                peer_list = self.find_peer_have(target_file)
                message["file"][target_file] = self.files[target_file]     
                self.create_and_send_message(client_socket, mess_type.RESPONSE, filename=message["file"],peers=peer_list)
            elif message["type"] == mess_type.CLOSE.value:
                with self.lock:
                    if client_socket in self.client_info:
                        for file in self.client_info[client_socket]:
                            flag = False
                            for client in self.client_info:
                                if client == client_socket: 
                                    continue
                                if file in self.client_info[client]:
                                    flag = True
                                    break
                            if not flag:
                                del self.files[file]
                        del self.client_info[client_socket]
                
                    client_socket.close()
                    print(f"client_info: {self.client_info}")
                    print(f"file: {self.files}")
                    break
            elif message["type"] == mess_type.PEER_UPDATE_REQUEST.value:
                for client in self.client_info:
                    if client == client_socket:
                        continue
                    self.create_and_send_message(client, mess_type.SERVER_UPDATE_REQUEST) 
                
                time.sleep(5)
                self.create_and_send_message(client_socket, mess_type.SERVER_UPDATE_RESPONSE, filename=self.files)
            elif message["type"] == mess_type.PEER_UPDATE_RESPONSE.value:
                self.update_file_from_one_peer(message["file"], client_socket)
                
            
            
                
                
                
                
                
tracker = server()

while True: 
    command = input("")
    if command == "end":
        tracker.stop()
        break



 