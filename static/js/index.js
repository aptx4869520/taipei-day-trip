const state = {
  category: "",
  keyword: "",
  nextPage: 0,
  loading: false,
  queryVersion: 0,
  controller: null,
};

const searchForm = document.querySelector("#search-form");
const keywordInput = document.querySelector("#keyword-input");
const categoryButton = document.querySelector("#category-button");
const selectedCategory = document.querySelector("#selected-category");
const categoryMenu = document.querySelector("#category-menu");
const mrtList = document.querySelector("#mrt-list");
const mrtLeft = document.querySelector("#mrt-left");
const mrtRight = document.querySelector("#mrt-right");
const attractionList = document.querySelector("#attraction-list");
const loadSentinel = document.querySelector("#load-sentinel");
const emptyMessage = document.querySelector("#empty-message");
const errorMessage = document.querySelector("#error-message");

function buildAttractionsURL(page) {
  const params = new URLSearchParams({ page: String(page) });

  if (state.category) {
    params.set("category", state.category);
  }

  if (state.keyword) {
    params.set("keyword", state.keyword);
  }

  return `/api/attractions?${params.toString()}`;
}

function createAttractionCard(attraction) {
  const card = document.createElement("a");
  card.className = "attraction-card";
  card.href = `/attraction/${attraction.id}`;

  const imageArea = document.createElement("div");
  imageArea.className = "attraction-card__image";

  const image = document.createElement("img");
  image.src = attraction.images[0] || "";
  image.alt = attraction.name;
  image.loading = "lazy";

  const name = document.createElement("h2");
  name.className = "attraction-card__name";
  name.textContent = attraction.name;

  const info = document.createElement("div");
  info.className = "attraction-card__info";

  const mrt = document.createElement("span");
  mrt.className = "attraction-card__mrt";
  mrt.textContent = attraction.mrt || "";

  const category = document.createElement("span");
  category.className = "attraction-card__category";
  category.textContent = attraction.category;

  imageArea.append(image, name);
  info.append(mrt, category);
  card.append(imageArea, info);

  return card;
}

function renderAttractions(attractions, replace) {
  if (replace) {
    attractionList.replaceChildren();
  }

  const fragment = document.createDocumentFragment();

  attractions.forEach((attraction) => {
    fragment.append(createAttractionCard(attraction));
  });

  attractionList.append(fragment);
}

async function loadAttractions({ replace = false } = {}) {
  if (state.loading || state.nextPage === null) {
    return;
  }

  const page = replace ? 0 : state.nextPage;
  const currentVersion = state.queryVersion;
  state.loading = true;
  errorMessage.hidden = true;

  try {
    const response = await fetch(buildAttractionsURL(page), {
      signal: state.controller?.signal,
    });

    if (!response.ok) {
      throw new Error(`Attractions API failed: ${response.status}`);
    }

    const result = await response.json();

    if (currentVersion !== state.queryVersion) {
      return;
    }

    renderAttractions(result.data, replace);
    state.nextPage = result.nextPage;
    emptyMessage.hidden = !(replace && result.data.length === 0);
  } catch (error) {
    if (error.name !== "AbortError") {
      console.error(error);
      errorMessage.hidden = false;
    }
  } finally {
    if (currentVersion === state.queryVersion) {
      state.loading = false;
    }
  }
}

function restartSearch() {
  state.controller?.abort();
  state.controller = new AbortController();
  state.queryVersion += 1;
  state.nextPage = 0;
  state.loading = false;
  loadAttractions({ replace: true });
}

function closeCategoryMenu() {
  categoryMenu.hidden = true;
  categoryButton.setAttribute("aria-expanded", "false");
}

function renderCategories(categories) {
  const fragment = document.createDocumentFragment();

  ["", ...categories].forEach((category) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "category__item";
    button.textContent = category || "全部分類";

    button.addEventListener("click", () => {
      state.category = category;
      selectedCategory.textContent = category || "全部分類";
      closeCategoryMenu();
    });

    fragment.append(button);
  });

  categoryMenu.replaceChildren(fragment);
}

async function loadCategories() {
  const response = await fetch("/api/categories");

  if (!response.ok) {
    throw new Error(`Categories API failed: ${response.status}`);
  }

  const result = await response.json();
  renderCategories(result.data);
}

function renderMRTs(mrts) {
  const fragment = document.createDocumentFragment();

  mrts.forEach((mrtName) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "mrt-bar__item";
    button.textContent = mrtName;

    button.addEventListener("click", () => {
      keywordInput.value = mrtName;
      state.keyword = mrtName;
      restartSearch();
    });

    fragment.append(button);
  });

  mrtList.replaceChildren(fragment);
}

async function loadMRTs() {
  const response = await fetch("/api/mrts");

  if (!response.ok) {
    throw new Error(`MRT API failed: ${response.status}`);
  }

  const result = await response.json();
  renderMRTs(result.data);
}

categoryButton.addEventListener("click", () => {
  const willOpen = categoryMenu.hidden;
  categoryMenu.hidden = !willOpen;
  categoryButton.setAttribute("aria-expanded", String(willOpen));
});

document.addEventListener("click", (event) => {
  if (!event.target.closest(".category")) {
    closeCategoryMenu();
  }
});

searchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  state.keyword = keywordInput.value.trim();
  restartSearch();
});

mrtLeft.addEventListener("click", () => {
  mrtList.scrollBy({
    left: -mrtList.clientWidth * 0.8,
    behavior: "smooth",
  });
});

mrtRight.addEventListener("click", () => {
  mrtList.scrollBy({
    left: mrtList.clientWidth * 0.8,
    behavior: "smooth",
  });
});

const observer = new IntersectionObserver(
  ([entry]) => {
    if (entry.isIntersecting && !state.loading && state.nextPage !== null) {
      loadAttractions();
    }
  },
  {
    rootMargin: "200px 0px",
  },
);

observer.observe(loadSentinel);

async function initializePage() {
  state.controller = new AbortController();

  const results = await Promise.allSettled([
    loadCategories(),
    loadMRTs(),
    loadAttractions({ replace: true }),
  ]);

  results.forEach((result) => {
    if (result.status === "rejected") {
      console.error(result.reason);
    }
  });
}

initializePage();
