from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client, get_tracker_conf
from django.conf import settings
import os
import re


def valid_ip(ip):
    if ("255" in ip) or (ip == "127.0.0.1") or (ip == "0.0.0.0"):
        return False
    else:
        return True


def get_ip(valid_ip):
    ipss = ''.join(os.popen("ifconfig").readlines())
    match = "\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    ips = re.findall(match, ipss, flags=re.M)
    ip = filter(valid_ip, ips)
    return "http://"+''.join(ip)+"/"


class FDFSStorage(Storage):
    """文件存储类"""

    def __init__(self, client_conf=None, base_url=None):
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf
        if base_url is None:
            base_url = get_ip(valid_ip)
        self.base_url = base_url

    def _open(self, name, mode='rb'):
        pass

    def _save(self, name, content):
        """保持文件使用"""
        # content包含文件上传内容file对象

        # 创建client对象
        client = Fdfs_client(get_tracker_conf(self.client_conf))

        # 上传文件到系统中
        res = client.upload_by_buffer(content.read())

        # dict
        # {
        #     'Group name': group_name,
        #     'Remote file_id': remote_file_id,
        #     'Status': 'Upload successed.',
        #     'Local file name': '',
        #     'Uploaded size': upload_size,
        #     'Storage IP': storage_ip
        # }
        if res.get('Status') != 'Upload successed.':
            # 上传你失败
            raise Exception('上传文件到 Fast DFS失败')
        filename = res.get('Remote file_id').decode('utf-8')
        return filename

    def exists(self, name):
        '''django判断文件是否可用'''
        return False

    def delete(self, name):
        pass

    def url(self, name):
        '''返回django文件路径'''
        return self.base_url + name

