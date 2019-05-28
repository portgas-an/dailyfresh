from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.generic import View
from django.urls import reverse
from goods.models import GoodsSKU
from django_redis import get_redis_connection
from user.models import Address
from django.contrib.auth.mixins import LoginRequiredMixin
from order.models import OrderInfo, OrderGoods
from datetime import datetime
from django.db import transaction


# Create your views here.


# /order/place
class OrderPlaceView(LoginRequiredMixin, View):
    """提交订单"""

    def post(self, request):
        """提交订单页面"""
        # 获取登录用户
        user = request.user
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
            sku.count = int(count)
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
        sku_ids = ','.join(sku_ids)
        context = {'skus': skus,
                   'total_count': total_count,
                   'total_price': total_price,
                   'transit_price': transit_price,
                   'total_pay': total_pay,
                   'addrs': addrs,
                   'sku_ids': sku_ids}
        # 使用模板
        return render(request, 'place_order.html', context)


# 前段创建的参数：地址(add_id) 支付方式(pay_method) 用户要购买的商品id字符串(sku_ids)
class OrderCommitView(View):
    """提交订单"""

    @transaction.atomic
    def post(self, request):
        """订单创建"""
        # 用户是否登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})
        # 接受参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        # 校验参数
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})
        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 2, 'errmsg': '非法支付方式'})
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            # 地址不存在
            return JsonResponse({'res': 3, 'errmsg': '地址不存在'})
        # todo:创建订单核心业务
        # 组织参数
        # 订单id:时间+用户id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)
        # 运费
        transit_price = 10
        # 总数目,总金额
        total_count = 0
        total_price = 0
        # 设置事务保存点
        save_id = transaction.savepoint()
        try:
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price)
            # todo:用户的订单中有几个商品就要加入几条记录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                for i in range(3):
                    # 获取商品的信息
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 4, 'errmsg': '商品不存在'})
                    # 从redis中获取用户的订单商品数量
                    count = conn.hget(cart_key, sku_id)

                    # todo:判断商品的库存
                    if int(count) > sku.stock:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 6, 'errmsg': '库存不足'})
                    orgin_stock = sku.stock
                    new_stock = orgin_stock - int(count)
                    new_sales = sku.sales + int(count)

                    # update df_goods_sku set stock=new_stock,sales=new_sales
                    # where id=sku_id and stock = orgin_stock
                    # 返回受影响的行数
                    res = GoodsSKU.objects.filter(id=sku_id, stock=orgin_stock).update(stock=new_stock, sales=new_sales)
                    if res == 0:
                        if i == 2:
                            # 尝试第三次没成功就下单失败
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res': 7, 'errmsg': '下单失败'})
                        continue
                    # todo:向df_order_info添加一条记录
                    OrderGoods.objects.create(order=order,
                                              sku=sku,
                                              count=count,
                                              price=sku.price)
                    # todo:更新商品的库存和销量
                    sku.stock -= int(count)
                    sku.sales += int(count)
                    sku.save()

                    # todo:累加计算订单商品的总数目,总价格
                    amount = sku.price * int(count)
                    total_count += int(count)
                    total_price += amount
                    # 跳出循环
                    break

            # todo:更新订单信息表中的总数量总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})
        # 提交事务
        transaction.savepoint_commit(save_id)
        # todo:清楚购物车里面的商品
        conn.hdel(cart_key, *sku_ids)

        # 返回订单
        return JsonResponse({'res': 5, 'message': '创建成功'})


# 前段传递的参数:订单id(order_id)
class OrderPayView(View):
    '''订单支付'''

    def post(self, request):

        # 是否登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})
        # 接受参数
        order_id = request.POST.get('order_id')
        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单id'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})
        # 业务处理
        return JsonResponse({'res': 3, 'pay_url': 'https://www.baidu.com'})


class CheckPayView(View):
    '''查看订单支付结果'''

    def post(self, request):
        '''查询支付结果'''
        # 是否登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})
        # 接受参数
        order_id = request.POST.get('order_id')
        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单id'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        trade_no = order_id
        order.trade_no = trade_no
        order.order_status = 4  # 待评价
        order.save()
        return JsonResponse({'res': 3, 'message': '支付成功'})


class CommentView(LoginRequiredMixin, View):
    '''订单评论'''

    def get(self, request, order_id):
        user = request.user
        # 校验数据
        if not order_id:
            return redirect(reverse('user:order'))
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))
        # 根据订单的状态获取订单的标题
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
        # 获取订单商品信息
        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            # 计算商品的小计
            amount = order_sku.count * order_sku.price
            # 动态给order_sku增加属性amount
            order_sku.amount = amount
        # 动态给order增加属性order_skus
        order.order_skus = order_skus
        return render(request, 'order_comment.html', {"order": order})

    def post(self, request, order_id):
        '''处理评论内容'''
        user = request.user
        if not order_id:
            return redirect(reverse('user:order'))
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))
        # 获取评论条数
        total_count = request.POST.get('total_count')
        total_count = int(total_count)

        for i in range(1, total_count + 1):
            # 获取评论的商品id
            sku_id = request.POST.get('sku_%d' % i)
            # 获取评论的商品内容
            content = request.POST.get('content_%d' % i, '')
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue
            order_goods.comment = content
            order_goods.save()
        order.order_status = 5
        order.save()

        return redirect(reverse('user:order', kwargs={"page": 1}))
