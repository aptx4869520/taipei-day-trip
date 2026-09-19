---
name: taipei-day-trip-booking
description: Search Taipei attractions and book a Taipei Day Trip when the user asks to find or reserve a Taipei sightseeing itinerary.
---

# Taipei Day Trip Booking

Use the `taipei-day-trip` MCP server for this workflow.

1. If the user has not provided a search keyword, ask for one Taipei attraction name or MRT station name.
2. Call `搜尋台北市景點` with `keyword`.
3. Show the matching attractions. Include at least each attraction's `id` and `name`. If none match, ask for another keyword.
4. Ask the user to provide the attraction id, date, and time in natural language. Reuse values already supplied instead of asking again.
5. Normalize the values before booking:
   - date: `YYYY-MM-DD`
   - morning or 上午: `time="morning"`, `price=2000`
   - afternoon or 下午: `time="afternoon"`, `price=2500`
6. If the date is ambiguous or any required value is missing, ask only for the missing or ambiguous value.
7. Call `預定景點導覽行程` with `attractionId`, `date`, `time`, and `price`.
8. When the tool succeeds, show the booking result and the Booking Page URL returned by the tool so the user can complete the order.

Do not invent an attraction id. Do not expose or repeat the Bearer Token. If a tool returns `{"error": true}`, state that the operation failed and ask the user to verify the input or MCP token as appropriate.
