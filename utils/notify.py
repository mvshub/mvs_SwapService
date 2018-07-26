import requests
import json
import logging
from utils.decimal_encoder import DecimalEncoder
from utils.exception import DepositNotifyException, WithdrawNotifyException


def notify_swap(swap, best_block_height, feedback):
    data = {
        'swap_id':swap.iden,
        'coin':swap.coin,
        'to_address':swap.to_address,
        'tx_hash':swap.tx_hash,
        'height':swap.block_height,
        'token':swap.token,
        'amount':swap.amount
    }
    logging.info('notify swap, %s' % data)

    from utils.crypto import sign_data, encrypt
    import os
    data = json.dumps(data, cls = DecimalEncoder)
    sign=""
    # sign = sign_data(os.environ['privkey'], data)
    # data = encrypt(os.environ['pubkey'], data)
    res = requests.post(feedback, data=data, headers={'Content-Type':'text/plain', 'signature':sign}, timeout=5)
    if res.status_code != 200:
        raise DepositNotifyException('notify deposit exception, %s, %s' % (res.status_code, res.text))