"""Run against local development MySQL; test rows always roll back."""
import asyncio
import json
import secrets
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx2
import app
import member_tokens
import trip_services
from database import get_connection

async def main():
    connection=get_connection(); cursor=connection.cursor();connection.start_transaction()
    class TransactionConnection:
        def cursor(self, **kwargs): return connection.cursor(**kwargs)
        def commit(self): pass
        def rollback(self): pass
        def close(self): pass
        def is_connected(self): return True
    try:
        cursor.execute('INSERT INTO users(name,email,password) VALUES(%s,%s,%s)',('MCP test',secrets.token_hex(16)+'@example.invalid','not-a-login-password'))
        user_id=cursor.lastrowid
        with patch.object(member_tokens,'get_connection',return_value=TransactionConnection()),patch.object(trip_services,'get_connection',return_value=TransactionConnection()):
            token=member_tokens.rotate_member_token(user_id)
            headers={'Authorization':'Bearer '+token,'Accept':'application/json, text/event-stream','MCP-Protocol-Version':'2025-06-18'}
            async with app.lifespan(app.app):
                async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app.app),base_url='http://127.0.0.1:8000') as client:
                    response=await client.post('/mcp/',json={'jsonrpc':'2.0','id':1,'method':'tools/list'})
                    assert response.status_code==401
                    async def rpc(method,params=None):
                        response=await client.post('/mcp/',headers=headers,json={'jsonrpc':'2.0','id':1,'method':method,'params':params or {}})
                        assert response.status_code==200,(response.status_code,response.text)
                        data=response.json();assert 'error' not in data,data
                        return data['result']
                    result=await rpc('initialize',{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'part7-test','version':'1'}})
                    assert result['serverInfo']['name']=='台北一日遊'
                    result=await rpc('tools/list')
                    assert {t['name'] for t in result['tools']}=={'搜尋台北市景點','預定景點導覽行程'}
                    async def call(name,arguments):
                        result=await rpc('tools/call',{'name':name,'arguments':arguments})
                        assert not result.get('isError'),result
                        return result.get('structuredContent') or json.loads(result['content'][0]['text'])
                    result=await call('搜尋台北市景點',{'keyword':'北投'})
                    assert result['data'] and all({'id','name','description'}<=row.keys() for row in result['data'])
                    attraction_id=result['data'][0]['id']
                    expected=[]; page=0
                    while page is not None:
                        data=await trip_services.get_attractions(page,'北投');expected.extend(row['id'] for row in data['data']);page=data['nextPage']
                    assert [row['id'] for row in result['data']]==expected
                    assert (await call('搜尋台北市景點',{'keyword':'no-such-place-7x9'}))=={'data':[]}
                    args={'attractionId':attraction_id,'date':'2026-10-01','time':'morning','price':2000}
                    result=await call('預定景點導覽行程',args)
                    assert result['ok'] and '/booking' in result['message']
                    cursor.execute('SELECT attraction_id,time,price FROM bookings WHERE user_id=%s',(user_id,));assert cursor.fetchone()==(attraction_id,'morning',2000)
                    for invalid in [dict(args,price=2500),dict(args,date='invalid'),dict(args,attractionId=-1),dict(args,time='晚上')]:
                        assert await call('預定景點導覽行程',invalid)=={'error':True}
                    cursor.execute('SELECT time,price FROM bookings WHERE user_id=%s',(user_id,));assert cursor.fetchone()==('morning',2000)
                    login=app.create_access_token(user_id,'MCP test','test@example.invalid')
                    response=await client.post('/api/booking',headers={'Authorization':'Bearer '+login},json=dict(args,time='afternoon',price=2500))
                    assert response.status_code==200
                    cursor.execute('SELECT time,price FROM bookings WHERE user_id=%s',(user_id,));assert cursor.fetchone()==('afternoon',2500)
                    member_tokens.rotate_member_token(user_id)
                    response=await client.post('/mcp/',headers=headers,json={'jsonrpc':'2.0','id':1,'method':'tools/list'});assert response.status_code==401
                    print('PASS: MCP initialize/list/call, exact tool names, complete search parity, no results, booking persistence, input errors, shared website booking, rotated-token 401')
    finally:
        connection.rollback();cursor.close();connection.close();print('All test rows rolled back.')
asyncio.run(main())
