from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client, get_tracker_conf


class FDFSStorage(Storage):
    """文件存储类"""

    def _open(self, name, mode='rb'):
        pass

    def _save(self, name, content):
        """保持文件使用"""
        # content包含文件上传内容file对象

        # 创建client对象
        client = Fdfs_client(get_tracker_conf('/etc/fdfs/client.conf'))

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
        return "file.ace.com"+name