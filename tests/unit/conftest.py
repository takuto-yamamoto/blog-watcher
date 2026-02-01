from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def _no_sleep() -> Generator[None, None, None]:
    """Disable asyncio.sleep globally in unit tests to avoid real delays from retry backoff."""
    with patch("asyncio.sleep", new_callable=AsyncMock):
        yield
