"""Shared attraction search and booking logic for website and MCP."""
from datetime import date
from typing import Any, Literal, cast
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from database import get_connection

class BookingInput(BaseModel):
    attractionId: int
    date: date
    time: Literal["morning", "afternoon"]
    price: Literal[2000, 2500]


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


async def get_attractions(
    page: int,
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

async def save_booking(
    user_id: int,
    booking_data: BookingInput,
):
    connection = None
    cursor = None

    try:
        expected_price = 2000 if booking_data.time == "morning" else 2500
        if booking_data.price != expected_price:
            return JSONResponse(status_code=400, content={"error": True, "message": "時段與價格不符"})

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
