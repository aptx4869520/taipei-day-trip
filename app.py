from fastapi import *
from fastapi.responses import FileResponse, JSONResponse
from typing import Any, cast
from database import get_connection

app = FastAPI()

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


PAGE_SIZE = 12


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
    page: int = Query(0, ge=0),
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