from app.auth import create_token, is_public_path, password_ok, verify_token

S, P = "secret", "hunter2"


def test_valid_token_roundtrip():
    assert verify_token(create_token(S, P, now=1000), S, P, now=1001)


def test_expired_token_rejected():
    tok = create_token(S, P, now=1000)
    assert not verify_token(tok, S, P, now=1000 + 8 * 24 * 3600)


def test_tampered_or_garbage_tokens_rejected():
    tok = create_token(S, P, now=1000)
    exp, sig = tok.split(".")
    assert not verify_token(f"{int(exp) + 99999}.{sig}", S, P, now=1001)  # extended expiry
    assert not verify_token(tok, "other-secret", P, now=1001)
    assert not verify_token(tok, S, "other-password", now=1001)  # changing the password logs everyone out
    for bad in (None, "", "abc", "x.y", "123"):
        assert not verify_token(bad, S, P, now=1001)


def test_password_check():
    assert password_ok("hunter2", "hunter2")
    assert not password_ok("hunter3", "hunter2")
    assert password_ok("كلمة", "كلمة")


def test_public_paths():
    for p in ("/", "/health", "/dashboard", "/dashboard/app.js", "/media/videos/a.mp4", "/auth/login"):
        assert is_public_path(p), p
    for p in ("/schedule", "/niches", "/content/ideas", "/docs", "/dashboardx", "/mediafoo", "/stats"):
        assert not is_public_path(p), p
