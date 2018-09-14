import datetime

def get_beijing_datetime():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=8)

def get_current_date():
    return int(datetime.datetime.strftime(get_beijing_datetime(), '%4Y%2m%2d'))

def get_current_time():
    return int(datetime.datetime.strftime(get_beijing_datetime(), '%2H%2M%2S'))

def get_n_days_before(n):
    n_days_before = get_beijing_datetime() - datetime.timedelta(days=n)
    return int(datetime.datetime.strftime(n_days_before, '%4Y%2m%2d'))

def get_local_time():
    return datetime.datetime.strftime(get_beijing_datetime(), "%4Y-%2m-%2d %2H:%2M:%2S")
