import asyncio
import json
import secrets
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app
import member_tokens
from database import get_connection
from starlette.requests import Request

def request(token=None):
    return Request({'type':'http','method':'POST','path':'/api/member/token','headers':[(b'authorization', ('Bearer '+token).encode())] if token else []})

async def run():
    response = await app.generate_member_token(request())
    assert response.status_code == 403
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute('SHOW CREATE TABLE member_tokens')
    assert 'token_hash' in cursor.fetchone()[1]
    connection.commit()
    connection.start_transaction()
    class TransactionConnection:
        def cursor(self): return connection.cursor()
        def commit(self): pass
        def rollback(self): pass
        def close(self): pass
    try:
        ids=[]
        for _ in range(2):
            cursor.execute('INSERT INTO users(name,email,password) VALUES(%s,%s,%s)',('Part7 test', secrets.token_hex(16)+'@example.invalid','not-a-login-password'))
            ids.append(cursor.lastrowid)
        with patch.object(member_tokens,'get_connection',return_value=TransactionConnection()):
            first=member_tokens.rotate_member_token(ids[0])
            assert member_tokens.get_mcp_user_id('Bearer '+first)==ids[0]
            second=member_tokens.rotate_member_token(ids[0])
            assert first!=second
            assert member_tokens.get_mcp_user_id('Bearer '+first) is None
            assert member_tokens.get_mcp_user_id('Bearer '+second)==ids[0]
            other=member_tokens.rotate_member_token(ids[1])
            assert member_tokens.get_mcp_user_id('Bearer '+other)==ids[1]
            assert member_tokens.get_mcp_user_id('Bearer invalid') is None
            assert member_tokens.get_mcp_user_id(None) is None
            login=app.create_access_token(ids[0],'Part7 test','test@example.invalid')
            assert member_tokens.get_mcp_user_id('Bearer '+login) is None
            assert app.decode_access_token(second) is None
            response=await app.generate_member_token(request(login))
            assert response.status_code==200
            assert response.headers['cache-control']=='no-store'
            assert member_tokens.get_mcp_user_id('Bearer '+json.loads(response.body)['token'])==ids[0]
            cursor.execute('SELECT token_hash FROM member_tokens WHERE user_id=%s',(ids[0],))
            digest=cursor.fetchone()[0]
            assert len(digest)==64 and digest!=second
        print('PASS: real MySQL rotation, old-token rejection, member isolation, invalid-token rejection, JWT/MCP separation, authenticated token API, no-store, hash-only storage, unauthenticated 403')
    finally:
        connection.rollback()
        cursor.close()
        connection.close()
        print('Test rows rolled back.')
asyncio.run(run())
