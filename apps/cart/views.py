from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from goods.models import GoodsSKU
from django_redis import get_redis_connection

# Create your views here.


class CartAddView(View):
    """购物车添加记录"""
    def post(self, request):
        """购物车添加记录"""
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})
        # 校验商品数量
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '商品数目出错'})
        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})
        # 业务处理:添加购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        # 先获取sku_id -> hget cart_key 属性
        cart_count = conn.hget(cart_key, sku_id)
        if cart_count:
            count += int(cart_count)
        # 校验商品库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})
        # 设置hash中sku_id对应的值
        conn.hset(cart_key, sku_id, count)
        return JsonResponse({'res': 5, 'message': '添加成功'})


# /cart/
class CartInfoView(LoginRequiredMixin, View):
    """购物车页面"""
    def get(self, request):
        # 获取登录用户
        user = request.user
        # 获取用户的购物车商品信息
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        cart_dict = conn.hgetall(cart_key)
        skus = []
        # 保存用户购物车总数目和价格
        total_count = 0
        total_price = 0
        # 遍历获商品的信息
        for sky_id, count in cart_dict.items():
            # 根据商品的id获取商品的信息
            sku = GoodsSKU.objects.get(id=sky_id)
            # 计算商品的小计
            amount = sku.price * int(count)
            # 动态给sku对象增加一个小计属性
            sku.amount = amount
            # 动态给sku对象增加购物车数量
            sku.count = int(count)
            skus.append(sku)
            # 累加计算商品的总数目和总价格
            total_count += int(count)
            total_price += amount
        # 组织上下午
        context = {'total_count': total_count,
                   'total_price': total_price,
                   'skus': skus}
        return render(request, 'cart.html', context)


# 更新购物车记录
# /cart/update/
class CartUpdateView(View):
    """购物车记录更新"""
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        # 接受数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        # 数据校验
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})
        # 校验商品数量
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '商品数目出错'})
        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})
        # 业务处理
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        # 校验商品的库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})
        # 更新
        conn.hset(cart_key, sku_id, count)
        # 计算用户购物车中商品的总件数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)
        # 返回应答
        return JsonResponse({'res': 5, 'message': '更新成功',
                             'total_count': total_count})


# 删除购物车记录
class CartDeleteView(View):
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        sku_id = request.POST.get('sku_id')
        if not sku_id:
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})
        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})
        # 业务处理,删除购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        # 删除商品
        conn.hdel(cart_key, sku_id)
        # 计算用户购物车中商品的总件数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)
        # 返回应答
        return JsonResponse({'res': 3, 'message': '删除成功'})