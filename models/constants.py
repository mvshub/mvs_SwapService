#!/usr/bin/env python
#! encoding=utf-8

from enum import IntEnum


FETCH_MAX_ROW = 1000


class Status(IntEnum):
    Swap_New = 1
    Swap_Issue = 2
    Swap_Send = 3
    Swap_Finish = 4

    Tx_Unconfirm = 5
    Tx_Confirm = 6

    Token_Normal = 7
    Token_Issue = 8


class Error(IntEnum):
    Success = 0
