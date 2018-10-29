import requests
from utils.log.logger import Logger
from utils.exception import RpcException, CriticalException, RpcErrorException
from utils.decimal_encoder import DecimalEncoder
from utils import date_time
import json
import datetime
from models.constants import Status, Error, SwapException
from models import constants


class ExchangeRate:
    bitfinex_ethusd_url = 'https://api.bitfinex.com/v1/pubticker/ethusd'
    bitfinex_etpusd_url = 'https://api.bitfinex.com/v1/pubticker/etpusd'

    rightbtc_ethusd_url = 'https://www.rightbtc.com/api/public/ticker/ETHUSD'
    rightbtc_etpusd_url = 'https://www.rightbtc.com/api/public/ticker/ETPUSD'

    # coinmarketcap_etpeth_url = 'https://api.coinmarketcap.com/v2/ticker/1703/?convert=ETH'
    # rightbtc__etpeth_url = 'https://www.rightbtc.com/api/public/ticker/ETPETH'

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
                raise RpcErrorException('no data item.')

            data = js['data']
            if not isinstance(data, dict) or data.get('quotes') is None:
                raise RpcErrorException('no quotes item')

            quotes = data['quotes']
            if not isinstance(quotes, dict) or quotes.get('ETH') is None:
                raise RpcErrorException('no ETH item')

            eth = quotes['ETH']
            if not isinstance(eth, dict) or eth.get('price') is None:
                raise RpcErrorException('no price item')
            value = eth.get('price')
            return 1 / value

        except Exception as e:
            raise SwapException(Error.EXCEPTION_GET_EXCHANGE_RATE_FAIL,
                                'url: {}, error: {}'.format(url, str(e)))
        return None

    @classmethod
    def request_rightbtc_rate(cls, url):
        try:
            js = ExchangeRate.request_url(url)
            if not isinstance(js, dict) or js.get('result') is None:
                raise RpcErrorException('no data item.')

            result = js['result']
            if not isinstance(result, dict) or result.get('last') is None:
                raise RpcErrorException('no last item')

            value = result.get('last') * (1e-8)
            return value

        except Exception as e:
            raise SwapException(Error.EXCEPTION_GET_EXCHANGE_RATE_FAIL,
                                'url: {}, error: {}'.format(url, str(e)))
        return None

    @classmethod
    def get_etpeth_exchange_rate_prev(cls):
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

    @classmethod 
    def request_bitfinex_rate(cls, url):
        try:
            js = ExchangeRate.request_url(url)
            if not isinstance(js, dict) or js.get('last_price') is None:
                raise RpcErrorException('no last_price item.')

            return float(js.get('last_price'))

        except Exception as e:
            raise SwapException(Error.EXCEPTION_GET_EXCHANGE_RATE_FAIL,
                                'url: {}, error: {}'.format(url, str(e)))
        return None

    @classmethod
    def get_bitfinex_rate(cls):
        url = ExchangeRate.bitfinex_ethusd_url
        ethusd_rate = ExchangeRate.request_bitfinex_rate(url)

        url = ExchangeRate.bitfinex_etpusd_url
        etpusd_rate = ExchangeRate.request_bitfinex_rate(url)

        if not ethusd_rate or not etpusd_rate:
            return None

        return ethusd_rate/etpusd_rate

    @classmethod
    def get_rightbtc_rate(cls):
        url = ExchangeRate.rightbtc_ethusd_url
        ethusd_rate = ExchangeRate.request_rightbtc_rate(url)

        url = ExchangeRate.rightbtc_etpusd_url
        etpusd_rate = ExchangeRate.request_rightbtc_rate(url)

        if not ethusd_rate or not etpusd_rate:
            return None

        return ethusd_rate/etpusd_rate

    @classmethod
    def get_explorer_rate(cls):
        url = 'https://explorer.mvs.org/api/bridge/rate/ETHETP'

        try:
            js = ExchangeRate.request_url(url)
            if not isinstance(js, dict) or js.get('status') is None:
                raise RpcErrorException('no status item.')

            status_dict = js.get('status')
            if not isinstance(status_dict, dict) or status_dict.get('success') is None:
                raise RpcErrorException('no success item.')

            if status_dict.get('success') != 1:
                return None

            if js.get('result') is None:
                raise RpcErrorException('no result item.')

            return js['result']

        except Exception as e:
            return None

        return None

    @classmethod
    def get_exchanger_rate(cls):
        bitfinex_rate = ExchangeRate.get_bitfinex_rate()
        rightbtc_rate = ExchangeRate.get_rightbtc_rate()

        if not bitfinex_rate and not rightbtc_rate:
            raise SwapException(Error.EXCEPTION_GET_EXCHANGE_RATE_FAIL,
                                'token: ETH, target: ETP')

        if not bitfinex_rate:
            bitfinex_rate = rightbtc_rate
        elif not rightbtc_rate:
            rightbtc_rate = bitfinex_rate

        # Logger.get().info("bitfinex_rate: {}, rightbtc_rate: {}".format(
        #     bitfinex_rate, rightbtc_rate))

        # diff = abs(coinmarketcap_bitfinex_raterate - rightbtc_rate)
        # max_fluctuation = 0.2
        # if (diff / bitfinex_rate > max_fluctuation
        #         or diff / rightbtc_rate > max_fluctuation):
        #     raise SwapException(Error.EXCEPTION_INVAILD_EXCHANGE_RATE,
        #                         'bitfinex_rate: {}, rightbtc_rate: {}'.format(
        #                             bitfinex_rate, rightbtc_rate))
        # ret_rate = (bitfinex_rate + rightbtc_rate) / 2
        ret_rate = min(bitfinex_rate, rightbtc_rate)

        # base on center standard time, 12 hours after beijing time
        curr_datetime = date_time.get_datetime_of_timezone(-4)
        end_of_all_saints_day = datetime.datetime(2018, 11, 2)
        if curr_datetime > end_of_all_saints_day:
            ret_rate *= 0.9

        return ret_rate

    @classmethod
    def get_etpeth_exchange_rate(cls):
        explorer_rate = ExchangeRate.get_explorer_rate()
        exchanger_rate = ExchangeRate.get_exchanger_rate()

        if not explorer_rate:
            explorer_rate = exchanger_rate

        diff = abs(exchanger_rate - explorer_rate)
        max_fluctuation = 0.1
        if (diff / exchanger_rate > max_fluctuation
                or diff / explorer_rate > max_fluctuation):
            raise SwapException(Error.EXCEPTION_INVAILD_EXCHANGE_RATE,
                                'explorer_rate: {}, exchanger_rate: {}'.format(
                                    explorer_rate, exchanger_rate))

        # Logger.get().info("explorer rate: {}, exchanger rate: {}".format(
        #     explorer_rate, exchanger_rate))
        return explorer_rate
