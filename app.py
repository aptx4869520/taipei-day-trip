import base64
import hashlib
import hmac
import os
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal, cast

import jwt
from fastapi import FastAPI, Query, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from mysql.connector import IntegrityError
from pydantic import BaseModel, EmailStr

from database import get_connection


app = FastAPI()


JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 7
PASSWORD_ITERATIONS = 600_000


class UserSignUpInput(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserSignInInput(BaseModel):
    email: EmailStr
    password: str


class BookingInput(BaseModel):
    attractionId: int
    date: date
    time: Literal["morning", "afternoon"]
    price: Literal[2000, 2500]


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )

    encoded_salt = base64.b64encode(salt).decode("ascii")
    encoded_hash = base64.b64encode(password_hash).decode("ascii")

    return (
        f"pbkdf2_sha256"
        f"${PASSWORD_ITERATIONS}"
        f"${encoded_salt}"
        f"${encoded_hash}"
    )


def verify_password(
    password: str,
    stored_password: str,
) -> bool:
    try:
        algorithm, iterations, encoded_salt, encoded_hash = (
            stored_password.split("$", 3)
        )

        if algorithm != "pbkdf2_sha256":
            return False

        salt = base64.b64decode(encoded_salt)
        expected_hash = base64.b64decode(encoded_hash)

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )

        return hmac.compare_digest(
            actual_hash,
            expected_hash,
        )

    except (ValueError, TypeError):
        return False


def create_access_token(
    user_id: int,
    name: str,
    email: str,
) -> str:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET 尚未設定")

    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(
        days=JWT_EXPIRATION_DAYS
    )

    payload = {
        "id": user_id,
        "name": name,
        "email": email,
        "iat": issued_at,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(
    token: str,
) -> dict[str, Any] | None:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET 尚未設定")

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={
                "require": [
                    "id",
                    "name",
                    "email",
                    "iat",
                    "exp",
                ],
            },
        )

        if (
            not isinstance(payload.get("id"), int)
            or not isinstance(payload.get("name"), str)
            or not isinstance(payload.get("email"), str)
        ):
            return None

        return payload

    except jwt.PyJWTError:
        return None


def get_authenticated_user_id(
    request: Request,
) -> int | None:
    authorization = request.headers.get(
        "Authorization"
    )

    if not authorization:
        return None

    scheme, separator, token = authorization.partition(" ")

    if (
        scheme.lower() != "bearer"
        or not separator
        or not token
    ):
        return None

    payload = decode_access_token(token)

    if payload is None:
        return None

    user_id = payload.get("id")

    if not isinstance(user_id, int):
        return None

    return user_id


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request,
    error: RequestValidationError,
):
    if request.url.path.startswith("/api/attraction/"):
        return JSONResponse(
            status_code=400,
            content={
                "error": True,
                "message": "景點編號不正確",
            },
        )

    if request.url.path in {
        "/api/user",
        "/api/user/auth",
        "/api/booking",
    }:
        return JSONResponse(
            status_code=400,
            content={
                "error": True,
                "message": "輸入資料不正確",
            },
        )

    return await request_validation_exception_handler(
        request,
        error,
    )


#------------------------------

# Static Pages (Never Modify Code in this Block)
@app.get("/", include_in_schema=False)
async def index(request: Request):
	return FileResponse("./static/index.html", media_type="text/html")
@app.get("/attraction/{id}", include_in_schema=False)
async def attraction(request: Request, id: int):
	return FileResponse("./static/attraction.html", media_type="text/html")
@app.get("/booking", include_in_schema=False)
async def booking(request: Request):
	return FileResponse("./static/booking.html", media_type="text/html")
@app.get("/thankyou", include_in_schema=False)
async def thankyou(request: Request):
	return FileResponse("./static/thankyou.html", media_type="text/html"	)

# ------------------------------


app.mount("/static", StaticFiles(directory="static"), name="static")


PAGE_SIZE = 8


def format_attraction(
	row: dict[str, Any],
    images: list[str],
) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "description": row["description"],
        "address": row["address"],
        "transport": row["transport"],
        "mrt": row["mrt"],
        "lat": float(row["lat"]),
        "lng": float(row["lng"]),
        "images": images,
    }


@app.get("/api/attractions")
async def get_attractions(
    page: int = Query(..., ge=0),
    keyword: str | None = None,
    category: str | None = None,
):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        conditions: list[str] = []
        parameters: list[Any] = []

        if category:
            conditions.append("category = %s")
            parameters.append(category)

        if keyword:
            conditions.append("(mrt = %s OR name LIKE %s)")
            parameters.append(keyword)
            parameters.append(f"%{keyword}%")

        where_clause = ""

        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        offset = page * PAGE_SIZE

        attraction_query = f"""
            SELECT
                id,
                name,
                category,
                description,
                address,
                transport,
                mrt,
                lat,
                lng
            FROM attractions
            {where_clause}
            ORDER BY id
            LIMIT %s OFFSET %s
        """

        query_parameters = parameters + [
            PAGE_SIZE + 1,
            offset,
        ]

        cursor.execute(
            attraction_query,
            query_parameters,
        )

        rows = cast(
            list[dict[str, Any]],
  			cursor.fetchall(),
		)

        has_next_page = len(rows) > PAGE_SIZE

        rows = rows[:PAGE_SIZE]

        attraction_ids = [
            row["id"]
            for row in rows
        ]

        images_by_attraction = {
            attraction_id: []
            for attraction_id in attraction_ids
        }

        if attraction_ids:
            placeholders = ", ".join(
                ["%s"] * len(attraction_ids)
            )

            image_query = f"""
                SELECT
                    attraction_id,
                    image_url
                FROM attraction_images
                WHERE attraction_id IN ({placeholders})
                ORDER BY attraction_id, image_order
            """

            cursor.execute(
                image_query,
                tuple(attraction_ids),
            )

            image_rows = cast(
                list[dict[str, Any]],
                cursor.fetchall(),
            )

            for image_row in image_rows:
                attraction_id = image_row["attraction_id"]
                image_url = image_row["image_url"]

                images_by_attraction[attraction_id].append(
                    image_url
                )

        data = []

        for row in rows:
            attraction_id = row["id"]

            attraction = format_attraction(
                row,
                images_by_attraction[attraction_id],
            )

            data.append(attraction)

        next_page = None

        if has_next_page:
            next_page = page + 1

        return {
            "nextPage": next_page,
            "data": data,
        }

    except Exception as error:
        print(
            "GET /api/attractions failed:",
            error,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "伺服器內部錯誤",
            },
        )

    finally:
        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()
            

@app.get("/api/attraction/{attraction_id}")
async def get_attraction(attraction_id: int):
    connection = None
    cursor = None

    try:
        if attraction_id < 1:
            return JSONResponse(
                status_code=400,
                content={
                    "error": True,
                    "message": "景點編號不正確",
                },
            )

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                name,
                category,
                description,
                address,
                transport,
                mrt,
                lat,
                lng
            FROM attractions
            WHERE id = %s
            """,
            (attraction_id,),
        )

        row = cast(
            dict[str, Any] | None,
            cursor.fetchone(),
        )

        if row is None:
            return JSONResponse(
                status_code=400,
                content={
                    "error": True,
                    "message": "景點編號不正確",
                },
            )

        cursor.execute(
            """
            SELECT image_url
            FROM attraction_images
            WHERE attraction_id = %s
            ORDER BY image_order
            """,
            (attraction_id,),
        )

        image_rows = cast(
            list[dict[str, Any]],
            cursor.fetchall(),
        )

        images = [
            image_row["image_url"]
            for image_row in image_rows
        ]

        return {
            "data": format_attraction(row, images)
        }

    except Exception as error:
        print(
            "GET /api/attraction/{attraction_id} failed:",
            error,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "伺服器內部錯誤",
            },
        )

    finally:
        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()


@app.get("/api/categories")
async def get_categories():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT DISTINCT category
            FROM attractions
            ORDER BY category
            """
        )

        rows = cast(
			list[tuple[str]],
			cursor.fetchall(),
		)

        categories = [
            row[0]
            for row in rows
        ]

        return {
            "data": categories
        }

    except Exception as error:
        print(
            "GET /api/categories failed:",
            error,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "伺服器內部錯誤",
            },
        )

    finally:
        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()


@app.get("/api/mrts")
async def get_mrts():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                mrt,
                COUNT(*) AS attraction_count,
                MIN(id) AS first_attraction_id
            FROM attractions
            WHERE mrt IS NOT NULL
            GROUP BY mrt
            ORDER BY
                attraction_count DESC,
                first_attraction_id ASC
            """
        )

        rows = cast(
            list[tuple[str, int, int]],
            cursor.fetchall(),
        )

        mrts = [
            row[0]
            for row in rows
        ]

        return {
            "data": mrts
        }

    except Exception as error:
        print(
            "GET /api/mrts failed:",
            error,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "伺服器內部錯誤",
            },
        )

    finally:
        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()


@app.post("/api/user")
async def sign_up_user(user: UserSignUpInput):
    connection = None
    cursor = None

    name = user.name.strip()
    email = str(user.email).strip().lower()
    password = user.password

    if not name or not password:
        return JSONResponse(
            status_code=400,
            content={
                "error": True,
                "message": "姓名、電子信箱和密碼不可為空",
            },
        )

    try:
        connection = get_connection()
        cursor = connection.cursor()

        password_hash = hash_password(password)

        cursor.execute(
            """
            INSERT INTO users (
                name,
                email,
                password
            )
            VALUES (%s, %s, %s)
            """,
            (
                name,
                email,
                password_hash,
            ),
        )

        connection.commit()

        return {
            "ok": True,
        }

    except IntegrityError:
        if connection is not None:
            connection.rollback()

        return JSONResponse(
            status_code=400,
            content={
                "error": True,
                "message": "此電子信箱已經註冊",
            },
        )

    except Exception as error:
        if connection is not None:
            connection.rollback()

        print(
            "POST /api/user failed:",
            error,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "伺服器內部錯誤",
            },
        )

    finally:
        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()


@app.put("/api/user/auth")
async def sign_in_user(user: UserSignInInput):
    connection = None
    cursor = None

    email = str(user.email).strip().lower()
    password = user.password

    if not password:
        return JSONResponse(
            status_code=400,
            content={
                "error": True,
                "message": "電子信箱和密碼不可為空",
            },
        )

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                password
            FROM users
            WHERE email = %s
            """,
            (email,),
        )

        row = cast(
            dict[str, Any] | None,
            cursor.fetchone(),
        )

        if (
            row is None
            or not verify_password(
                password,
                row["password"],
            )
        ):
            return JSONResponse(
                status_code=400,
                content={
                    "error": True,
                    "message": "電子信箱或密碼錯誤",
                },
            )

        token = create_access_token(
            user_id=row["id"],
            name=row["name"],
            email=row["email"],
        )

        return {
            "token": token,
        }

    except Exception as error:
        print(
            "PUT /api/user/auth failed:",
            error,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "伺服器內部錯誤",
            },
        )

    finally:
        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()


@app.get("/api/user/auth")
async def get_current_user(request: Request):
    authorization = request.headers.get(
        "Authorization"
    )

    if not authorization:
        return {
            "data": None,
        }

    scheme, separator, token = authorization.partition(" ")

    if (
        scheme.lower() != "bearer"
        or not separator
        or not token
    ):
        return {
            "data": None,
        }

    try:
        payload = decode_access_token(token)

        if payload is None:
            return {
                "data": None,
            }

        return {
            "data": {
                "id": payload["id"],
                "name": payload["name"],
                "email": payload["email"],
            },
        }

    except Exception as error:
        print(
            "GET /api/user/auth failed:",
            error,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "伺服器內部錯誤",
            },
        )


@app.post("/api/booking")
async def create_booking(
    request: Request,
    booking_data: BookingInput,
):
    connection = None
    cursor = None

    try:
        user_id = get_authenticated_user_id(request)

        if user_id is None:
            return JSONResponse(
                status_code=403,
                content={
                    "error": True,
                    "message": "未登入系統，拒絕存取",
                },
            )

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id
            FROM attractions
            WHERE id = %s
            """,
            (booking_data.attractionId,),
        )

        attraction = cursor.fetchone()

        if attraction is None:
            return JSONResponse(
                status_code=400,
                content={
                    "error": True,
                    "message": "景點編號不正確",
                },
            )

        cursor.execute(
            """
            INSERT INTO bookings (
                user_id,
                attraction_id,
                date,
                time,
                price
            )
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                attraction_id = VALUES(attraction_id),
                date = VALUES(date),
                time = VALUES(time),
                price = VALUES(price)
            """,
            (
                user_id,
                booking_data.attractionId,
                booking_data.date,
                booking_data.time,
                booking_data.price,
            ),
        )

        connection.commit()

        return {
            "ok": True,
        }

    except Exception as error:
        if connection is not None:
            connection.rollback()

        print(
            "POST /api/booking failed:",
            error,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "伺服器內部錯誤",
            },
        )

    finally:
        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()


@app.get("/api/booking")
async def get_booking(request: Request):
    connection = None
    cursor = None

    try:
        user_id = get_authenticated_user_id(request)

        if user_id is None:
            return JSONResponse(
                status_code=403,
                content={
                    "error": True,
                    "message": "未登入系統，拒絕存取",
                },
            )

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                bookings.date,
                bookings.time,
                bookings.price,
                attractions.id AS attraction_id,
                attractions.name AS attraction_name,
                attractions.address AS attraction_address,
                (
                    SELECT attraction_images.image_url
                    FROM attraction_images
                    WHERE
                        attraction_images.attraction_id
                        = attractions.id
                    ORDER BY attraction_images.image_order
                    LIMIT 1
                ) AS attraction_image
            FROM bookings
            INNER JOIN attractions
                ON attractions.id = bookings.attraction_id
            WHERE bookings.user_id = %s
            """,
            (user_id,),
        )

        row = cast(
            dict[str, Any] | None,
            cursor.fetchone(),
        )

        if row is None:
            return {
                "data": None,
            }

        return {
            "data": {
                "attraction": {
                    "id": row["attraction_id"],
                    "name": row["attraction_name"],
                    "address": row["attraction_address"],
                    "image": row["attraction_image"],
                },
                "date": row["date"].isoformat(),
                "time": row["time"],
                "price": row["price"],
            },
        }

    except Exception as error:
        print(
            "GET /api/booking failed:",
            error,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "伺服器內部錯誤",
            },
        )

    finally:
        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()


@app.delete("/api/booking")
async def delete_booking(request: Request):
    connection = None
    cursor = None

    try:
        user_id = get_authenticated_user_id(request)

        if user_id is None:
            return JSONResponse(
                status_code=403,
                content={
                    "error": True,
                    "message": "未登入系統，拒絕存取",
                },
            )

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM bookings
            WHERE user_id = %s
            """,
            (user_id,),
        )

        connection.commit()

        return {
            "ok": True,
        }

    except Exception as error:
        if connection is not None:
            connection.rollback()

        print(
            "DELETE /api/booking failed:",
            error,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "伺服器內部錯誤",
            },
        )

    finally:
        if cursor is not None:
            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):
            connection.close()
