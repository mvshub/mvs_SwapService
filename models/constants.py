#!/usr/bin/env python
#! encoding=utf-8

from enum import IntEnum

DEFAULT_REQUEST_TIMEOUT = 10
DEFAULT_REQUEST_TIMEOUT_MAX = 60

FETCH_MAX_ROW = 1000

SWAP_TOKEN_PREFIX = 'ERCT2.'

MAX_SWAP_ASSET_DECIMAL = 8

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
        str = "Secondary issue Asset, waitting for confirm"
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
    EXCEPTION_CONFIG_ERROR_DECIMAL = 7
    EXCEPTION_COIN_AMOUNT_NO_ENOUGH = 8


class SwapException(Exception):

    def __init__(self, errcode_, errstr_ = None):
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
        Error.EXCEPTION_CONFIG_ERROR_DECIMAL: "Config error of decimal number, must be specified"
    }

    def get_error_str(self):
        strAll = ""
        if self.errcode in self.errmsg:
            strAll = self.errmsg[self.errcode]

        if self.errstr != None:
            strAll = strAll + ':' + self.errstr

        return strAll
