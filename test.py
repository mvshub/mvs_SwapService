import time
import requests
import json
import random
from models import constants

def make_request(method, params=[]):
    data = {"jsonrpc": "2.0", "method": method, "params": params, "id": 83}
    res = requests.post('http://10.10.10.175:8545', json.dumps(data), headers={'Content-Type': 'application/json'}, timeout=5)
    if res.status_code != 200:
        raise Exception('bad request code,%s' % res.status_code)
    try:
        js = json.loads(res.text)
    except Exception as e:
        raise Exception(
            'bad response content, failed to parse,%s' % res.text)
    if js.get('error') is not None:
        raise Exception('%s' % js['error']['message'])
    return js['result']

def unlock_account(address, passphrase, unlock_time=10):
    res = make_request('personal_unlockAccount', [
                            address, passphrase, unlock_time])
    return res

def estimate_gas(options):
    res = make_request('eth_estimateGas', [options])
    return int(res, 16)

def send_eth_from_ethereum():
    #1. send eth to scan address
    one_token = 10 ** 18
    amount = random.randrange(one_token*10, one_token*20)
    print('send_eth_from_ethereum: {}'.format(amount))
    options = {'from': "0x0c1933b3fdaf77bc196e7853256959ab9b28e1ff",
                 'to': "0x2d23fdffe79c9b5769b399ccd0d8c2e46e1aea26",
              'value': hex(amount)}
    gas = estimate_gas(options)
    options['gas'] = hex(gas)

    assert( unlock_account(options['from'], "passwd123456") )

    res = make_request('eth_sendTransaction', [options])
    return res

def send_token_from_ethereum():
    token = "XYZ"
    to_address = "2d23fdffe79c9b5769b399ccd0d8c2e46e1aea26"

    from_ = "0x0c1933b3fdaf77bc196e7853256959ab9b28e1ff"

    assert (unlock_account(from_, "passwd123456"))

    contract = "0x9faa766fcbcd3bdbab27681c7cca6e1a6016b7c5"

    one_token = 10 ** 12
    amount = random.randrange(one_token*10, one_token*20)
    print('send_token_from_ethereum: {}'.format(amount))
    data = '0xa9059cbb' + '0' * (64 - len(to_address)) + to_address + ('%064x' % amount)
    res = make_request('eth_sendTransaction', [
        {'from': from_, 'to': contract, 'data': data}])
    return res

from mvs_rpc import mvs_api as mvs_rpc
def send_ethtoken_asset_from_mvs():
    one_token = 10 ** 9
    amount = random.randrange(one_token*10, one_token*20)
    print('send_ethtoken_asset_from_mvs: {}'.format(amount))
    em, result = mvs_rpc.didsendasset('test2', 'test123456', 'crosschain', constants.SWAP_TOKEN_PREFIX + 'XYZ',\
            amount, message='{"type":"ETH", "address":"0x0c1933b3fdaf77bc196e7853256959ab9b28e1ff"}')
    assert( em == None)
    return result['transaction']['hash']

def send_eth_asset_from_mvs():
    one_token = 10 ** 9
    amount = random.randrange(one_token*10, one_token*20)
    print('send_eth_asset_from_mvs: {}'.format(amount))
    em, result = mvs_rpc.didsendasset('test2', 'test123456', 'crosschain', constants.SWAP_TOKEN_PREFIX + 'ETH',\
            amount, message='{"type":"ETH", "address":"0x0c1933b3fdaf77bc196e7853256959ab9b28e1ff"}')
    assert( em == None)
    return result['transaction']['hash']

def main():
    while True:
        try:
            print(time.ctime())
            print('eth->etp: ' + send_eth_from_ethereum())
            print('etp->eth: ' + send_eth_asset_from_mvs())
            print('ethtoken->etp: ' + send_token_from_ethereum())
            print('etp->ethtoken: ' + send_ethtoken_asset_from_mvs())
            print('sleep 200 seconds ...')
            time.sleep(200)
        except Exception as e:
            print('exception caught: {}'.format(e))

if __name__ == '__main__':
    main()
