from django.conf.urls import url
from order.views import OrderPlaceView, OrderCommitVIew

urlpatterns = [
    url(r'^place$', OrderPlaceView.as_view(), name='place'),  # 提交订单页面
    url(r'^commit$', OrderCommitVIew.as_view(), name='commit'),  # 提交订单页面
]
