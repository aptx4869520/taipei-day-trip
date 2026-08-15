import os

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


def get_connection():
    """
    建立並回傳一條 MySQL 連線。

    呼叫端負責在使用完畢後關閉 connection。
    """
    try:
        connection = mysql.connector.connect(**DATABASE_CONFIG)

        if connection.is_connected():
            return connection

        raise ConnectionError("MySQL 連線未成功建立")

    except Error as error:
        raise ConnectionError(
            f"無法連線至 MySQL：{error}"
        ) from error
