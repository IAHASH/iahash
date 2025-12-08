import pytest

from api.main import CHATGPT_SHARE_PATTERN
from iahash.extractors.chatgpt_share import _validate_share_url
from iahash.extractors.exceptions import InvalidShareURL


@pytest.mark.parametrize(
    "url",
    [
        "https://chatgpt.com/share/6935bbc0-3fc4-8001-b6fa-b57c687905a8",
        "https://chat.openai.com/share/6935bbc0-3fc4-8001-b6fa-b57c687905a8",
        "https://chatgpt.com/share/6935bbc0-3fc4-8001-b6fa-b57c687905a8/",
        "https://chatgpt.com/share/6935bbc0-3fc4-8001-b6fa-b57c687905a8?utm=test",
        "http://chatgpt.com/share/6935bbc0-3fc4-8001-b6fa-b57c687905a8",
        "https://www.chat.openai.com/share/6935bbc0-3fc4-8001-b6fa-b57c687905a8",
    ],
)
def test_chatgpt_share_pattern_accepts_valid_urls(url):
    assert CHATGPT_SHARE_PATTERN.match(url)
    _validate_share_url(url)  # Does not raise


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/share/6935bbc0-3fc4-8001-b6fa-b57c687905a8",
        "https://chat.openai.com/other/6935bbc0-3fc4-8001-b6fa-b57c687905a8",
        "https://chatgpt.com/share/",
    ],
)
def test_chatgpt_share_pattern_rejects_invalid_urls(url):
    assert not CHATGPT_SHARE_PATTERN.match(url)
    with pytest.raises(InvalidShareURL):
        _validate_share_url(url)
