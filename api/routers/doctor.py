# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/routers/doctor.py
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

import csv
import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..schemas import (
    CrawlerStartRequest,
    CrawlerTypeEnum,
    LoginTypeEnum,
    PlatformEnum,
)
from ..services import crawler_manager

router = APIRouter(tags=["doctor"])

PROJECT_ROOT = Path(__file__).parent.parent.parent
DOCTOR_CSV_PATH = Path(os.environ.get("DOCTOR_CSV_PATH", str(PROJECT_ROOT / "抖音医生账号.csv")))
DOCTOR_PAGE_PATH = Path(__file__).parent.parent / "static" / "doctor.html"

CSV_COLUMN_URL = "抖音主页链接"
CSV_COLUMN_NAME = "医生姓名"
CSV_COLUMN_HOSPITAL = "所在医院"


def load_doctors() -> List[dict]:
    """读取医生账号 CSV，返回 [{name, hospital, url}]，按文件顺序。"""
    if not DOCTOR_CSV_PATH.exists():
        raise FileNotFoundError(f"医生账号文件不存在: {DOCTOR_CSV_PATH}")
    doctors: List[dict] = []
    with open(DOCTOR_CSV_PATH, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            url = (row.get(CSV_COLUMN_URL) or "").strip()
            name = (row.get(CSV_COLUMN_NAME) or "").strip()
            if not url or not name:
                continue
            doctors.append(
                {
                    "name": name,
                    "hospital": (row.get(CSV_COLUMN_HOSPITAL) or "").strip(),
                    "url": url,
                }
            )
    return doctors


def find_doctor(name: str) -> dict:
    for doctor in load_doctors():
        if doctor["name"] == name:
            return doctor
    raise KeyError(name)


@router.get("/doctors")
async def list_doctors():
    """医生账号列表（来自 CSV）"""
    try:
        return {"doctors": load_doctors()}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


class DoctorCrawlRequest(BaseModel):
    """按医生姓名发起抓取"""

    doctor_name: str
    video_count: int = Field(default=10, ge=0, description="抓取的新视频数量，0 表示全部")


@router.post("/doctors/crawl")
async def crawl_doctor_videos(request: DoctorCrawlRequest):
    """按姓名映射到 CSV 中的抖音主页链接，启动 creator 模式抓取"""
    name = request.doctor_name.strip()
    try:
        doctor = find_doctor(name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail=f"CSV 中找不到医生: {name}")

    crawl_request = CrawlerStartRequest(
        platform=PlatformEnum.DOUYIN,
        login_type=LoginTypeEnum.QRCODE,
        crawler_type=CrawlerTypeEnum.CREATOR,
        creator_ids=doctor["url"],
        enable_comments=False,
        enable_sub_comments=False,
        max_creator_notes_count=request.video_count,
    )
    success = await crawler_manager.start(crawl_request)
    if not success:
        raise HTTPException(status_code=400, detail="爬虫已在运行中或启动失败")

    return {"status": "ok", "doctor": doctor, "video_count": request.video_count}


@router.get("/doctor", response_class=HTMLResponse)
async def doctor_page():
    """医生视频抓取 Web 对话框"""
    return HTMLResponse(DOCTOR_PAGE_PATH.read_text(encoding="utf-8"))
