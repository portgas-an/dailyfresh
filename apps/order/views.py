from django.shortcuts import render, redirect
from django.views.generic import View
from django.urls import reverse
from goods.models import GoodsSKU
from django_redis import get_redis_connection
from user.models import Address
# Create your views here.


# /order/place
class OrderPlaceView(View):
    """提交订单"""
    def post(self, request):
        """提交订单页面"""
        # 获取登录用户
        user  = request.user
        # 获取参数sku_ids
        sku_ids = request.POST.getlist('sku_ids')  # [1,2,3,4]
        # 校验参数
        if not sku_ids:
            return redirect(reverse('cart:show'))

        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        skus = []
        total_count = 0
        total_price = 0
        for sku_id in sku_ids:
            # 根据商品的id获取商品的信息
            sku = GoodsSKU.objects.get(id=sku_id)
            # 获取用户主要购买的商品的数量
            count = conn.hget(cart_key, sku_id)
            # 计算商品的小计
            amount = sku.price * int(count)
            # 动态给sku增加count属性
            sku.count = count
            # 动态给sku增加amount属性
            sku.amount = amount
            # 追加
            skus.append(sku)
            total_count += int(count)
            total_price += amount

        transit_price = 10
        # 实款数
        total_pay = total_price + transit_price
        # 获取用户的收货地址
        addrs = Address.objects.filter(user=user)
        # 组织上下文
        context = {'skus': skus,
                   'total_count_': total_count,
                   'total_price': total_price,
                   't'}