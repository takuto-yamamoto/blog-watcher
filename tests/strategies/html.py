"""HTML-related Hypothesis strategies."""

from __future__ import annotations

from hypothesis import strategies as st


@st.composite
def html_with_links_strategy(draw: st.DrawFn) -> str:
    return draw(st.text(min_size=0, max_size=500))


@st.composite
def html_strategy(draw: st.DrawFn) -> str:
    tags = draw(st.lists(st.sampled_from(["<div>", "</div>", "<a>", "</a>", "<p>", "</p>", "text"]), max_size=50))
    return "".join(tags)


random_html = st.text(min_size=0, max_size=500)
