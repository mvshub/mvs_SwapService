#!/usr/bin/env python3
#! encoding=utf-8

import urllib.request
import urllib.error
import datetime
import time
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

is_debug = False
is_force_mailing = False
is_dry_run = False

def send_mail(subject, content, attach_file=""):
    mailto_list = [
        "xxx1@viewfin.com",
        "xxx2@viewfin.com",
        "xxx3@viewfin.com",
        "xxx4@viewfin.com",
    ]                                 #收件人列表1
    if not is_debug:
        mailto_list.extend([
        ])                            #收件人列表2

    mail_host = "smtp.163.com"        #设置服务器
    mail_port = "465"                 #设置服务器端口
    mail_user = "mywatchdog@163.com"  #用户名
    mail_pass = "XXXXXXXXXXXXX"       #口令
    user_alias = "swap_weekly_report" #用户别名

    msg = MIMEMultipart()
    body = MIMEText(content, _subtype='plain', _charset='utf-8')
    msg.attach(body)

    if attach_file != "":
        attach1 = MIMEText(open(attach_file, 'rb').read(), 'base64', 'utf-8')
        attach1['Content-Type'] = 'application/octet-stream'
        attach1["Content-Disposition"] = 'attachment; filename="{}"'.format(attach_file)
        msg.attach(attach1)

    me = user_alias + "<" + mail_user + ">"
    msg['Subject'] = subject
    msg['From'] = me

    try:
        server = smtplib.SMTP_SSL(mail_host, mail_port)
        server.login(mail_user, mail_pass)
        for receiver in mailto_list:
            msg.__delitem__('To')
            msg['To'] = receiver
            if is_debug:
                print("Prepare to send mail to {} ......\n{}".format(msg['To'], body.as_string()))
            if not is_dry_run:
                server.sendmail(me, [receiver], msg.as_string())
            if is_debug:
                print("Send mail to {} succeed.\n------------\n\n".format(msg['To']))
        server.close()
        print("发送成功")
        return True
    except Exception as e:
        print("exception caught: {}".format(e))
        print("发送失败")
        return False

def save_html(url, file_name):
    try:
        urllib.request.urlretrieve(url, file_name)
        return True
    except urllib.error.URLError as e:
        if hasattr(e, 'reason'):
            print('We failed to reach a server.')
            print('Reason: ', e.reason)
        elif hasattr(e, 'code'):
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
        return False
    except Exception as e:
        print("exception caught: {}".format(e))
        return False

def get_query_url():
    if is_debug:
        return 'http://127.0.0.1:8081/report'
    else:
        return 'http://54.183.220.91:8081/report'

def get_beijing_time():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=8)

def generate_report_file_name():
    beijiing_time_str = datetime.datetime.strftime(get_beijing_time(), "%4Y-%2m-%2dT%2H-%2M-%2S")
    report_file_name = 'eth_swap_report_' + beijiing_time_str + '.html'
    if is_debug:
        report_file_name = 'debug-' + report_file_name
    return report_file_name

def need_send_mail():
    # send mail once at Sunday between 20:00 to 20:59
    d = get_beijing_time()
    return d.isoweekday() == 7 and d.hour == 20

def send_weekly_report():
    query_url = get_query_url()
    report_file_name = generate_report_file_name()
    if save_html(query_url, report_file_name):
        subject = "weekly report of swap service"
        content = "请查收附件: " + report_file_name
        attach_file = report_file_name
        send_mail(subject, content, attach_file)
        return True
    else:
        return False


######################## main ####################################
if __name__ == '__main__':
    is_debug = '-d' in sys.argv or '-D' in sys.argv
    is_force_mailing = '-f' in sys.argv or '-F' in sys.argv
    is_dry_run = "--dry-run" in sys.argv

    print("is_debug = {}".format(is_debug))
    print("is_force_mailing = {}".format(is_force_mailing))
    print("is_dry_run = {}".format(is_dry_run))
    time.sleep(2)

    if is_force_mailing:
        send_weekly_report()

    while True:
        while not need_send_mail():
            time.sleep(600)

        if send_weekly_report():
            time.sleep(3600)
