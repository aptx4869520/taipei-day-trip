import json
import os
import re

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error


load_dotenv()


DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME", "taipei_day_trip"),
    "charset": "utf8mb4",
}


def extract_image_urls(img_host: str, raw_imgurls: str) -> list[str]:
    """
    將原始格式：
    /imgs/1-0.jpg/imgs/1-1.jpg

    轉換為：
    [
        "https://.../imgs/1-0.jpg",
        "https://.../imgs/1-1.jpg"
    ]
    """
    pattern = re.compile(
        r"/imgs/[^/]+?\.(?:jpg|jpeg|png)",
        re.IGNORECASE,
    )

    paths = pattern.findall(raw_imgurls or "")
    return [img_host + path for path in paths]


def load_raw_data() -> tuple[list[dict], str]:
    with open(
        "data/taipei-attractions.json",
        "r",
        encoding="utf-8",
    ) as file:
        raw_data = json.load(file)

    attractions = raw_data["list"]
    img_host = raw_data["img_host"]

    return attractions, img_host


def import_data() -> None:
    connection = None
    cursor = None

    try:
        attractions, img_host = load_raw_data()

        connection = mysql.connector.connect(**DATABASE_CONFIG)
        cursor = connection.cursor()

        attraction_sql = """
            INSERT INTO attractions (
                id,
                name,
                category,
                description,
                address,
                transport,
                mrt,
                lat,
                lng
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        image_sql = """
            INSERT INTO attraction_images (
                attraction_id,
                image_url,
                image_order
            )
            VALUES (%s, %s, %s)
        """

        attraction_count = 0
        image_count = 0

        for item in attractions:
            attraction_values = (
                item["_id"],
                item["name"],
                item["CAT"],
                item["description"],
                item["address"],
                item["direction"],
                item["MRT"],
                item["latitude"],
                item["longitude"],
            )

            cursor.execute(attraction_sql, attraction_values)
            attraction_count += 1

            image_urls = extract_image_urls(
                img_host,
                item["imgurls"],
            )

            if not image_urls:
                raise ValueError(
                    f"景點 ID {item['_id']} 沒有可匯入的圖片網址"
                )

            for image_order, image_url in enumerate(image_urls):
                image_values = (
                    item["_id"],
                    image_url,
                    image_order,
                )

                cursor.execute(image_sql, image_values)
                image_count += 1

        connection.commit()

        print("資料匯入成功")
        print(f"景點數量：{attraction_count}")
        print(f"圖片數量：{image_count}")

    except (Error, KeyError, TypeError, ValueError) as error:
        if connection is not None and connection.is_connected():
            connection.rollback()

        print("資料匯入失敗")
        print(error)

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    import_data()