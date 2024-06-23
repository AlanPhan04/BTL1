import os
import math
import ast

import common



class File:
    def __init__(self, path, metainfo = {}, pieces = []):
        self.meta_info = metainfo
        self.pieces = []
        self.piece_idx_downloaded = []
        self.piece_idx_not_downloaded = []
        self.path = path
    
    @property
    def data_hash(self):
        if self.pieces is None:
            return b""
        
        return b"".join([piece.data for piece in self.pieces])
        
    @property
    def data(self):
        return self.data_hash.decode(common.CODE)
    
    @property
    def downloaded_bytes(self):
        return len(self.data_hash)
    
    def get_meta_info(self):
        info_dict = {} # length, name, num_of_pieces, piece length
        info_dict['length'] = os.path.getsize(self.path)
        info_dict['name'] = os.path.basename(self.path)
        info_dict['num_of_pieces'] = math.ceil(info_dict['length'] / common.PIECE_SIZE)
        info_dict['piece_length'] = common.PIECE_SIZE
        self.meta_info = info_dict
        return info_dict
        
    def get_all_info_locally(self):
        pieces = []
        pieces_index = []
        meta_info = {}
        i = 0
        with open(self.path, 'r') as f:
            if(os.path.getsize(self.path) == 0):
                os.remove(self.path)
            data = f.read()[0]
        if data == "*":
            with open(self.path, 'r') as f:
                pieces_info = f.readline()
                pieces_info = pieces_info.split("::")
                pieces_index = ast.literal_eval(pieces_info[1])
                meta_info = ast.literal_eval(pieces_info[2])
            self.save_file_complete(self.path)
            
            with open(self.path, 'rb') as f:
                while True:
                    data = f.read(common.PIECE_SIZE)
                    try:
                        pieces.append(Piece(data, pieces_index[i]))
                    except IndexError:
                        break
                    i += 1
        else:
            with open(self.path, 'rb') as f:
                while True:
                    data = f.read(common.PIECE_SIZE)
                    if not data:
                        break
                    pieces.append(Piece(data, i))
                    pieces_index.append(i)
                    i += 1
                info_dict = {} # length, name, num_of_pieces, piece length
            meta_info = self.get_meta_info()
        self.pieces = pieces
        self.piece_idx_downloaded = pieces_index   
        self.piece_idx_not_downloaded = [i for i in range(meta_info['num_of_pieces']) if i not in pieces_index]
        self.meta_info = meta_info
            
    def get_piece_download(self, piece, path = "test.txt"):
        if piece is None:
            return
        if piece in self.pieces:
            self.pieces.remove(piece)
        self.pieces.append(piece)
        self.pieces = sorted(self.pieces, key = lambda x: x.index)
        self.piece_idx_downloaded.append(piece.index)
        self.piece_idx_downloaded = sorted(self.piece_idx_downloaded)
        if piece.index in self.piece_idx_not_downloaded:
            self.piece_idx_not_downloaded.remove(piece.index)
                
        with open(path, "wb") as f:
            if len(self.piece_idx_downloaded) != self.meta_info['num_of_pieces']:
                list_str = f"*::{self.piece_idx_downloaded}::{self.meta_info}\n"
                f.write(list_str.encode(common.CODE))
            for piece in self.piece_idx_downloaded:
                piece = self.get_piece(piece)
                f.write(piece.data)
                
    def get_piece(self, index):
        for piece in self.pieces:
            if piece.index == index:
                return piece
    
    def save_file_complete(self, path = "test.txt"):
        with open(path, 'r') as f:
            lines = f.readlines()
        with open(path, 'w') as f:
            f.writelines(lines[1:])
        
        
        
class Piece:
    def __init__(self, data : bytes= b'', index = 0):
        self.index = index
        self.data = data


# test = File("test.tx")
# test.get_all_info_locally()
# print(test.meta_info, test.piece_idx)
# for piece in test.pieces:
#     print(piece.index)
#     print(piece.data)





















