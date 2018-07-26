import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_pkcs1_v1_5
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_PSS, PKCS1_v1_5
from Crypto.Hash import SHA256
from base64 import b64encode


def sign_data(privkey, data):
    # private_key_loc = '/home/jiang/Downloads/privkey.pem'
    '''
    param: private_key_loc Path to your private key
    param: package Data to be signed
    return: base64 encoded signature
    '''

    # key = open(private_key_loc, "r").read()
    rsakey = RSA.importKey(privkey)
    signer = PKCS1_PSS.new(rsakey)
    digest = SHA256.new()
    # It's being assumed the data is base64 encoded, so it's decoded before
    # updating the digest
    digest.update(data)
    sign = signer.sign(digest)
    return b64encode(sign)


def encrypt(pubkey, data):
    rsakey = RSA.importKey(pubkey)
    cipher = Cipher_pkcs1_v1_5.new(rsakey)
    cipher_text = base64.b64encode(cipher.encrypt(data))
    return cipher_text


def verify(pubkey, data, signature):
    key = RSA.importKey(pubkey)
    h = SHA256.new()
    h.update(data)
    verifier = PKCS1_PSS.new(key)
    if verifier.verify(h, base64.b64decode(signature)):
        return True

    return False
