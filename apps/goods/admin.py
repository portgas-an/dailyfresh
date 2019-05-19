from django.contrib import admin
from goods.models import *


# Register your models here.

class BaseModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        """更新表中的数据时"""
        super().save_model(request, obj, form, change)

        # 发出任务，celery_worker重新生成静态页面
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

    def delete_model(self, request, obj):
        super().delete_model(request, obj)

        # 发出任务，celery_worker重新生成静态页面
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()


class IndexPromotionBannerAdmin(BaseModelAdmin):
    pass


class GoodsTypeAdmin(BaseModelAdmin):
    pass


class IndexTypeGoodsBannerAdmin(BaseModelAdmin):
    pass


class IndexGoodsBannerAdmin(BaseModelAdmin):
    pass


admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
