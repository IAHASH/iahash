from iahash.crypto import normalise, sha256_hex


def test_normalise_converts_newlines_and_trims_spaces():
    raw = "Linea 1  \r\nLinea 2\rLinea 3   \n"
    normalised = normalise(raw)
    assert normalised == b"Linea 1\nLinea 2\nLinea 3"


def test_sha256_hex_known_vector():
    assert sha256_hex(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
