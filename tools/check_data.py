import json
import re
from collections import Counter

with open("data/taipei-attractions.json", "r", encoding="utf-8") as file:
    raw_data = json.load(file)

attractions = raw_data["list"]
img_host = raw_data["img_host"]

ids = [item["_id"] for item in attractions]

duplicate_ids = [
    attraction_id
    for attraction_id, count in Counter(ids).items()
    if count > 1
]

invalid_coordinates = []
no_images = []
image_counts = []

pattern = re.compile(
    r"/imgs/[^/]+?\.(?:jpg|jpeg|png)",
    re.IGNORECASE
)

for item in attractions:
    attraction_id = item["_id"]

    try:
        float(item["latitude"])
        float(item["longitude"])
    except (TypeError, ValueError):
        invalid_coordinates.append(attraction_id)

    paths = pattern.findall(item["imgurls"])
    images = [img_host + path for path in paths]

    image_counts.append(len(images))

    if not images:
        no_images.append(attraction_id)

print("ID 數量：", len(ids))
print("唯一 ID 數量：", len(set(ids)))
print("重複 ID：", duplicate_ids)
print("無效經緯度：", invalid_coordinates)
print("沒有圖片：", no_images)
print("最少圖片：", min(image_counts))
print("最多圖片：", max(image_counts))
print("圖片總數：", sum(image_counts))