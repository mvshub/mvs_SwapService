import time

def get_current_date():
    return int(time.strftime('%4Y%2m%2d', time.localtime()))

def get_current_time():
    return int(time.strftime('%2H%2M%2S', time.localtime()))

def get_n_days_before(n):
    return int(time.strftime(
        '%4Y%2m%2d', time.localtime(time.time() - n * 24 * 60 * 60)))
