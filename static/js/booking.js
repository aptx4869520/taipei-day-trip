const bookingElements = {
  headline: document.querySelector("#booking-headline"),
  userName: document.querySelector("#booking-user-name"),
  empty: document.querySelector("#booking-empty"),
  details: document.querySelector("#booking-details"),
  attractionImage: document.querySelector(
    "#booking-attraction-image"
  ),
  attractionName: document.querySelector(
    "#booking-attraction-name"
  ),
  date: document.querySelector("#booking-date"),
  time: document.querySelector("#booking-time"),
  price: document.querySelector("#booking-price"),
  address: document.querySelector("#booking-address"),
  totalPrice: document.querySelector(
    "#booking-total-price"
  ),
  contactName: document.querySelector("#contact-name"),
  contactEmail: document.querySelector("#contact-email"),
  deleteButton: document.querySelector("#booking-delete")
};

function getAuthorizationHeaders(token) {
  return {
    Authorization: `Bearer ${token}`
  };
}

function redirectToHome() {
  window.location.href = "/";
}

function renderEmptyBooking() {
  bookingElements.details.hidden = true;
  bookingElements.empty.hidden = false;

  document.body.classList.add("booking-empty-state");
}

function renderBooking(booking) {
  const timeText = booking.time === "morning"
    ? "早上 9 點到下午 1 點"
    : "下午 2 點到晚上 9 點";

  bookingElements.attractionImage.src =
    booking.attraction.image;

  bookingElements.attractionImage.alt =
    booking.attraction.name;

  bookingElements.attractionName.textContent =
    booking.attraction.name;

  bookingElements.date.textContent = booking.date;
  bookingElements.time.textContent = timeText;
  bookingElements.price.textContent = booking.price;
  bookingElements.address.textContent =
    booking.attraction.address;

  bookingElements.totalPrice.textContent =
    booking.price;

  bookingElements.empty.hidden = true;
  bookingElements.details.hidden = false;

  document.body.classList.remove("booking-empty-state");
}

async function loadBookingPage() {
  const token = localStorage.getItem("token");

  if (!token) {
    redirectToHome();
    return;
  }

  const headers = getAuthorizationHeaders(token);

  try {
    const userResponse = await fetch("/api/user/auth", {
      method: "GET",
      headers
    });

    if (userResponse.status === 403) {
      localStorage.removeItem("token");
      redirectToHome();
      return;
    }

    if (!userResponse.ok) {
      throw new Error("無法取得會員資料");
    }

    const userResult = await userResponse.json();

    if (!userResult.data) {
      localStorage.removeItem("token");
      redirectToHome();
      return;
    }

    bookingElements.userName.textContent =
      userResult.data.name;

    bookingElements.contactName.value =
      userResult.data.name;

    bookingElements.contactEmail.value =
      userResult.data.email;

    bookingElements.headline.hidden = false;

    const bookingResponse = await fetch("/api/booking", {
      method: "GET",
      headers
    });

    if (bookingResponse.status === 403) {
      localStorage.removeItem("token");
      redirectToHome();
      return;
    }

    if (!bookingResponse.ok) {
      throw new Error("無法取得預訂資料");
    }

    const bookingResult = await bookingResponse.json();

    if (bookingResult.data === null) {
      renderEmptyBooking();
      return;
    }

    renderBooking(bookingResult.data);
  } catch (error) {
    console.error("載入預訂頁面失敗：", error);
  }
}

async function deleteBooking() {
  const token = localStorage.getItem("token");

  if (!token) {
    redirectToHome();
    return;
  }

  bookingElements.deleteButton.disabled = true;

  try {
    const response = await fetch("/api/booking", {
      method: "DELETE",
      headers: getAuthorizationHeaders(token)
    });

    if (response.status === 403) {
      localStorage.removeItem("token");
      redirectToHome();
      return;
    }

    if (!response.ok) {
      throw new Error("刪除預訂資料失敗");
    }

    window.location.reload();
  } catch (error) {
    console.error("刪除預訂行程失敗：", error);
    bookingElements.deleteButton.disabled = false;
  }
}

bookingElements.deleteButton.addEventListener(
  "click",
  deleteBooking
);

loadBookingPage();