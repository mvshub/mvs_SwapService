import time
from utils import mailsend


def send_mail(symbol, subject, content, history = {}):

    current_time = int(time.time())
    diff_time = 30 * 60 # 30 min

    # not maturity :-)
    if history.get(symbol, 0) + diff_time >= current_time:
        return

    history[symbol] = current_time

    # NOTICE: call send_mail after config and testing
    print("{}\n{}\n{}".format(symbol, subject, content))
    #ms = mailsend.MailSending()
    #ms.send_mail(symbol, subject, content)
