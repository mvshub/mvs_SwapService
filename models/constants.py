#!/usr/bin/env python
#! encoding=utf-8

from enum import IntEnum

DEFAULT_REQUEST_TIMEOUT = 10
DEFAULT_REQUEST_TIMEOUT_MAX = 60

FETCH_MAX_ROW = 1000

SWAP_TOKEN_PREFIX = 'ERC20.'

MAX_SWAP_ASSET_DECIMAL = 8

MIN_FEE_FOR_ETP_DEVELOPER_COMMUNITY = 10**8  # 1 ETP


def calc_multiple(fee):
    if int(fee) <= MIN_FEE_FOR_ETP_DEVELOPER_COMMUNITY:
        return 1

    diff = int(fee) / MIN_FEE_FOR_ETP_DEVELOPER_COMMUNITY - 1
    attenuation = 0.8
    option = 0.8
    return 1 + option * ((1 - pow(attenuation, diff)) / (1 - attenuation))


class Status(IntEnum):
    Swap_New = 1
    Swap_Issue = 2
    Swap_Send = 3
    Swap_Finish = 4
    Swap_Ban = 10

    Tx_Unconfirm = 0
    Tx_Confirm = 1

    Token_Normal = 0
    Token_Issue = 1

    Record_All = 0,
    Record_Finish = 1,
    Record_Pending = 2,


StatusStr = {
    Status.Swap_New: 'New',
    Status.Swap_Issue: 'Issue',
    Status.Swap_Send: 'Send',
    Status.Swap_Finish: 'Finish',
    Status.Swap_Ban: 'Ban',
}

ConfirmStr = {
    Status.Tx_Unconfirm: 'Unconfirm',
    Status.Tx_Confirm: 'Confirmed',
}


def ProcessStr(status, confirm):
    str = "Swap finished"
    if status == Status.Swap_New:
        str = "Scan transaction, waitting for process"
    elif status == Status.Swap_Issue:
        str = "Issue Asset, waitting for confirm"
        if confirm == Status.Tx_Confirm:
            str = "Confirm tx success"
    elif status == Status.Swap_Send:
        str = "Send asset, waitting for confirm"
        if confirm == Status.Tx_Confirm:
            str = "Confirm tx success"
    elif status == Status.Swap_Ban:
        str = "Swap ban"

    return str


TokenStr = {
    Status.Token_Normal: 'Normal',
    Status.Token_Issue: 'Issue',
}


class Error(IntEnum):
    Success = 0
    EXCEPTION_GET_BINDER = 1
    EXCEPTION_GET_COINRPC = 2
    EXCEPTION_INVAILD_ADDRESS = 3
    EXCEPTION_COIN_NOT_EXIST = 4
    EXCEPTION_COIN_ISSUING = 5
    EXCEPTION_COIN_AMOUNT_TOO_SMALL = 6
    EXCEPTION_COIN_AMOUNT_NO_ENOUGH = 7
    EXCEPTION_CONFIG_ERROR_DECIMAL = 8
    EXCEPTION_CONFIG_ERROR_EXCHANGE_RATE_URL = 9
    EXCEPTION_INVAILD_EXCHANGE_RATE = 10


class SwapException(Exception):

    def __init__(self, errcode_, errstr_=None):
        self.errcode = errcode_
        self.errstr = errstr_

    errmsg = {
        Error.Success: "",
        Error.EXCEPTION_GET_BINDER: "cannot find bind address in db",
        Error.EXCEPTION_GET_COINRPC: "failed to get rpc",
        Error.EXCEPTION_INVAILD_ADDRESS: "Invailed to_address",
        Error.EXCEPTION_COIN_NOT_EXIST: "Coin does not exist",
        Error.EXCEPTION_COIN_ISSUING: "Coin is issuing,cannot issue again",
        Error.EXCEPTION_COIN_AMOUNT_TOO_SMALL: "Coin amount too small",
        Error.EXCEPTION_COIN_AMOUNT_NO_ENOUGH: "Coin amount no enough",
        Error.EXCEPTION_CONFIG_ERROR_DECIMAL: "Config error of decimal number, must be specified",
        Error.EXCEPTION_CONFIG_ERROR_EXCHANGE_RATE_URL: "Config error of exchange rate url, must be specified",
        Error.EXCEPTION_INVAILD_EXCHANGE_RATE: "invaild exchange rate"
    }

    def get_error_str(self):
        strAll = ""
        if self.errcode in self.errmsg:
            strAll = self.errmsg[self.errcode]

        if self.errstr != None:
            strAll = strAll + ':' + self.errstr

        return strAll

def format_amount(amount):
    if not amount:
        return '0'

    amount_str = str(amount)
    return format_amount_str(amount_str)

def format_amount_str(amount_str):
    dot_index = amount_str.find('.')
    if dot_index != -1:
        e_index = amount_str.find('E-', dot_index)
        if e_index == -1:
            amount_str = amount_str.rstrip('0')
            if amount_str.endswith('.'):
                amount_str = amount_str[0:len(amount_str) - 1]
        else:
            prefix = amount_str[:e_index]
            postfix = amount_str[e_index:]
            prefix = prefix.rstrip('0')
            if prefix.endswith('.'):
                prefix = prefix[0:len(prefix) - 1]
            amount_str = prefix + postfix

    if amount_str == '0E-18':
        amount_str = '0'
    return amount_str

