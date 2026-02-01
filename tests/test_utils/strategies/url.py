from __future__ import annotations

from hypothesis import strategies as st


@st.composite
def url_strategy(draw: st.DrawFn) -> str:
    scheme = draw(st.sampled_from(["http", "https", "HTTP", "HTTPS"]))
    host = draw(st.from_regex(r"[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?", fullmatch=True))
    tld = draw(st.sampled_from(["com", "org", "net", "io", "dev"]))
    path = draw(st.one_of(st.just(""), st.from_regex(r"/[a-z0-9/_-]{0,50}", fullmatch=True)))
    query = draw(st.one_of(st.just(""), st.from_regex(r"\?[a-z0-9=&_-]{1,50}", fullmatch=True)))
    fragment = draw(st.one_of(st.just(""), st.from_regex(r"#[a-z0-9_-]{1,20}", fullmatch=True)))

    return f"{scheme}://{host}.{tld}{path}{query}{fragment}"


@st.composite
def url_with_tracking_params_strategy(draw: st.DrawFn) -> str:
    base_url = draw(url_strategy())
    separator = "&" if "?" in base_url else "?"
    tracking_params = ["utm_source=test", "utm_medium=email", "utm_campaign=spring", "fbclid=abc123", "gclid=xyz789", "mc_eid=test"]

    tracking_param = draw(st.sampled_from(tracking_params))

    return f"{base_url}{separator}{tracking_param}"


url_lists = st.lists(url_strategy(), min_size=0, max_size=20)
