import time
import requests
import json
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
    options = {'from': "0x0c1933b3fdaf77bc196e7853256959ab9b28e1ff",
                 'to': "0x2d23fdffe79c9b5769b399ccd0d8c2e46e1aea26",
              'value': hex(100000000000000000)}
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

    contract = "0x7cf4d8fdec9244e774272aac648d33e051fd83f4"


    data = '0xa9059cbb' + '0' * (64 - len(to_address)) + to_address + ('%064x' % 1234000000000000)
    res = make_request('eth_sendTransaction', [
        {'from': from_, 'to': contract, 'data': data}])
    return res

from mvs_rpc import mvs_api as mvs_rpc
def send_ethtoken_asset_from_mvs():
    em, result = mvs_rpc.didsendasset('test2', 'test123456', 'crosschain', constants.SWAP_TOKEN_PREFIX + 'XYZ', 19870000, message="0x0c1933b3fdaf77bc196e7853256959ab9b28e1ff")
    assert( em == None)
    return result['transaction']['hash']

def send_eth_asset_from_mvs():
    em, result = mvs_rpc.didsendasset('test2', 'test123456', 'crosschain', constants.SWAP_TOKEN_PREFIX + 'ETH', 13570000, message="0x0c1933b3fdaf77bc196e7853256959ab9b28e1ff")
    assert( em == None)
    return result['transaction']['hash']

def main():
    while True:
        print('eth->etp ' + send_eth_from_ethereum())
        print('ethtoken->etp ' + send_token_from_ethereum())
        print('etp->ethtoken: ' + send_ethtoken_asset_from_mvs())
        print('etp->eth: ' + send_eth_asset_from_mvs())
        print('sleep 300 seconds ...')
        time.sleep(300)

if __name__ == '__main__':
    main()
