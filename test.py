import time
import requests
import json

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
              'value': hex(100)}
    gas = estimate_gas(options)
    options['gas'] = hex(gas)

    assert( unlock_account(options['from'], "passwd123456") )

    res = make_request('eth_sendTransaction', [options])
    return res

def send_token_from_ethereum():
    token = "ABC"
    to_address = "2d23fdffe79c9b5769b399ccd0d8c2e46e1aea26"

    from_ = "0x0c1933b3fdaf77bc196e7853256959ab9b28e1ff"

    assert (unlock_account(from_, "passwd123456"))

    contract = "0x0506e5ef752ea1129a7e6ed41df5e93131bee8a7"


    data = '0xa9059cbb' + '0' * (64 - len(to_address)) + to_address + ('%064x' % 100)
    res = make_request('eth_sendTransaction', [
        {'from': from_, 'to': contract, 'data': data}])
    return res

def main():
    while True:
        print(send_eth_from_ethereum())
        print(send_token_from_ethereum())
        time.sleep(30)


if __name__ == '__main__':
    main()