#!/bin/env python
#-*- coding:utf-8 -*-
from email import encoders
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr
import smtplib

def sendMail(title,contentMsg):
    from_addr = ' '
    passwd = ' '
    to_addr = ' '
    smtp_addr = 'smtp.163.com'
    title_msg=title

    def _format_addr(s):
        name, addr = parseaddr(s)
        return formataddr((Header(name, 'utf-8').encode(), addr))

    msg = MIMEText(contentMsg, 'plain', 'utf-8')
    msg['From'] = _format_addr('机智的咯咯咯咯格 <%s>' % from_addr)
    msg['To'] = _format_addr('收件人 <%s>' % to_addr)
    msg['Subject'] = Header(title, 'utf-8').encode()

    s = smtplib.SMTP(smtp_addr, 25)  # 定义一个s对象
    #s.set_debuglevel(1)  # 打印debug日志
    s.login(from_addr, passwd)  # auth发件人信息
    s.sendmail(from_addr, to_addr, msg.as_string())
    s.quit()
