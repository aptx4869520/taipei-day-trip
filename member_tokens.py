"""MCP tokens are separate from website login JWTs; only hashes are stored."""
import hashlib
import secrets
from database import get_connection


def rotate_member_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode()).hexdigest()
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO member_tokens (user_id, token_hash) VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE token_hash = VALUES(token_hash)
        """, (user_id, digest))
        connection.commit()
        return token
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def get_mcp_user_id(authorization: str | None) -> int | None:
    scheme, separator, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not separator or not token or len(token) > 256:
        return None
    digest = hashlib.sha256(token.encode()).hexdigest()
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT member_tokens.user_id FROM member_tokens
            INNER JOIN users ON users.id = member_tokens.user_id
            WHERE token_hash = %s
        """, (digest,))
        row = cursor.fetchone()
        return int(row[0]) if row else None
    finally:
        cursor.close()
        connection.close()
