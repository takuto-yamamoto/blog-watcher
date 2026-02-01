from __future__ import annotations

from tests.test_utils.strategies.html import html_strategy, html_with_links_strategy, random_html
from tests.test_utils.strategies.url import (
    url_lists,
    url_strategy,
    url_with_tracking_params_strategy,
)
from tests.test_utils.strategies.xml import xml_strategy

__all__ = [
    "html_strategy",
    "html_with_links_strategy",
    "random_html",
    "url_lists",
    "url_strategy",
    "url_with_tracking_params_strategy",
    "xml_strategy",
]
