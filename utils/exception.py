class RpcException(Exception):
    pass


class CriticalException(Exception):
    pass


class TransactionNotfoundException(Exception):
    pass


class NotifyException(Exception):
    pass


class WithdrawNotifyException(NotifyException):
    pass


class DepositNotifyException(NotifyException):
    pass


class WithdrawException(Exception):
    pass


class SendingWithdrawException(WithdrawException):
    pass
