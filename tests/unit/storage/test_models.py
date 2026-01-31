from __future__ import annotations

import pytest
from tests.factories.storage import BlogStateFactory


@pytest.mark.parametrize("blog_id", [""])
def test_blog_state_rejects_empty_blog_id(blog_id: str) -> None:
    with pytest.raises(ValueError, match="blog_id cannot be empty"):
        BlogStateFactory.build(blog_id=blog_id)


def test_blog_state_rejects_negative_consecutive_errors() -> None:
    with pytest.raises(ValueError, match="consecutive_errors cannot be negative"):
        BlogStateFactory.build(consecutive_errors=-1)
