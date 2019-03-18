# -*- coding:utf-8 -*-
import os, sys, json, requests, threading, subprocess
from flask_pymongo import PyMongo
from app import MysqlDB
from app import MongoDB
from ... import common
import config
from ..drive import models


"""
    OneDrive 重新获取token
    @Author: yyyvy <76836785@qq.com>
    @Description:
    @Time: 2019-03-16
    id: 网盘ID
"""
def reacquireToken(id):
    data_list = models.drive_list.find_by_id(id)
    token = json.loads(json.loads(data_list.token))
    redirect_url = common.get_web_site()
    ReFreshData = 'client_id={client_id}&redirect_uri={redirect_uri}&client_secret={client_secret}&refresh_token={refresh_token}&grant_type=refresh_token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = ReFreshData.format(client_id = data_list.client_id, redirect_uri = redirect_url, client_secret = data_list.client_secret,
                              refresh_token = token["refresh_token"])
    url = config.BaseAuthUrl+'/common/oauth2/v2.0/token'
    res = requests.post(url, data=data, headers=headers)
    models.drive_list.update({"id": id, "token": json.dumps(res.text)}) # 更新数据库的Token
    return res.text


"""
    获取OneDrive文件列表
    @Author: yyyvy <76836785@qq.com>
    @Description:
    @Time: 2019-03-16
    token: 网盘ID
    path: 路径，如果为空则从根目录获取，否则从路径获取
"""
def get_one_file_list(id, path=''):
    data_list = models.drive_list.find_by_id(id)
    token = json.loads(json.loads(data_list.token))
    if path:
        BaseUrl = config.app_url + '/v1.0/me/drive/root:{}:/children?expand=thumbnails'.format(path)
    else:
        BaseUrl = config.app_url + '/v1.0/me/drive/root/children?expand=thumbnails'
    headers = {'Authorization': 'Bearer {}'.format(token["access_token"])}
    try:
        get_res = requests.get(BaseUrl, headers=headers, timeout=30)
        get_res = json.loads(get_res.text)
        if 'error' in get_res.keys():
            reacquireToken(id)
            get_one_file_list(id, path)
        else:
            if 'value' in get_res.keys():
                return {'code': True, 'msg': '获取成功', 'data': get_res}
            else:
                get_one_file_list(id, path)
    except:
        get_one_file_list(id, path)


"""
    OneDrive 重命名文件
    @Author: yyyvy <76836785@qq.com>
    @Description:
    @Time: 2019-03-16
    token: 网盘ID
    fileid: 源文件id
    new_name: 新文件名字
"""
def rename_files(id, fileid, new_name):
    data_list = models.drive_list.find_by_id(id)
    token = json.loads(json.loads(data_list.token))
    url = config.app_url + '/v1.0/me/drive/items/{}'.format(fileid)
    headers = {'Authorization': 'bearer {}'.format(token["access_token"]), 'Content-Type': 'application/json'}
    payload = {
        "name": new_name
    }
    get_res = requests.patch(url, headers=headers, data=json.dumps(payload))
    get_res = json.loads(get_res.text)
    if 'error' in get_res.keys():
        reacquireToken(id)
        rename_files(id, fileid, new_name)
    else:
        return {'code': True, 'msg': '成功', 'data':''}


"""
    OneDrive 删除文件
    @Author: yyyvy <76836785@qq.com>
    @Description:
    @Time: 2019-03-16
    token: 网盘ID
    fileid: 源文件id
"""
def delete_files(id, fileid):
    data_list = models.drive_list.find_by_id(id)
    token = json.loads(json.loads(data_list.token))
    url = config.app_url + '/v1.0/me/drive/items/{}'.format(fileid)
    headers = {'Authorization': 'bearer {}'.format(token["access_token"]), 'Content-Type': 'application/json'}
    get_res = requests.delete(url, headers=headers)
    if get_res.status_code == 204:
        return {'code': True, 'msg': '成功', 'data':''}
    else:
        reacquireToken(id)
        delete_files(id, fileid)


"""
    MongoDB 更新缓存
    @Author: yyyvy <76836785@qq.com>
    @Description:
    @Time: 2019-03-16
    drive_id: 驱动ID
    type: 更新类型，all全部，dif差异
"""
def update_cache(drive_id, type):
    driveinfo = models.drive_list.find_by_drive_id(drive_id)
    threads = []
    for i in driveinfo:
        command = "python {}/app/task/cuteTask.py {} {}".format(os.getcwd(), i.id, type)  # 后台任务文件路
        t = threading.Thread(target=run_command, args=(command,))
        threads.append(t)
    for t in threads:
        t.setDaemon(True)
        t.start()


"""
    执行shell指令
    @Author: yyyvy <76836785@qq.com>
    @Description:
    @Time: 2019-03-16
    command: shell指令
"""
def run_command(command):
    subprocess.Popen(command, shell=True)




"""
    MongoDB 更新缓存 后台任务
    @Author: yyyvy <76836785@qq.com>
    @Description:
    @Time: 2019-03-16
"""
def cache_task():
    print(1)