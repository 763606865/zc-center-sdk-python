from __future__ import annotations

from zc_center.crypto import Crypto


def test_canonical_request_matches_thinkphp_fixture() -> None:
    crypto = Crypto()
    query = {"z": "最后", "a": "first value"}
    body = '{"echo":"hello"}'
    canonical = crypto.canonical_request(
        "post",
        "/sapi/ping",
        query,
        "1787823238",
        "g3N4RKzB9QMHYVqE4-ug_SDl",
        body,
    )
    expected = (
        "POST\n/sapi/ping\na=first%20value&z=%E6%9C%80%E5%90%8E\n"
        "1787823238\ng3N4RKzB9QMHYVqE4-ug_SDl\n"
        + crypto.sha256_hex(body)
    )
    assert canonical == expected


def test_aes_gcm_round_trip() -> None:
    crypto = Crypto()
    secret = "sdk-test-secret"
    aad = crypto.aad("sdk-test-app-key", "1787823238", "g3N4RKzB9QMHYVqE4-ug_SDl")
    payload = {"hello": "世界"}

    envelope = crypto.encrypt(payload, secret, aad)
    decrypted = crypto.decrypt(envelope, secret, aad)
    assert decrypted == payload

    signature = crypto.sign(
        "\n".join(
            [
                "1787823238",
                "g3N4RKzB9QMHYVqE4-ug_SDl",
                envelope["iv"],
                envelope["tag"],
                envelope["ciphertext"],
            ]
        ),
        secret,
    )
    assert crypto.verify_encrypted_response(
        envelope, signature, "1787823238", "g3N4RKzB9QMHYVqE4-ug_SDl", secret
    )
