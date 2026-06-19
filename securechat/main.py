#!/usr/bin/env python3
"""
SecureChat - 本地手机号注册与登录示例

功能说明：
- 本地 SQLite 数据库存储账号信息
- 注册时填写手机号、密码、真实姓名和身份证号
- 注册时生成本地验证码完成验证
- 登录时支持密码登录或验证码登录
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, 'src')
sys.path.insert(0, SRC_DIR)


def run_gui():
    from auth_ui import AuthApp
    app = AuthApp(data_dir=BASE_DIR)
    app.run()


if __name__ == '__main__':
    run_gui()
