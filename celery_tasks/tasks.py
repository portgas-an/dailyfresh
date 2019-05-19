import django
import time
from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dailyfresh.settings')
django.setup()

app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/8')

from goods.models import *
from django.template import loader
from django.conf import settings
from django.core.mail import send_mail


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


@app.task
def generate_static_index_html():
    """产生静态页面"""
    # 获取商品的种类信息
    types = GoodsType.objects.all()

    # 获取首页轮播商品信息
    goods_banners = IndexGoodsBanner.objects.all().order_by('index')

    # 获取首页促销活动信息
    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类商品展示信息
    for type in types:  # GoodsType
        # 获取type种类首页分类商品的图片展示信息
        image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
        # 获取type种类首页分类商品的文字展示信息
        title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

        # 动态给type增加属性，分别保存首页分类商品的图片展示信息和文字展示信息
        type.image_banners = image_banners
        type.title_banners = title_banners

    context = {'types': types,
               'goods_banners': goods_banners,
               'promotion_banners': promotion_banners}

    # 加载模板
    temp = loader.get_template('static_index.html')
    # 渲染模板
    static_index_html = temp.render(context)
    # 生成首页对应的静态文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')

    with open(save_path, 'w') as f:
        f.write(static_index_html)
