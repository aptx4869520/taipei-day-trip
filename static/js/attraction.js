"use strict";

const pathParts = window.location.pathname.split("/").filter(Boolean);
const attractionId = Number(pathParts.at(-1));

const pageElements = {
  section: document.querySelector(".attraction"),
  separator: document.querySelector(".separator"),
  information: document.querySelector(".information"),
  error: document.querySelector("#attraction-error"),
  name: document.querySelector("#attraction-name"),
  meta: document.querySelector("#attraction-meta"),
  description: document.querySelector("#attraction-description"),
  address: document.querySelector("#attraction-address"),
  transport: document.querySelector("#attraction-transport"),
  image: document.querySelector("#attraction-image"),
  indicators: document.querySelector("#slideshow-indicators"),
  previousButton: document.querySelector(".slideshow__arrow--left"),
  nextButton: document.querySelector(".slideshow__arrow--right"),
  price: document.querySelector("#booking-price"),
  date: document.querySelector("#booking-date"),
  bookingButton: document.querySelector(".booking__button"),
  authTrigger: document.querySelector("[data-auth-trigger]"),
};

const timeInputs = document.querySelectorAll('input[name="time"]');
const TOUR_PRICES = {
  morning: 2000,
  afternoon: 2500,
};

let attractionImages = [];
let currentImageIndex = 0;
let attractionName = "";

async function fetchAttraction(id) {
  const response = await fetch(`/api/attraction/${id}`);
  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.message || "景點資料載入失敗");
  }

  if (!result.data) {
    throw new Error("景點資料格式不正確");
  }

  return result.data;
}

function renderCurrentImage() {
  const hasImages = attractionImages.length > 0;
  pageElements.image.hidden = !hasImages;

  if (!hasImages) {
    pageElements.image.removeAttribute("src");
    pageElements.image.alt = "";
    return;
  }

  pageElements.image.src = attractionImages[currentImageIndex];
  pageElements.image.alt = `${attractionName}，第 ${currentImageIndex + 1} 張圖片`;
}

function renderIndicators() {
  const fragment = document.createDocumentFragment();

  attractionImages.forEach((_, index) => {
    const indicator = document.createElement("span");
    indicator.className = "slideshow__indicator";

    if (index === currentImageIndex) {
      indicator.classList.add("slideshow__indicator--active");
    }

    fragment.append(indicator);
  });

  pageElements.indicators.replaceChildren(fragment);
}

function updateSlideshowControls() {
  const shouldShowControls = attractionImages.length > 1;
  pageElements.previousButton.hidden = !shouldShowControls;
  pageElements.nextButton.hidden = !shouldShowControls;
  pageElements.indicators.hidden = attractionImages.length === 0;
}

function renderSlideshow() {
  renderCurrentImage();
  renderIndicators();
  updateSlideshowControls();
}

function showNextImage() {
  if (attractionImages.length <= 1) {
    return;
  }

  currentImageIndex = (currentImageIndex + 1) % attractionImages.length;
  renderSlideshow();
}

function showPreviousImage() {
  if (attractionImages.length <= 1) {
    return;
  }

  currentImageIndex =
    (currentImageIndex - 1 + attractionImages.length) % attractionImages.length;
  renderSlideshow();
}

function renderAttraction(attraction) {
  attractionName = attraction.name;
  attractionImages = Array.isArray(attraction.images)
    ? attraction.images.filter((image) => typeof image === "string" && image)
    : [];
  currentImageIndex = 0;

  pageElements.name.textContent = attraction.name;
  pageElements.meta.textContent = attraction.mrt
    ? `${attraction.category} at ${attraction.mrt}`
    : attraction.category;
  pageElements.description.textContent = attraction.description;
  pageElements.address.textContent = attraction.address;
  pageElements.transport.textContent = attraction.transport;
  document.title = `${attraction.name} | 台北一日遊`;

  renderSlideshow();
}

function updatePrice(time) {
  const price = TOUR_PRICES[time];

  if (price !== undefined) {
    pageElements.price.textContent = `新台幣 ${price} 元`;
  }
}

function initializeBookingDate() {
  const today = new Date();
  const timezoneOffset = today.getTimezoneOffset()
    * 60
    * 1000;

  const localDate = new Date(
    today.getTime() - timezoneOffset
  );

  pageElements.date.min = localDate
    .toISOString()
    .split("T")[0];
}

function initializeBookingTime() {
  const selectedTime = document.querySelector('input[name="time"]:checked');

  if (selectedTime) {
    updatePrice(selectedTime.value);
  }

  timeInputs.forEach((input) => {
    input.addEventListener("change", () => updatePrice(input.value));
  });
}

async function createBooking() {
  const token = localStorage.getItem("token");

  if (!token) {
    pageElements.authTrigger.click();
    return;
  }

  if (!pageElements.date.value) {
    pageElements.date.reportValidity();
    return;
  }

  const selectedTime = document.querySelector(
    'input[name="time"]:checked'
  );

  if (!selectedTime) {
    return;
  }

  const time = selectedTime.value;
  const price = TOUR_PRICES[time];

  pageElements.bookingButton.disabled = true;

  try {
    const response = await fetch("/api/booking", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        attractionId,
        date: pageElements.date.value,
        time,
        price
      })
    });

    const result = await response.json();

    if (response.status === 403) {
      localStorage.removeItem("token");
      pageElements.authTrigger.click();
      return;
    }

    if (!response.ok) {
      throw new Error(
        result.message || "建立預訂行程失敗"
      );
    }

    window.location.href = "/booking";
  } catch (error) {
    console.error("建立預訂行程失敗：", error);
    window.alert(
      error.message || "建立預訂行程失敗"
    );
  } finally {
    pageElements.bookingButton.disabled = false;
  }
}

function showPageError(message) {
  pageElements.section.hidden = true;
  pageElements.separator.hidden = true;
  pageElements.information.hidden = true;
  pageElements.error.textContent = message;
  pageElements.error.hidden = false;
}

async function initializeAttractionPage() {
  initializeBookingDate();
  initializeBookingTime();

  pageElements.bookingButton.addEventListener(
    "click",
    createBooking
  );

  pageElements.previousButton.addEventListener(
    "click",
    showPreviousImage
  );

  pageElements.nextButton.addEventListener("click", showNextImage);

  if (!Number.isInteger(attractionId) || attractionId < 1) {
    showPageError("景點編號不正確");
    return;
  }

  try {
    const attraction = await fetchAttraction(attractionId);
    renderAttraction(attraction);
  } catch (error) {
    console.error(error);
    showPageError(error.message || "景點資料載入失敗，請稍後再試");
  }
}

initializeAttractionPage();
