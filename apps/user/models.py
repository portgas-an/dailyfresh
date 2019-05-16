from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
# Create your models here.
from db.base_model import BaseModel
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

class User(AbstractUser, BaseModel):
    """
    用户模型类
    """

    # def generate_active_token(self):
    #     """生成用户签名"""
    #     serializer = Serializer(settings.SECRET_KEY, 3600)
    #     info = {'confirm': self.id}
    #     token = serializer.dumps(info)
    #     return token.decode()

    class Meta:
        db_table = 'df_user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name


class AddressManager(models.Manager):
    """地址模型管理器"""
    # 改变原有查询结果集all()
    # 封装方法:用户操作模型对应的数据表
    def get_default_address(self, user):
        """获取用户的默认地址"""
        # self.model获取self对象所对应的模型类
        try:
            address = self.get(user=user, is_default=True) # model.Manager
        except self.model.DoesNotExist:
            # 不存在默认收货地址
            address = None
        return address


class Address(BaseModel):
    """
    地址模型
    """
    user = models.ForeignKey('User', verbose_name='所属账户', on_delete=models.CASCADE)
    receiver = models.CharField(max_length=20, verbose_name='收件人')
    addr = models.CharField(max_length=256, verbose_name='收件地址')
    zip_code = models.CharField(max_length=6, null=True, verbose_name='邮编编码')
    phone = models.CharField(max_length=11, verbose_name='联系电话')
    is_default = models.BooleanField(default=False, verbose_name='是否默认')
    # 自定义一个模型管理器
    objects = AddressManager()

    class Meta:
        db_table = 'df_address'
        verbose_name = '地址'
        verbose_name_plural = verbose_name
