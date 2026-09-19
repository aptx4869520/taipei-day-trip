"""Part 7 MCP transport and the two assignment tools."""
import os
from urllib.parse import urlsplit
from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from member_tokens import get_mcp_user_id
from trip_services import BookingInput, get_attractions, save_booking

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
parsed_url = urlsplit(PUBLIC_BASE_URL)
if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc or parsed_url.username or parsed_url.query or parsed_url.fragment or parsed_url.path not in {"", "/"}:
    raise RuntimeError("PUBLIC_BASE_URL 必須為網站的 http/https 網址")
mcp = MCPServer("台北一日遊")


@mcp.tool(name="搜尋台北市景點", description="透過關鍵字和捷運站名搜尋台北市一日旅遊的景點")
async def search_attractions(keyword: str) -> dict:
    try:
        data = []
        page = 0
        while True:
            result = await get_attractions(page, keyword)
            if isinstance(result, JSONResponse):
                return {"error": True}
            data.extend({key: row[key] for key in ("id", "name", "description")} for row in result["data"])
            page = result["nextPage"]
            if page is None:
                return {"data": data}
    except Exception:
        return {"error": True}


@mcp.tool(name="預定景點導覽行程", description="根據景點編號、日期、時間、價格，預定一個景點導覽行程")
async def add_to_cart(attractionId: int, date: str, time: str, price: int, ctx: Context) -> dict:
    try:
        user_id = await run_in_threadpool(get_mcp_user_id, (ctx.headers or {}).get("authorization"))
        if user_id is None:
            return {"error": True}
        booking = BookingInput(attractionId=attractionId, date=date, time=time, price=price)
        result = await save_booking(user_id, booking)
        if isinstance(result, JSONResponse):
            return {"error": True}
        return {"ok": True, "message": f"台北導覽行程，預定成功，請到 {PUBLIC_BASE_URL}/booking 完成付款。"}
    except Exception:
        return {"error": True}


class BearerAuthentication:
    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            authorization = headers.get(b"authorization", b"").decode("latin-1")
            try:
                user_id = await run_in_threadpool(get_mcp_user_id, authorization)
            except Exception:
                await JSONResponse({"error": True}, status_code=503)(scope, receive, send)
                return
            if user_id is None:
                await JSONResponse({"error": True}, status_code=401, headers={"WWW-Authenticate": "Bearer"})(scope, receive, send)
                return
        await self.application(scope, receive, send)


mcp_app = BearerAuthentication(mcp.streamable_http_app(
    streamable_http_path="/", json_response=True, stateless_http=True,
    transport_security=TransportSecuritySettings(
        allowed_hosts=["127.0.0.1:*", "localhost:*", parsed_url.netloc],
        allowed_origins=["http://127.0.0.1:*", "http://localhost:*", PUBLIC_BASE_URL],
    ),
))
