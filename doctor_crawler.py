# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/doctor_crawler.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

"""
医生抖音视频抓取入口。

启动本地 Web 对话框（自动打开浏览器）：
1. 从项目根目录的 抖音医生账号.csv 加载医生清单（姓名 -> 抖音主页链接）
2. 页面中选择医生姓名、输入抓取视频数量
3. 提交后启动 creator 模式爬虫，弹出浏览器扫码登录抖音后开始抓取
4. 已抓取过的视频自动跳过（记录在 data/douyin/state/crawled_aweme_ids.jsonl）

运行：uv run python doctor_crawler.py
"""

import threading
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8080
DOCTOR_PAGE_URL = f"http://{HOST}:{PORT}/api/doctor"


def _open_page() -> None:
    webbrowser.open(DOCTOR_PAGE_URL)


if __name__ == "__main__":
    # 服务就绪前打开浏览器会有竞态，延迟 1.5 秒再打开页面
    threading.Timer(1.5, _open_page).start()
    uvicorn.run("api.main:app", host=HOST, port=PORT)
