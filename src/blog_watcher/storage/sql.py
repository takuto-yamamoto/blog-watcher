from __future__ import annotations

from pathlib import Path


def _read_sql(relative_path: str) -> str:
    return (Path(__file__).resolve().parent / "sql" / relative_path).read_text(encoding="utf-8")


SCHEMA_SQL = _read_sql("schema.sql")

BLOG_STATE_GET_SQL = _read_sql("blog_state/get.sql")
BLOG_STATE_LIST_ALL_SQL = _read_sql("blog_state/list_all.sql")
BLOG_STATE_UPSERT_SQL = _read_sql("blog_state/upsert.sql")
BLOG_STATE_DELETE_SQL = _read_sql("blog_state/delete.sql")

CHECK_HISTORY_ADD_SQL = _read_sql("check_history/add.sql")
CHECK_HISTORY_LIST_BY_BLOG_ID_SQL = _read_sql("check_history/list_by_blog_id.sql")

__all__ = [
    "BLOG_STATE_DELETE_SQL",
    "BLOG_STATE_GET_SQL",
    "BLOG_STATE_LIST_ALL_SQL",
    "BLOG_STATE_UPSERT_SQL",
    "CHECK_HISTORY_ADD_SQL",
    "CHECK_HISTORY_LIST_BY_BLOG_ID_SQL",
    "SCHEMA_SQL",
]
