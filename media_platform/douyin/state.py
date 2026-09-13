# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/douyin/state.py
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

import json
import os
import time
from typing import Dict, Iterable, Optional, Set

import config


class DouyinCrawlState:
    """记录已抓取过的抖音作品，creator 模式增量抓取时用于去重。

    状态文件为 JSONL，一行一条记录：aweme_id、sec_user_id、crawled_at。
    """

    def __init__(self, state_file: Optional[str] = None):
        base_path = config.SAVE_DATA_PATH or "data"
        self.state_file = state_file or os.path.join(
            base_path, "douyin", "state", "crawled_aweme_ids.jsonl"
        )
        self._crawled: Dict[str, str] = {}  # aweme_id -> sec_user_id
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.state_file):
            return
        with open(self.state_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    # 容忍进程中断导致的最后一行写入不完整
                    continue
                aweme_id = item.get("aweme_id")
                if aweme_id:
                    self._crawled[aweme_id] = item.get("sec_user_id", "")

    @property
    def crawled_ids(self) -> Set[str]:
        return set(self._crawled)

    def mark_crawled(self, aweme_ids: Iterable[str], sec_user_id: str = "") -> None:
        new_ids = [
            aweme_id for aweme_id in aweme_ids if aweme_id and aweme_id not in self._crawled
        ]
        if not new_ids:
            return
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        crawled_at = int(time.time())
        with open(self.state_file, "a", encoding="utf-8") as f:
            for aweme_id in new_ids:
                record = {
                    "aweme_id": aweme_id,
                    "sec_user_id": sec_user_id,
                    "crawled_at": crawled_at,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        for aweme_id in new_ids:
            self._crawled[aweme_id] = sec_user_id
