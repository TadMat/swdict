'''
SignWriting Dictionary Class
'''
import sqlite3
import struct
import pickle
import time
import os
from dataclasses import dataclass
import xml.etree.ElementTree as ET

sss_dict01 = None
sss_dict45 = None
sss_dict23 = None
data_dir = 'data'

@dataclass(frozen=True)
class Symbol:
    """ISWA symbol in a sign
    """
    category: int   # category of ISWA
    id: int     # symbol id
    x:  int     # position x
    y:  int     # position y


@dataclass (frozen=True)
class Sign:
    """Sign in swdic.db
    """
    id: int     # sign id in dictionary
    gloss: str
    tag: str
    symbols: list # Symbol list


def pack_sss(sss):
    '''
    Pack sss string into 4 bytes sss
        ex) '01-02-003-04-05-06' -> b'\x12\x03\x45\x06'
    '''
    seg = sss.split('-')
    assert len(seg) == 6  # sss must be split into six segments
    cat = int(seg[0])  # category
    grp = int(seg[1])  # group
    bsym = int(seg[2]) # base symbol
    var = int(seg[3])  # variation
    fill = int(seg[4]) # fill
    rot = int(seg[5])  # rotation

    packed_sss = struct.pack('BBBB',
        (cat << 4) + grp,   # category|gropu
        bsym,               # base symbol
        (var << 4) + fill,  # variation | fill
        rot)                # rotation
    return packed_sss


#@staticmethod
def unpack_sss(packed_sss):
    '''
    Unpack sss bytes into string
    '''
    bs = struct.unpack('BBBB', packed_sss)
    cat = bs[0] >> 4
    grp = bs[0] & 0x0f
    bsym = bs[1]
    var = bs[2] >> 4
    fill = bs[2] & 0x0f
    rot = bs[3]

    sss = f'{cat:02}-{grp:02}-{bsym:03}-{var:02}-{fill:02}-{rot:02}'
    return sss
    

def sss_category(sss):
    ''' returns category of sss '''
    if type(sss) == str:
        # string SSS
        cat = int(sss[:2])
        return cat
    elif type(sss) == bytes:
        # packed SSS
        cat = sss[0] >> 4
        return cat
    print("*** Invalid SSS type:", type(sss), sss)
    return None


def sss2id(sss):
    """ID and category of SSS
    sss: string or packed sss
    returns: ID and category
    """
    global sss_dict01
    global sss_dict45
    global sss_dict23

    if sss_dict01 is None:
        load_sss_dicts()

    cat = sss_category(sss)
    if type(sss) == str:
        sss = pack_sss(sss)

    if cat == 1:
        id = sss_dict01[sss]
    elif cat == 4 or cat == 5:
        id = sss_dict45[sss]
    elif cat == 2 or cat == 3:
        id = sss_dict23[sss]
    else:
        id = None
        print("### SSS not in dict:", unpack_sss(sss), type(sss))
    return (id, cat)


def id2sss(id: int, category: int):
    '''convert id and category into SSS
    '''
    global sss_dict01
    global sss_dict45
    global sss_dict23

    if sss_dict01 is None:
        load_sss_dicts()

    if category == 1:
        dict = sss_dict01
    elif category == 4 or category == 5:
        dict = sss_dict45
    elif category == 2 or category == 3:
        dict = sss_dict23
    else:
        return None

    ids = [k for k, v in dict.items() if v == id]
    if len(ids) > 0:
        return unpack_sss(ids[0])
    else:
        print("@@@ ID is not in dict:", id)
        return None


def load_sss_dicts():
    ''' SSSからIDを得るための辞書をロードする '''
    global sss_dict01
    global sss_dict45
    global sss_dict23
    global data_dir

    DICT_FILE_01 = 'packed-sss-dict-01.pkl'
    DICT_FILE_45 = 'packed-sss-dict-45.pkl'
    DICT_FILE_23 = 'packed-sss-dict-23.pkl'
    
    if sss_dict01:
        # already loaded
        return

    base_dir = os.path.join(os.path.dirname(__file__), data_dir)

    dict_path01 = os.path.join(base_dir, DICT_FILE_01)
    dict_path45 = os.path.join(base_dir, DICT_FILE_45)
    dict_path23 = os.path.join(base_dir, DICT_FILE_23)

    #print('dict_path01:', dict_path01)


    with open(dict_path01, 'rb') as f:
        # handshape
        sss_dict01 = pickle.load(f)
        #print('###', sss_dict01)

    with open(dict_path45, 'rb') as f:
        # head & face
        sss_dict45 = pickle.load(f)

    with open(dict_path23, 'rb') as f:
        # movement & dynamics
        sss_dict23 = pickle.load(f)


def swml2sign(text: str):
    """Generate sign from swml string
    text: swml string
    """
    root = ET.fromstring(text)
    child = root.find('sign')
    gloss = child.find('gloss').text
    symbols = []
    for symbol in child.iter('symbol'):
        pos_x = int(symbol.get('x'))
        pos_y = int(symbol.get('y'))
        sss = symbol.text
        id, cat = sss2id(sss)
        if id is not None:
            sym = Symbol(cat, id, pos_x, pos_y)
            symbols.append(sym)
    sign = Sign(id=0, gloss=gloss, tag='', symbols=symbols)
    return sign


def sign_from_swmlfile(path: str):
    with open(path, 'r') as f:
        swmlstr = f.read()
    sign = swml2sign(swmlstr)
    return sign


class SwDict:
    '''
    SignWriting Dictionary Class
    '''    
    def __init__(self):

        self.signs = {}
        # signs is dictionary of sign,
        #   key: signid, value: (gloss, symbols)
        # symbols is a list of symbols
        #   symbol is a tuple of (packed_sss, pos_x, pos_y)
        self.from_file('swdict.pkl')
        self.signid_vocab = {}

    def get_signid_vocab(self):
        """
        Get signid vocabulari
        Returns: signid-serial number dictionary for generate one-hot vector
        """
        if len(self.signid_vocab) == 0:
            vocab_idx = 0
            for key in self.signs.keys():
                self.signid_vocab[key] = vocab_idx
                vocab_idx += 1
        return self.signid_vocab


    def from_db(self, swdic_file="swdic.db"):
        ''' Read swdic.db file '''
        global data_dir
        swdic_path = os.path.join(os.path.dirname(__file__), data_dir)
        swdic_path = os.path.join(swdic_path, swdic_file)
        con = sqlite3.connect(swdic_path)
        cur_sign = con.cursor()
        cur_symbol = con.cursor()

        self.signs = {}

        for row in cur_sign.execute(
                'SELECT SignID, Gloss, Tag, StdGloss, IsCompound \
                    FROM Signs ORDER BY SignID;'):
            signid = int(row[0])
            gloss = row[1]
            tag = row[2]
            if tag is None:
                tag = ''
            #if tag is not None and len(tag) > 0:
            #    gloss += tag
            std_gloss = row[3]
            if std_gloss is not None and len(std_gloss) > 0:
                # skip alias sign
                continue
            is_compound = row[4]
            if is_compound == 1:
                # skip compound sign
                continue
            
            query = f'SELECT SSS, pos_x, pos_y FROM Spelling \
                WHERE SignID = {signid} ORDER BY SubID;'
            symbol_rows = cur_symbol.execute(query).fetchall()
            if len(symbol_rows) == 0:
                # skip sign which has no symbol
                continue

            symbols = []    # symbol list
            for sym_row in symbol_rows:
                # Read symbols
                sss = sym_row[0]
                #packed_sss = pack_sss(sss)
                id, cat = sss2id(sss)
                pos_x = int(sym_row[1])
                pos_y = int(sym_row[2])
                sym = Symbol(cat, id, pos_x, pos_y)
                symbols.append(sym)
        
            sign = Sign(id=signid, gloss=gloss, tag=tag, symbols=symbols)
            self.signs[signid] = sign
        con.close()
    

    def save_signs(self, output_path):
        ''' Save sign list into file '''
        with open(output_path, 'wb') as f:
            pickle.dump(self.signs, f)
    

    def from_file(self, input_file):
        ''' Load sign list from file '''
        global data_dir

        #print(__file__)
        #print(os.path.dirname(__file__))
        input_path = os.path.join(os.path.dirname(__file__), data_dir)
        input_path = os.path.join(input_path, input_file)
        with open(input_path, 'rb') as f:
            self.signs = pickle.load(f)


    def size(self):
        ''' vocabulary size '''
        return len(self.signs)


    def search_by_id(self, id):
        ''' search sign by sign id
        '''
        if id in self.signs:
            return self.signs[id]
        else:
            return None
    

    def search_by_gloss(self, gloss):
        '''search sign by gloss
        '''
        signs = [v for k, v in self.signs.items() \
            if v.gloss == gloss]
        return signs


    def search_by_name(self, name):
        ''' search sign by name (gloss+tag)
        '''
        signs = [v for k, v in self.signs.items() \
            if v.gloss + v.tag == name]
        return signs


    def sign_list(self):
        '''return list of signs
        '''
        return list(self.signs.values())


def test():
    ''' SwDic test '''
    swdict = SwDict()

    start_time = time.perf_counter()
    # load from sqlite db
    swdict.from_db('./swdic.db')
    end_time = time.perf_counter()
    print('Data load time (from_db):', end_time - start_time)

    #swdict.save_signs('swdict.pkl')

    start_time = time.perf_counter()
    # load from dumped file
    swdict.from_file('./swdict.pkl')
    end_time = time.perf_counter()
    print('Data load time (from_file):', end_time - start_time)
 
    # search sign by ID
    start_time = time.perf_counter()
    gloss, symbols = swdict.search_by_id(1)
    end_time = time.perf_counter()
    print('Time for searching sign by ID:', end_time - start_time)
    print(gloss)
    for packed_sss, pos_x, pos_y in symbols:
        print(unpack_sss(packed_sss))
    
    # search sign by name
    start_time = time.perf_counter()
    gloss, symbols = swdict.search_by_name('父')
    end_time = time.perf_counter()
    print('Time for searching sign by name:', end_time - start_time)
    print(gloss)
    for packed_sss, pos_x, pos_y in symbols:
        print(unpack_sss(packed_sss))


def sss_test():
    sss = "05-02-003-01-02-03"
    packed_sss = pack_sss(sss)
    print('category:', sss_category(sss))
    print('category:', sss_category(packed_sss))

#if __name__ == '__main__':
#    #sss_test()
#    test()
