from blog_watcher.detection.urls.extractor import ExtractionConfig, extract_urls
from blog_watcher.detection.urls.fingerprinter import fingerprint_urls, has_changed
from blog_watcher.detection.urls.html_parser import parse_html
from blog_watcher.detection.urls.normalizer import NormalizationConfig, normalize_url, normalize_urls

__all__ = [
    "ExtractionConfig",
    "NormalizationConfig",
    "extract_urls",
    "fingerprint_urls",
    "has_changed",
    "normalize_url",
    "normalize_urls",
    "parse_html",
]
