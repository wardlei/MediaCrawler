# -*- coding: utf-8 -*-

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import config
from api.main import app
from api.routers import doctor
from api.schemas import (
    CrawlerStartRequest,
    CrawlerTypeEnum,
    LoginTypeEnum,
    PlatformEnum,
)
from api.services.crawler_manager import CrawlerManager
from media_platform.douyin.state import DouyinCrawlState


def _write_csv(path, rows):
    lines = ["抖音主页链接,医生姓名,所在医院"]
    for url, name, hospital in rows:
        lines.append(f"{url},{name},{hospital}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_load_doctors_reads_csv(tmp_path, monkeypatch):
    csv_file = tmp_path / "doctors.csv"
    _write_csv(csv_file, [
        ("https://www.douyin.com/user/MS4wLjABAAAAaaa", "刘忠华", "七台河七煤医院"),
        ("https://www.douyin.com/user/MS4wLjABAAAAbbb", "冯霞", "三六三医院"),
    ])
    monkeypatch.setattr(doctor, "DOCTOR_CSV_PATH", csv_file)

    doctors = doctor.load_doctors()

    assert doctors == [
        {
            "name": "刘忠华",
            "hospital": "七台河七煤医院",
            "url": "https://www.douyin.com/user/MS4wLjABAAAAaaa",
        },
        {
            "name": "冯霞",
            "hospital": "三六三医院",
            "url": "https://www.douyin.com/user/MS4wLjABAAAAbbb",
        },
    ]


def test_crawl_endpoint_maps_name_to_url(tmp_path, monkeypatch):
    csv_file = tmp_path / "doctors.csv"
    _write_csv(csv_file, [("https://www.douyin.com/user/MS4wLjABAAAAaaa", "刘忠华", "七台河七煤医院")])
    monkeypatch.setattr(doctor, "DOCTOR_CSV_PATH", csv_file)

    client = TestClient(app)
    with patch("api.routers.doctor.crawler_manager.start", new_callable=AsyncMock) as mock_start:
        mock_start.return_value = True
        resp = client.post("/api/doctors/crawl", json={"doctor_name": "刘忠华", "video_count": 5})

    assert resp.status_code == 200
    mock_start.assert_awaited_once()
    req = mock_start.await_args[0][0]
    assert req.crawler_type == CrawlerTypeEnum.CREATOR
    assert req.creator_ids == "https://www.douyin.com/user/MS4wLjABAAAAaaa"
    assert req.max_creator_notes_count == 5
    assert req.enable_comments is False


def test_crawl_endpoint_unknown_doctor_returns_404(tmp_path, monkeypatch):
    csv_file = tmp_path / "doctors.csv"
    _write_csv(csv_file, [("https://www.douyin.com/user/MS4wLjABAAAAaaa", "刘忠华", "七台河七煤医院")])
    monkeypatch.setattr(doctor, "DOCTOR_CSV_PATH", csv_file)

    client = TestClient(app)
    resp = client.post("/api/doctors/crawl", json={"doctor_name": "不存在", "video_count": 5})

    assert resp.status_code == 404
    assert "不存在" in resp.json()["detail"]


def test_build_command_emits_creator_max_count():
    manager = CrawlerManager()
    req = CrawlerStartRequest(
        platform=PlatformEnum.DOUYIN,
        login_type=LoginTypeEnum.QRCODE,
        crawler_type=CrawlerTypeEnum.CREATOR,
        creator_ids="MS4wLjABAAAAaaa",
        enable_comments=False,
        max_creator_notes_count=5,
    )

    cmd = manager._build_command(req)

    assert "--crawler_max_creator_notes_count" in cmd
    assert cmd[cmd.index("--crawler_max_creator_notes_count") + 1] == "5"
    assert "--creator_id" in cmd


def test_crawl_state_roundtrip_and_dedup(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SAVE_DATA_PATH", str(tmp_path))

    state = DouyinCrawlState()
    assert state.crawled_ids == set()

    state.mark_crawled(["aweme-1", "aweme-2"], sec_user_id="sec-uid-a")
    state.mark_crawled(["aweme-2"], sec_user_id="sec-uid-a")  # 重复标记不落盘

    reloaded = DouyinCrawlState()
    assert reloaded.crawled_ids == {"aweme-1", "aweme-2"}

    state_file = tmp_path / "douyin" / "state" / "crawled_aweme_ids.jsonl"
    lines = [json.loads(line) for line in state_file.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2
    assert lines[0]["sec_user_id"] == "sec-uid-a"
    assert isinstance(lines[0]["crawled_at"], int)


def test_crawl_state_tolerates_broken_last_line(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SAVE_DATA_PATH", str(tmp_path))

    state_file = tmp_path / "douyin" / "state" / "crawled_aweme_ids.jsonl"
    state_file.parent.mkdir(parents=True)
    state_file.write_text(
        '{"aweme_id": "ok-1", "sec_user_id": "u", "crawled_at": 1}\n{"aweme_id": "bro',
        encoding="utf-8",
    )

    state = DouyinCrawlState()
    assert state.crawled_ids == {"ok-1"}
