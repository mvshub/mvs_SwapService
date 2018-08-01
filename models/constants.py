#!/usr/bin/env python
#! encoding=utf-8

from enum import IntEnum


FETCH_MAX_ROW = 1000


class Status(IntEnum):
    Swap_New = 1
    Swap_Issue = 2
    Swap_Send = 3
    Swap_Finish = 4

    Tx_Unconfirm = 0
    Tx_Confirm = 1

    Token_Normal = 0
    Token_Issue = 1

StatusStr = {
    Status.Swap_New:'New',
    Status.Swap_Issue:'Issue',
    Status.Swap_Send:'Send',
    Status.Swap_Finish:'Finish',
}

ConfirmStr = {
    Status.Tx_Unconfirm:'Unconfirm',
    Status.Tx_Confirm:'Confirmed',
}

def ProcessStr(status, confirm):
    if status == Status.Swap_New:
        return "Scan transaction,waitting for process"
    elif Status == Status.Swap_Issue:
        return "SecondIssue Asset,"+ "waitting for confirm " \
        if confirm == Status.Tx_Unconfirm else "confirm tx success"
    elif status == Status.Swap_Send:
        return "Send Asset,"+ "waitting for confirm " \
        if confirm == Status.Tx_Unconfirm else "confirm tx success"
    
    return "Swap finished"


TokenStr = {
    Status.Token_Normal:'Normal',
    Status.Token_Issue:'Issue',
}

class Error(IntEnum):
    Success = 0
    EXCEPTION_GET_BINDER = 1
    EXCEPTION_GET_COINRPC = 2
    EXCEPTION_INVAILD_ADDRESS = 3
    EXCEPTION_COIN_NOT_EXIST = 4
    EXCEPTION_COIN_ISSUING = 5



class SwapException(Exception):
    def __init__(self, errcode_):
        self.errcode = errcode_

    errmsg={
       Error.Success:"",
       Error.EXCEPTION_GET_BINDER:"cannot find bind address in db",
       Error.EXCEPTION_GET_COINRPC:"failed to get rpc",
       Error.EXCEPTION_INVAILD_ADDRESS:"Invailed to_address",
       Error.EXCEPTION_COIN_NOT_EXIST:"Coin does not exist",
       Error.EXCEPTION_COIN_ISSUING:"Coin is issuing,cannot issue again"
    }  
    def get_error_str(self):
        if self.errcode in self.errmsg:
            return self.errmsg[self.errcode]

        return ""