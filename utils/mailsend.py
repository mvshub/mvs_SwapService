#!/usr/bin/env python3
# coding:utf-8

import smtplib
from email.mime.text import MIMEText

class MailSending:
    def __init__(self, is_debug=False):
        self.is_debug = is_debug
        self.mailto_list = [
            "xxx1@viewfin.com",
            "xxx2@viewfin.com",
            "xxx3@viewfin.com",
        ]                                      #收件人列表
        self.mail_host = "smtp.163.com"        #设置服务器
        self.mail_port = "465"                 #设置服务器端口
        self.mail_user = "mywatchdog@163.com"  #用户名
        self.mail_pass = "XXXXXXXXXXXXX"       #口令
        self.user_alias = "swap-watchdog"      #用户别名

    def send_mail(self, from_user, subject, content):
        me = self.user_alias + "<" + self.mail_user + ">"
        msg = MIMEText(from_user + "\r\n" + content, _subtype='plain', _charset='gb2312')
        msg['Subject'] = subject
        msg['From'] = me

        #一次发送至多人
        #msg['To'] = ";".join(self.mailto_list)
        #try:
        #    #server = smtplib.SMTP(self.mail_host)
        #    server = smtplib.SMTP_SSL(self.mail_host, self.mail_port)
        #    server.login(self.mail_user, self.mail_pass)
        #    if self.is_debug:
        #        print("Prepare to send mail to {} ......\n{}".format(msg['To'], msg.as_string()))
        #    server.sendmail(me, self.mailto_list, msg.as_string())
        #    if self.is_debug:
        #        print("Send mail to {} succeed.\n------------\n\n".format(msg['To']))
        #    server.close()
        #    return True
        #except Exception as e:
        #    print("exception caught: {}".format(e))
        #    return False

        #一次发送至一人, 循环遍历发送
        # Notice: 163 only support send to one receiver per time,
        # or else caught exception of (554, DT:SPM ...)
        try:
            #server = smtplib.SMTP(self.mail_host)
            server = smtplib.SMTP_SSL(self.mail_host, self.mail_port)
            server.login(self.mail_user, self.mail_pass)
            for receiver in self.mailto_list:
                msg.__delitem__('To')
                msg['To'] = receiver
                if self.is_debug:
                    print("Prepare to send mail to {} ......\n{}".format(msg['To'], msg.as_string()))
                server.sendmail(me, [receiver], msg.as_string())
                if self.is_debug:
                    print("Send mail to {} succeed.\n------------\n\n".format(msg['To']))
            server.close()
            return True
        except Exception as e:
            print("exception caught: {}".format(e))
            return False

if __name__ == '__main__':
    ms = MailSending(is_debug=True)
    if ms.send_mail("test@xxx.com", "hello", u"Hello world! 你好，世界！"):
        print("发送成功")
    else:
        print("发送失败")
