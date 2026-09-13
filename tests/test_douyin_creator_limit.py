# -*- coding: utf-8 -*-

import pytest

import config
from cmd_arg import parse_cmd
from media_platform.douyin.client import DouYinClient


def _build_pages():
    """Three pages chained by max_cursor, two posts per page."""
    def _page(aweme_ids, has_more, next_cursor):
        return {
            "has_more": has_more,
            "max_cursor": next_cursor,
            "aweme_list": [{"aweme_id": aweme_id} for aweme_id in aweme_ids],
        }

    return {
        "": _page(["1", "2"], 1, "10"),
        "10": _page(["3", "4"], 1, "20"),
        "20": _page(["5", "6"], 0, "20"),
    }


def _build_client(pages, requested_cursors):
    client = DouYinClient(headers={}, playwright_page=None, cookie_dict={})

    async def fake_get_user_aweme_posts(sec_user_id, max_cursor=""):
        requested_cursors.append(max_cursor)
        return pages[max_cursor]

    client.get_user_aweme_posts = fake_get_user_aweme_posts
    return client


@pytest.mark.asyncio
async def test_default_max_count_crawls_all_pages():
    pages = _build_pages()
    cursors = []
    client = _build_client(pages, cursors)

    result = await client.get_all_user_aweme_posts("sec_uid")

    assert [post["aweme_id"] for post in result] == ["1", "2", "3", "4", "5", "6"]
    assert cursors == ["", "10", "20"]


@pytest.mark.asyncio
async def test_explicit_zero_max_count_crawls_all_pages():
    pages = _build_pages()
    cursors = []
    client = _build_client(pages, cursors)
    batches = []

    async def callback(posts):
        batches.append([post["aweme_id"] for post in posts])

    result = await client.get_all_user_aweme_posts("sec_uid", callback=callback, max_count=0)

    assert [post["aweme_id"] for post in result] == ["1", "2", "3", "4", "5", "6"]
    assert cursors == ["", "10", "20"]
    assert batches == [["1", "2"], ["3", "4"], ["5", "6"]]


@pytest.mark.asyncio
async def test_max_count_truncates_across_pages_before_callback():
    pages = _build_pages()
    cursors = []
    client = _build_client(pages, cursors)
    batches = []

    async def callback(posts):
        batches.append([post["aweme_id"] for post in posts])

    result = await client.get_all_user_aweme_posts("sec_uid", callback=callback, max_count=3)

    assert [post["aweme_id"] for post in result] == ["1", "2", "3"]
    assert cursors == ["", "10"]
    assert batches == [["1", "2"], ["3"]]


@pytest.mark.asyncio
async def test_max_count_within_first_page_fetches_single_page():
    pages = _build_pages()
    cursors = []
    client = _build_client(pages, cursors)
    batches = []

    async def callback(posts):
        batches.append([post["aweme_id"] for post in posts])

    result = await client.get_all_user_aweme_posts("sec_uid", callback=callback, max_count=1)

    assert [post["aweme_id"] for post in result] == ["1"]
    assert cursors == [""]
    assert batches == [["1"]]


@pytest.mark.asyncio
async def test_max_count_larger_than_total_crawls_everything():
    pages = _build_pages()
    cursors = []
    client = _build_client(pages, cursors)

    result = await client.get_all_user_aweme_posts("sec_uid", max_count=100)

    assert len(result) == 6
    assert cursors == ["", "10", "20"]


@pytest.mark.asyncio
async def test_cmd_arg_writes_crawler_max_creator_notes_count():
    original = config.CRAWLER_MAX_CREATOR_NOTES_COUNT
    try:
        await parse_cmd(["--platform", "dy", "--crawler_max_creator_notes_count", "20"])
        assert config.CRAWLER_MAX_CREATOR_NOTES_COUNT == 20
    finally:
        config.CRAWLER_MAX_CREATOR_NOTES_COUNT = original


def _page(aweme_ids, has_more, next_cursor):
    return {
        "has_more": has_more,
        "max_cursor": next_cursor,
        "aweme_list": [{"aweme_id": aweme_id} for aweme_id in aweme_ids],
    }


@pytest.mark.asyncio
async def test_skip_ids_stops_when_full_page_already_crawled():
    pages = {
        "": _page(["old-1", "old-2"], 1, "10"),
        "10": _page(["new-1"], 0, "10"),
    }
    cursors = []
    client = _build_client(pages, cursors)

    result = await client.get_all_user_aweme_posts("sec_uid", skip_ids={"old-1", "old-2"})

    assert result == []
    assert cursors == [""]  # 整页都是旧作品，视为已到上次抓取边界，不再翻页


@pytest.mark.asyncio
async def test_skip_ids_with_max_count_counts_new_items_only():
    pages = {
        "": _page(["1", "2"], 1, "10"),
        "10": _page(["3", "4"], 1, "20"),
        "20": _page(["5", "6"], 0, "20"),
    }
    skip_ids = {"1", "3", "5"}  # 每页各有一条旧作品
    cursors = []
    client = _build_client(pages, cursors)

    result = await client.get_all_user_aweme_posts("sec_uid", max_count=2, skip_ids=skip_ids)

    assert [post["aweme_id"] for post in result] == ["2", "4"]  # 数量按新作品计
    assert cursors == ["", "10"]
