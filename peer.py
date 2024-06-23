import socket
import threading
import random
import os
import ast
import time

import common
from common import mess_type

import file
from file import Piece
from file import File

PEER_IP = common.get_ip_address()
PEER_PORT = random.randint(12600, 22000)
LISTEN_DURATION = 5
RECEIVE_SIZE = 1024
CODE = 'utf-8'

class peer:
    def __init__(self):
        # the address including the IP address and port number of the peer
        self.port_for_server_connection = PEER_PORT
        self.port_for_peer_connection = PEER_PORT + 1
        # self.port_for_download = PEER_PORT + 2
        self.ip = PEER_IP
        self.id = PEER_PORT
        self.running = False
        self.file_in_dir = []
        
        self.lock = threading.Lock()
        self.server = []
        self.peer_downloading_from = []
        
        # A socket for listening from server only in the network is created
        self.handle_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.handle_server_socket.bind((self.ip, self.port_for_server_connection))
        print(f"a peer with IP address {self.ip}, ID {self.id} is created")
        
        # A socket for listening from other peers in the network
        self.handle_peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.handle_peer_socket.bind((self.ip, self.port_for_peer_connection))
        
        # A socket for downloading from other peers in the network
        # self.download_from_peer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.download_from_peer.bind((self.ip, self.port_for_download))
        
        
        self.connect_server_thread = threading.Thread(target=self.connect_server_channel)
        self.listen_peer_thread = threading.Thread(target=self.listen_peer_channel)
        
    @property
    def respo_path(self):
        respo_path = "peer_respo_" + str(self.id)
        os.makedirs(respo_path, exist_ok=True)
        respo_path += "/"
        return respo_path
    
    def get_file_in_dir(self) -> list:
        directory_file = os.listdir(self.respo_path)
        files = []
        if len(directory_file) == 0:
            return files
        else: 
            for name in directory_file:
                if(os.path.getsize(self.respo_path + name) == 0):
                    os.remove(self.respo_path + name)
                else:
                    files.append(File(self.respo_path+name))
                    files[-1].get_all_info_locally()
        return files

    
    def create_and_send_message(self, connect_socket : socket.socket, type : mess_type,
                                filename = {}, peers = [], data = b'', indx = 0):
        message = ""
        if type == mess_type.HANDSHAKE:
            message = f"type::{type.value};sid::{self.id};file::{filename}" # filename has the form of a dictionary {"name" : [indexes, metainfo]}
        elif type == mess_type.REQUEST:
            message = f"type::{type.value};sid::{self.id};file::{filename}" #  filename has the form {"name" : [empty]}
        elif type == mess_type.PEER_REQUEST:
            message = f"type::{type.value};sid::{self.id};file::{filename}"
        elif type == mess_type.PEER_RESPONSE:
            message = f"type::{type.value};sid::{self.id};file::{filename};data::{data}"
        elif type == mess_type.PEER_UPDATE_REQUEST:
            message = f"type::{type.value};sid::{self.id}"
        elif type == mess_type.PEER_UPDATE_RESPONSE:
            message = f"type::{type.value};sid::{self.id};file::{filename}"
        elif type == mess_type.CLOSE:
            message = f"type::{type.value};sid::{self.id}"
        elif type == mess_type.PEER_UPDATE_RESPONSE:
            message = f"type::{type.value};sid::{self.id};file::{filename}"
        
        # print(message)
        connect_socket.send(message.encode(CODE))
    
    def parse_message(self, message) -> dict:
        pairs = message.split(";")
        mess_struct = {}
        
        for pair in pairs:
            pair = pair.split("::")
            mess_struct[pair[0]] = pair[1]
            
        mess_struct['type'] = int(mess_struct['type'])
        
        if mess_struct['type'] == mess_type.HANDSHAKE.value or mess_struct['type'] == mess_type.RESPONSE.value or mess_struct['type'] == mess_type.PEER_REQUEST.value or mess_struct['type'] == mess_type.PEER_RESPONSE.value or mess_struct['type'] == mess_type.SERVER_UPDATE_RESPONSE.value:
            mess_struct['file'] = ast.literal_eval(mess_struct['file'])
            
            
        if mess_struct['type'] == mess_type.RESPONSE.value:
            mess_struct['peers'] = ast.literal_eval(mess_struct['peers'])
            print(mess_struct['peers'])
            
            
        if mess_struct['type'] == mess_type.PEER_RESPONSE.value:
            mess_struct['data'] = ast.literal_eval(mess_struct['data'])
            
            
        print(mess_struct)  
        return mess_struct
    
    def listen_peer_channel(self):
        self.handle_peer_socket.listen()
        print("start listening for other peers...")
        while self.running:
            try:
                self.handle_peer_socket.settimeout(LISTEN_DURATION)
                connect_socket, addr = self.handle_peer_socket.accept()
            except socket.timeout as e:
                continue
            except Exception as e:
                print(f"a false in accepting connection from peer: {e}")
            
            
            handle_specific_peer = threading.Thread(target=self.handle_specific_peer, args=(connect_socket, addr))
            handle_specific_peer.start()
            
        self.handle_peer_socket.close()
        print("stop listening for other peers...")
        
        
    
    
    def handle_specific_peer(self, client_socket : socket.socket, client_addr):
        print(f"accept connection from peer {client_socket}")       
        
        while self.running:
            
            try:
                message = client_socket.recv(RECEIVE_SIZE).decode(CODE)
            except Exception as e:
                print(f"a false in receiving message from peer: {e}")
            
            if not message:
                continue
            
            try:
                message = self.parse_message(message)
            except Exception as e:
                print(f"a false in parse message: {e}")
                
            
            
            if message["type"] == mess_type.PEER_REQUEST.value:
                target_file = None
                target_name = list(message['file'])[0]
                piece_idx = message['file'][target_name]
                with self.lock:
                    self.file_in_dir = self.get_file_in_dir()
                for file in self.file_in_dir:
                    if target_name == file.meta_info['name']:
                        target_file = file
                        break
                if target_file is None:
                    print("no file found")
                    return
                if piece_idx in target_file.piece_idx_downloaded:
                    piece = target_file.get_piece(piece_idx)
                    self.create_and_send_message(client_socket, mess_type.PEER_RESPONSE, filename = {target_name : piece_idx}, data = piece.data)
                else:
                    self.create_and_send_message(client_socket, mess_type.PEER_RESPONSE, filename = {target_name : piece_idx}, data = b'NO FOUND')
            elif message["type"] == mess_type.CLOSE.value:
                client_socket.close()
                break
            
            else:
                print("unknown message type from p2p")
        
        client_socket.close()
            
                
    def connect_server_channel(self):
        server_ip = self.server[0]
        server_port = self.server[1]
        
        # connect to the server and send the info about id and files in respo for the server
        try:
            self.handle_server_socket.connect((server_ip, server_port))
        except socket.error as e:
            print(f"a false in connecting to the server: {e}")
            self.stop()
            return
        
        while self.running: 
            try:
                message = self.handle_server_socket.recv(RECEIVE_SIZE).decode(CODE)
            except Exception as e:
                print(f"a false in receiving message from server: {e}")
                break
            
            if not message:
                continue
            
            
            try:
                message = self.parse_message(message)
            except Exception as e:
                print(f"a false in parse message: {e}")
            
            if message["type"] == mess_type.HANDSHAKE.value:
                self.server_id = message['sid']
                print(f"files available for downloading:")
                for file in message['file']:
                    # print(file, message['file'][file])
                    print(file)
                with self.lock:
                    self.file_in_dir = self.get_file_in_dir()
                file_list = {}
                for file in self.file_in_dir:
                    info_list = [[file.piece_idx_downloaded[0],file.piece_idx_downloaded[-1]], file.meta_info]
                    file_list[file.meta_info['name']] = info_list
                self.create_and_send_message(self.handle_server_socket, mess_type.HANDSHAKE, filename = file_list)
            elif message["type"] == mess_type.RESPONSE.value:
                peer_list = message['peers']
                if len(peer_list) == 0:
                    print("no peer has the file")
                    continue
                
                target_file = list(message['file'].keys())[0]
                metainfo = message['file'][target_file]
                target_file = self.get_download_file(target_file, metainfo)
                self.peer_downloading_from.clear()
                print(f"file {target_file.piece_idx_downloaded} {target_file.piece_idx_not_downloaded}")
                for peer in peer_list:
                    try:
                        if peer['port'] == self.port_for_server_connection or peer['port'] == self.port_for_peer_connection:
                            if peer['ip'] == self.ip:
                                continue
                        peer_download_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        peer_download_socket.connect((peer['ip'], peer['port']))
                        self.peer_downloading_from.append(peer_download_socket)
                    except Exception as e:
                        print(f"a false in connecting to peer: {e}")
                        continue
                    
                    download_from_peer = threading.Thread(target=self.download_from_peer_func, args=(peer_download_socket, target_file))
                    download_from_peer.start()
            elif message["type"] == mess_type.SERVER_UPDATE_REQUEST.value:
                with self.lock:
                    self.file_in_dir = self.get_file_in_dir()
                file_list = {}
                for file in self.file_in_dir:
                    info_list = [[file.piece_idx_downloaded[0],file.piece_idx_downloaded[-1]], file.meta_info]
                    file_list[file.meta_info['name']] = info_list
                self.create_and_send_message(self.handle_server_socket, mess_type.PEER_UPDATE_RESPONSE, filename = file_list)
            elif message["type"] == mess_type.SERVER_UPDATE_RESPONSE.value:
                print(f"files available for downloading:")
                for file in message['file']:
                    # print(file, message['file'][file])
                    print(file)
                        
    
    def get_download_file(self, target_file, meta_info):
        for file in self.file_in_dir:
            if target_file == file.meta_info['name']:
                return file
            
        target_file = File(self.respo_path + target_file)
        target_file.meta_info = meta_info
        target_file.pieces = []
        target_file.piece_idx_downloaded = []
        target_file.piece_idx_not_downloaded = list(range(meta_info['num_of_pieces']))
        self.file_in_dir.append(target_file)
        with open(target_file.path, 'w') as f:
            pass
        if len(target_file.piece_idx_downloaded) != 0:
            target_file.piece_idx_not_downloaded.append(target_file.piece_idx_downloaded[-1])
        return target_file
    
    
    
    def download_from_peer_func(self, peer_download_socket : socket.socket, target_file):
        
        while self.running:
            
            try:
                with self.lock:
                    if len(target_file.piece_idx_not_downloaded) == 0:
                        print("The file is already downloaded")
                        break
                    piece_idx = target_file.piece_idx_not_downloaded.pop(0)
            except Exception as e:
                print(f"a false in choosing piece to download: {e}")
            print(f"requiring piece {piece_idx} from peer {peer_download_socket.getpeername()}")
            
            try:
                self.create_and_send_message(peer_download_socket, mess_type.PEER_REQUEST, filename = {target_file.meta_info['name'] : piece_idx})
            except Exception as e:
                print(f"a false in sending require message to peer: {e}")
                break
            
            
            try:
                message = peer_download_socket.recv(RECEIVE_SIZE).decode(CODE)
            except Exception as e:
                print(f"a false in receiving message from peer: {e}")
                break
            
            if not message:
                peer_download_socket.close()
                break
            
            try:
                message = self.parse_message(message)
            except Exception as e:
                print(f"a false in parse message: {e}")
            
            if message["type"] == mess_type.PEER_RESPONSE.value:
                if message['data'] == b'NO FOUND':
                    with self.lock:
                        target_file.piece_idx_not_downloaded.append(piece_idx)
                    continue
                else:
                    piece_rcv = Piece(data = message['data'], index = message["file"][target_file.meta_info['name']])
                    with self.lock:
                        target_file.get_piece_download(piece_rcv, target_file.path)
                    if len(target_file.piece_idx_not_downloaded) == 0:
                        print(f"file {target_file.meta_info['name']} has been downloaded")
                        self.create_and_send_message(peer_download_socket, mess_type.CLOSE)
                        peer_download_socket.close()
                        break
            else:
                print("no piece received")
            
            time.sleep(1)
    
    def close_connection(self, connect_socket : socket.socket):
        self.create_and_send_message(connect_socket, mess_type.CLOSE)
        connect_socket.close()
                             
    
    # fucntion for button on GUI
    def request_and_download_file(self):
        target_file = input("Input the file you want to download: ")
        self.create_and_send_message(self.handle_server_socket, mess_type.REQUEST, filename = {target_file : []})
    
    def start(self):
        server_ip = input("enter IP address of the server: ")
        server_port = int(input("enter port number the server is listening on: "))
        self.running = True
        self.server = [server_ip, server_port]
        self.connect_server_thread.start()
        self.listen_peer_thread.start()
    
    def stop(self):
        self.create_and_send_message(self.handle_server_socket ,mess_type.CLOSE)
        time.sleep(1)
        self.running = False
        self.handle_peer_socket.close()
        self.handle_server_socket.close()    

    def update_file_for_download(self):
        self.create_and_send_message(self.handle_server_socket, mess_type.PEER_UPDATE_REQUEST)
    
    # def stop_downloading(self):
    #     if len(self.peer_downloading_from) == 0:
    #         return
    #     for connnect in self.peer_downloading_from:
    #         self.create_and_send_message(connnect, mess_type.CLOSE)
    #         connnect.close()    
    
peer_port = int(input("enter the port number for the peer: "))            
PEER_PORT = peer_port
peer_f = peer()
while True:
    command = input("")
    if command == "request": 
        peer_f.request_and_download_file()
    elif command == "start":
        peer_f.start()
    elif command == "end":
        peer_f.stop()
        break
    elif command == "update": 
        peer_f.update_file_for_download()
    else:
        print("unknown command")
    # elif command == "stop":
    #     peer_f.stop_downloading()


        