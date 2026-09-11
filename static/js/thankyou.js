const thankyouElements = {
  title: document.querySelector("#thankyou-title"),
  message: document.querySelector("#thankyou-message"),
  successIcon: document.querySelector("#success-icon"),
  pendingIcon: document.querySelector("#pending-icon"),
  orderCard: document.querySelector("#order-card"),
  orderNumber: document.querySelector("#order-number"),
  copyButton: document.querySelector("#copy-order-number"),
  copyFeedback: document.querySelector("#copy-feedback")
};

const searchParams = new URLSearchParams(window.location.search);
const orderNumber = searchParams.get("number")?.trim();

function showOrderNumber() {
  thankyouElements.orderNumber.textContent = orderNumber;
  thankyouElements.orderCard.hidden = false;
}

function showPaidOrder() {
  thankyouElements.successIcon.hidden = false;
  thankyouElements.pendingIcon.hidden = true;
  thankyouElements.title.textContent = "付款成功";
  thankyouElements.message.textContent =
    "行程已預訂完成，請記下您的訂單編號。";
  playSuccessAnimation();
}

// 付款狀態確認成功後，才播放一次慶祝動畫。
function playSuccessAnimation() {
  const card = document.querySelector(".thankyou-card");
  if (card.classList.contains("is-paid")) return;
  card.classList.add("is-paid");
  const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");

  const confetti = document.createElement("div");
  confetti.className = "thankyou-confetti";
  confetti.setAttribute("aria-hidden", "true");
  const colors = ["#448899", "#72bca5", "#b8ded0", "#d6b66e"];
  for (let index = 0; index < 36; index += 1) {
    const piece = document.createElement("span");
    piece.style.setProperty("--left", `${Math.random() * 100}%`);
    piece.style.setProperty("--drift", `${Math.random() * 120 - 60}px`);
    piece.style.setProperty("--delay", `${Math.random() * 0.5}s`);
    piece.style.setProperty("--duration", `${2.4 + Math.random() * 0.8}s`);
    piece.style.setProperty("--rotation", `${Math.random() * 720 - 360}deg`);
    piece.style.backgroundColor = colors[index % colors.length];
    confetti.appendChild(piece);
  }
  document.querySelector(".thankyou-page").appendChild(confetti);

  const cleanup = () => {
    confetti.remove();
    motionPreference.removeEventListener("change", cleanup);
  };
  motionPreference.addEventListener("change", cleanup);
  window.setTimeout(cleanup, 4000);
}

function showUnpaidOrder() {
  thankyouElements.successIcon.hidden = true;
  thankyouElements.pendingIcon.hidden = false;
  thankyouElements.title.textContent = "付款尚未完成";
  thankyouElements.message.textContent =
    "訂單已建立但付款未完成；如需協助，請提供下方訂單編號。";
}

function showOrderError(title, message) {
  thankyouElements.successIcon.hidden = true;
  thankyouElements.pendingIcon.hidden = true;
  thankyouElements.title.textContent = title;
  thankyouElements.message.textContent = message;
}

async function loadOrderStatus() {
  if (!orderNumber) {
    showOrderError(
      "找不到訂單編號",
      "請返回預定行程頁面確認訂單。"
    );
    return;
  }

  showOrderNumber();

  const token = localStorage.getItem("token");
  if (!token) {
    showOrderError(
      "無法確認訂單狀態",
      "登入狀態已失效，請重新登入後確認訂單。"
    );
    return;
  }

  try {
    const response = await fetch(`/api/order/${encodeURIComponent(orderNumber)}`, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });

    if (response.status === 403) {
      localStorage.removeItem("token");
      showOrderError(
        "無法確認訂單狀態",
        "登入狀態已失效，請重新登入後確認訂單。"
      );
      return;
    }

    const result = await response.json();
    if (!response.ok || !result.data) {
      showOrderError(
        "找不到訂單資料",
        "請確認訂單編號，或稍後再試。"
      );
      return;
    }

    if (result.data.status === 1) {
      showPaidOrder();
    } else {
      showUnpaidOrder();
    }
  } catch {
    showOrderError(
      "暫時無法確認訂單",
      "請保留下方訂單編號，稍後再試。"
    );
  }
}

function fallbackCopy(text) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.setAttribute("readonly", "");
  textArea.style.position = "fixed";
  textArea.style.opacity = "0";
  document.body.appendChild(textArea);
  textArea.select();
  const copied = document.execCommand("copy");
  textArea.remove();
  return copied;
}

async function copyOrderNumber() {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(orderNumber);
    } else if (!fallbackCopy(orderNumber)) {
      throw new Error("Copy failed");
    }
    thankyouElements.copyFeedback.textContent = "訂單編號已複製";
  } catch {
    thankyouElements.copyFeedback.textContent =
      "無法自動複製，請手動選取訂單編號。";
  }
}

thankyouElements.copyButton.addEventListener("click", copyOrderNumber);
loadOrderStatus();
