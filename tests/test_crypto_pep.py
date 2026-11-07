import base64
import os

from closer.services.crypto import FieldCipher
from closer.services.pep import load_pep_offer


def test_field_cipher_roundtrip():
    key = base64.b64encode(os.urandom(32)).decode()
    c = FieldCipher(key)
    blob = c.encrypt("4510 123456")
    assert c.decrypt(blob) == "4510 123456"


def test_pep_sha_stable():
    offer = load_pep_offer()
    assert offer.version
    assert len(offer.sha256) == 64
