import django
import time
from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dailyfresh.settings')
django.setup()

app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/8')


@app.task
def send_register_active_email(to_email, username, token):
    subject = '天天生鲜欢迎信息'
    message = ''
    html_message = "<h1>%s,欢迎你注册为天天生鲜用户</h1>请点击下面的链接激活为你的账户</br><a " \
                   "href='http:0.0.0.0:8080/user/active/%s'>http:0.0.0.0:8080/user/active/%s</a>" % (
                       username, token, token)
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    send_mail(subject, message, sender, recipient_list=receiver, html_message=html_message)
    time.sleep(5)
