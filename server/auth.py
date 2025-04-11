# auth.py

# Danh sách token hợp lệ
VALID_TOKENS = {
    "123456",
    "abcdef",
    "token_xyz"
}

def verify_token(token: str) -> bool:
    """
    Kiểm tra token có hợp lệ không.
    """
    return token in VALID_TOKENS
