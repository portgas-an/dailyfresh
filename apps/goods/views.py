from django.shortcuts import render, redirect
from django.views.generic.base import View, reverse
from goods.models import *
from django_redis import get_redis_connection
from django.core.cache import cache
from order.models import OrderGoods
from django.core.paginator import Paginator
from jieba.analyse import ChineseAnalyzer

class IndexView(View):
    """首页"""
    def get(self, request):
        """显示首页"""
        context = cache.get('index_page_data')
        if context is None:

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
            # 设置缓存
            cache.set('index_page_data', context, 3600)

        # 获取用户购物车中商品的数目
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            # 用户已登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

        # 组织模板上下文
        context.update(cart_count=cart_count)

        # 使用模板
        return render(request, 'index.html', context)


# /good/商品id
class DetailView(View):
    """详情页"""
    def get(self, request, goods_id):
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在
            return redirect(reverse('goods:index'))
        # 获取商品分类信息
        types = GoodsType.objects.all()
        # 获取商品用户评论
        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment='')
        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('create_time')[:2]
        # 获取同一个SPU的其他规格商品
        samp_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)

        # 获取用户购物车中商品的数目
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            # 用户已登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)
            # 添加用户的历史记录
            history_key = 'history_%d' % user.id
            # 移除列表中的goods_id
            conn.lrem(history_key, 0, goods_id)
            # 把goods_id插入到列表中
            conn.lpush(history_key, goods_id)
            # 只保存5条用户历史浏览记录
            conn.ltrim(history_key, 0, 4)
        context = {'sku': sku,
                   'types': types,
                   'sku_orders': sku_orders,
                   'new_skus': new_skus,
                   'samp_spu_skus': samp_spu_skus,
                   'cart_count': cart_count}
        return render(request, 'detail.html', context)


# 种类id 页码 排序方式
# /list/种类id/页码/排序方式
class ListView(View):
    def get(self, request, type_id, page):
        # 获取种类信息
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            return render(request, 'index.html')
        types = GoodsType.objects.all()
        # 获取排序方式
        # sort=default 默认id
        # sort=price 价格
        # sort=hot 销量排序
        sort = request.GET.get('sort')
        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            sort = 'default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')
        # 对数据进行分页
        pageinator = Paginator(skus, 2)
        # 获取第page页的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1
        if page > pageinator.num_pages:
            page = 1
        # 获取分页
        skus_page = pageinator.page(page)
        # 页码控制,小于5显示所有，大于五显示全部
        num_pages = pageinator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages+1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <=2:
            pages = range(num_pages-4, num_pages+1)
        else:
            pages = range(page-2,page+3)

        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=type).order_by('create_time')[:2]
        # 获取用户购物车中商品的数目
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            # 用户已登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

        # 组织模板上下文
        context = {'type': type,
                   'types': types,
                   'pages': pages,
                   'skus_page': skus_page,
                   'new_skus': new_skus,
                   'cart_count': cart_count,
                   'sort': sort}

        return render(request, 'list.html', context)