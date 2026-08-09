from database import get_connection


connection = None
cursor = None

try:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM attractions")
    attraction_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM attraction_images")
    image_count = cursor.fetchone()[0]

    print("資料庫連線成功")
    print(f"景點數量：{attraction_count}")
    print(f"圖片數量：{image_count}")

finally:
    if cursor is not None:
        cursor.close()

    if connection is not None and connection.is_connected():
        connection.close()