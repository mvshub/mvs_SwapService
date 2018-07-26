import json
from utils.decimal_encoder import DecimalEncoder

ERR_SUCCESS = 0
ERR_BAD_PARAMETER = 1
ERR_SERVER_ERROR = 2
ERR_WITHDRAW_EXISTED = 3
ERR_INVALID_ADDRESS = 4
ERR_INVALID_AMOUNT = 5

errors = {
    ERR_SUCCESS: 'success',
    ERR_BAD_PARAMETER: 'bad parameter',
    ERR_SERVER_ERROR: 'internal server error',
    ERR_WITHDRAW_EXISTED: 'withdraw existed',
    ERR_INVALID_ADDRESS: 'invalid address',
    ERR_INVALID_AMOUNT: 'invalid amount'
}


def make_response(code=ERR_SUCCESS, result=None):
    if result is None and code != ERR_SUCCESS:
        result = errors[code]
    from utils.crypto import encrypt
    import os
    return json.dumps({'code': code, 'result': result}, cls=DecimalEncoder)
