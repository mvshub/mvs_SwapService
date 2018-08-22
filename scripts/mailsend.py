#!/usr/bin/env python3
# coding:utf-8

import smtplib
from email.mime.text import MIMEText

class MailSending:
    def __init__(self):
        self.mailto_list = [
            "xxx1@viewfin.com",
            "xxx2@viewfin.com",
            "xxx3@viewfin.com",
        ]                                      #收件人列表
        self.mail_host = "smtp.exmail.qq.com"  #设置服务器
        self.mail_user = "watchdog@xxx.org"    #用户名
        self.mail_pass = "xxx"                 #口令
        self.user_alias = "swap-watchdog"      #用户别名

    def send_mail(self, from_user, subject, content):
        me = self.user_alias + "<" + self.mail_user + ">"
        msg = MIMEText(from_user + "\r\n" + content, _subtype='plain', _charset='gb2312')
        msg['Subject'] = subject
        msg['From'] = me
        msg['To'] = ";".join(self.mailto_list)
        try:
            server = smtplib.SMTP()
            server.connect(self.mail_host)
            server.login(self.mail_user, self.mail_pass)
            server.sendmail(me, self.mailto_list, msg.as_string())
            server.close()
            return True
        except Exception as e:
            print("exception caught: {}".format(e))
            return False

if __name__ == '__main__':
    ms = MailSending()
    if ms.send_mail("xxx@some.com", "watchdog test", u"watchdog 发送邮件测试"):
        print("发送成功")
    else:
        print("发送失败")
