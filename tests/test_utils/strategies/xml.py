from __future__ import annotations

from hypothesis import strategies as st


@st.composite
def xml_strategy(draw: st.DrawFn) -> str:
    sample_tags = ["<rss>", "</rss>", "<channel>", "</channel>", "<item>", "</item>", "text", "<![CDATA[content]]>"]
    tags = draw(st.lists(st.sampled_from(sample_tags), max_size=30))
    return "".join(tags)
