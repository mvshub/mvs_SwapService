import requests
from utils.log.logger import Logger
from utils.exception import RpcException, CriticalException, RpcErrorException
from utils.decimal_encoder import DecimalEncoder
from utils import date_time
import json
from models.constants import Status, Error, SwapException
from models import constants


class ExchangeRate:
    coinmarketcap_etpeth_url = 'https://api.coinmarketcap.com/v2/ticker/1703/?convert=ETH'
    rightbtc__etpeth_url = 'https://www.rightbtc.com/api/public/ticker/ETPETH'

    @classmethod
    def request_url(cls, url):
        result = requests.get(
            url, timeout=constants.DEFAULT_REQUEST_TIMEOUT)
        if result.status_code != 200:
            raise RpcException(
                'bad request code, url: {}, {}'.format(url, result.status_code))
        return json.loads(result.text)

    @classmethod
    def request_coinmarketcap_rate(cls):
        try:
            url = ExchangeRate.coinmarketcap_etpeth_url
            js = ExchangeRate.request_url(url)
            if not isinstance(js, dict) or js.get('data') is None:
                raise RpcErrorException('not data item.')

            data = js['data']
            if not isinstance(data, dict) or data.get('quotes') is None:
                raise RpcErrorException('not quotes item')

            quotes = data['quotes']
            if not isinstance(quotes, dict) or quotes.get('ETH') is None:
                raise RpcErrorException('not ETH item')

            eth = quotes['ETH']
            if not isinstance(eth, dict) or eth.get('price') is None:
                raise RpcErrorException('not price item')
            value = eth.get('price')
            return 1 / value

        except Exception as e:
            raise SwapException(Error.EXCEPTION_GET_EXCHANGE_RATE_FAIL,
                                'url: {}, error: {}'.format(url, str(e)))
        return None

    @classmethod
    def request_rightbtc_rate(cls):
        try:
            url = ExchangeRate.rightbtc__etpeth_url
            js = ExchangeRate.request_url(url)
            if not isinstance(js, dict) or js.get('result') is None:
                raise RpcErrorException('not data item.')

            result = js['result']
            if not isinstance(result, dict) or result.get('sell') is None:
                raise RpcErrorException('not sell item')

            value = result.get('last') * (1e-8)
            return 1 / value

        except Exception as e:
            raise SwapException(Error.EXCEPTION_GET_EXCHANGE_RATE_FAIL,
                                'url: {}, error: {}'.format(url, str(e)))
        return None

    @classmethod
    def get_etpeth_exchange_rate(cls):
        coinmarketcap_rate = ExchangeRate.request_coinmarketcap_rate()
        #connection timeout to rightbtc
        #rightbtc_rate = ExchangeRate.request_rightbtc_rate()
        rightbtc_rate = ExchangeRate.request_coinmarketcap_rate()

        if not coinmarketcap_rate or not rightbtc_rate:
            raise SwapException(Error.EXCEPTION_GET_EXCHANGE_RATE_FAIL,
                                'token: ETH, target: ETP')
        diff = abs(coinmarketcap_rate - rightbtc_rate)
        max_fluctuation = 0.2
        if (diff / coinmarketcap_rate > max_fluctuation
                or diff / rightbtc_rate > max_fluctuation):
            raise SwapException(Error.EXCEPTION_INVAILD_EXCHANGE_RATE,
                                'coinmarketcap_rate: {}, rightbtc_rate: {}'.format(
                                    coinmarketcap_rate, rightbtc_rate))
        ret_rate = (coinmarketcap_rate + rightbtc_rate) / 2

        curr_datetime = date_time.get_beijing_datetime()
        end_of_all_saints_day = datetime.datetime(2018, 11, 2)
        if curr_datetime > end_of_all_saints_day:
            ret_rate *= 0.9

        return ret_rate
