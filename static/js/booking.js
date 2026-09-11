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
  contactPhone: document.querySelector("#contact-phone"),
  deleteButton: document.querySelector("#booking-delete"),
  confirmButton: document.querySelector("#booking-confirm"),
  paymentMessage: document.querySelector("#payment-message")
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

let currentBooking = null;
let orderSubmitted = false;

function renderBooking(booking) {
  currentBooking = booking;
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
    setupTapPay();
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


const tappayConfig = {
  appId: 171085,
  appKey: "app_hSGPwfzDzTjryZD3NR9zhVeouGK2JEhy4RZsmhDnhjZhyUpLUEjoyMeR8af2",
  serverType: "sandbox"
};

let isGettingPrime = false;

function setupTapPay() {
  if (!window.TPDirect) {
    bookingElements.paymentMessage.textContent =
      "付款服務載入失敗，請重新整理頁面。";
    return;
  }

  if (!Number.isInteger(tappayConfig.appId)
      || tappayConfig.appId <= 0
      || !tappayConfig.appKey.trim()) {
    bookingElements.paymentMessage.textContent =
      "付款服務尚未設定完成。";
    return;
  }

  try {
    TPDirect.setupSDK(
      tappayConfig.appId,
      tappayConfig.appKey,
      tappayConfig.serverType
    );

    TPDirect.card.setup({
      fields: {
        number: {
          element: "#card-number",
          placeholder: "**** **** **** ****"
        },
        expirationDate: {
          element: "#card-expiration-date",
          placeholder: "MM / YY"
        },
        ccv: {
          element: "#card-ccv",
          placeholder: "CCV"
        }
      },
      styles: {
        input: {
          "color": "#000000",
          "font-size": "16px"
        },
        ".invalid": {
          "color": "#b3261e"
        }
      }
    });

    TPDirect.card.onUpdate((update) => {
      bookingElements.confirmButton.disabled =
        isGettingPrime || orderSubmitted || !update.canGetPrime;

      if (!isGettingPrime && !orderSubmitted) {
        bookingElements.paymentMessage.textContent = update.hasError
          ? "請確認卡號、有效期限與驗證碼是否正確。"
          : "";
      }
    });
  } catch {
    bookingElements.confirmButton.disabled = true;
    bookingElements.paymentMessage.textContent =
      "付款服務初始化失敗，請確認設定後重新整理。";
  }
}

function getPaymentPrime() {
  if (isGettingPrime || orderSubmitted || !window.TPDirect || !currentBooking) {
    return;
  }

  for (const input of [bookingElements.contactName,
    bookingElements.contactEmail, bookingElements.contactPhone]) {
    input.value = input.value.trim();
    if (!input.reportValidity()) return;
  }

  if (!TPDirect.card.getTappayFieldsStatus().canGetPrime) {
    bookingElements.paymentMessage.textContent = "請完整填寫正確的信用卡資料。";
    return;
  }

  isGettingPrime = true;
  bookingElements.confirmButton.disabled = true;
  bookingElements.deleteButton.disabled = true;
  bookingElements.paymentMessage.textContent = "正在確認信用卡資料…";

  try {
    TPDirect.card.getPrime(async (result) => {
      try {
        if (result.status !== 0
            || typeof result.card?.prime !== "string"
            || !result.card.prime.trim()) {
          bookingElements.paymentMessage.textContent = "取得 Prime 失敗，請確認信用卡資料後重試。";
          return;
        }
        await submitOrder(result.card.prime);
      } finally {
        finishPaymentAttempt();
      }
    });
  } catch {
    bookingElements.paymentMessage.textContent = "取得 Prime 失敗，請稍後重試。";
    finishPaymentAttempt();
  }
}

function finishPaymentAttempt() {
  isGettingPrime = false;
  bookingElements.confirmButton.disabled = orderSubmitted
    || !TPDirect.card.getTappayFieldsStatus().canGetPrime;
  bookingElements.deleteButton.disabled = orderSubmitted;
}

async function submitOrder(prime) {
  const token = localStorage.getItem("token");
  if (!token) {
    redirectToHome();
    return;
  }

  orderSubmitted = true;
  bookingElements.paymentMessage.textContent = "訂單付款處理中，請勿重複操作…";
  try {
    const response = await fetch("/api/orders", {
      method: "POST",
      headers: {
        ...getAuthorizationHeaders(token),
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        prime,
        order: {
          price: currentBooking.price,
          trip: {
            attraction: currentBooking.attraction,
            date: currentBooking.date,
            time: currentBooking.time
          },
          contact: {
            name: bookingElements.contactName.value.trim(),
            email: bookingElements.contactEmail.value.trim(),
            phone: bookingElements.contactPhone.value.trim()
          }
        }
      })
    });
    if (response.status === 403) {
      localStorage.removeItem("token");
      redirectToHome();
      return;
    }
    const result = await response.json();
    if (!response.ok) {
      if (response.status === 400) orderSubmitted = false;
      bookingElements.paymentMessage.textContent = result.message
        || "訂單結果尚未確認，請勿重複付款，請聯繫客服查詢。";
      return;
    }
    if (!result.data?.number || !result.data.payment) {
      throw new Error("Invalid order response");
    }
    window.location.href =
      `/thankyou?number=${encodeURIComponent(result.data.number)}`;
  } catch {
    bookingElements.paymentMessage.textContent =
      "訂單結果尚未確認，請勿重複付款，請聯繫客服查詢。";
  }
}

bookingElements.confirmButton.addEventListener("click", getPaymentPrime);

loadBookingPage();
