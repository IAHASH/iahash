from iahash.crypto import normalise, sha256_hex


def test_normalise_strips_crlf_and_trailing_spaces():
    original = "hola\r\nque tal  \r\n"
    normalised = normalise(original)
    assert normalised == b"hola\nque tal\n"


def test_sha256_hex_matches_expected():
    assert sha256_hex(b"test") == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
