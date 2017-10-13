import ast
import os
import hashlib
import base64

def try_eval(val):
    try:
        val = ast.literal_eval(val)
    except (ValueError, SyntaxError):
        #evaluation failed, so we most likely have a string
        pass
    return val

def hash_password(password):
    salt = os.urandom(32)
    return base64.b64encode(_hash_password(password, salt)).decode('ascii')

def _hash_password(password, salt):
    #Technically not secure, because the hash computes too fast.
    #This makes it possible to brute-force. Good enough for this purpose though.
    m = hashlib.sha256()
    m.update(password.encode())
    m.update(salt)
    pw_hash = m.digest()
    return pw_hash + salt

def verify_password(password, hash_):
    hash_ = base64.b64decode(hash_.encode('ascii'))
    salt = hash_[32:]
    return _hash_password(password, salt) == hash_
