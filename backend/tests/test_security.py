from app.core.security import hash_password, verify_password


def test_hash_password_does_not_store_the_plaintext() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert "correct horse battery staple" not in password_hash
    assert password_hash.startswith("$argon2id$")


def test_verify_password_accepts_the_original_password() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert verify_password(password="correct horse battery staple", password_hash=password_hash)


def test_verify_password_rejects_a_wrong_password() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert not verify_password(password="wrong password", password_hash=password_hash)


def test_verify_password_rejects_a_malformed_hash() -> None:
    assert not verify_password(password="anything", password_hash="not-a-real-hash")


def test_hash_password_is_salted_and_produces_different_hashes_each_time() -> None:
    first = hash_password("same password")
    second = hash_password("same password")

    assert first != second
