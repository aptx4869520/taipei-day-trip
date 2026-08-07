import mysql.connector
from mysql.connector import Error


DATABASE_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "ddmpkdanny98",
    "database": "taipei_day_trip",
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