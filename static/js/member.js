const memberStatus = document.querySelector("#member-status");
const memberToken = localStorage.getItem("token");
const memberHeaders = memberToken
  ? { Authorization: `Bearer ${memberToken}` }
  : {};

async function loadMember() {
  try {
    const response = await fetch("/api/user/auth", { headers: memberHeaders });
    if (!response.ok) throw new Error("無法確認登入狀態，請稍後重新整理。");
    const result = await response.json();
    if (!result.data) {
      localStorage.removeItem("token");
      window.location.replace("/");
      return;
    }
    document.querySelector("#member-name").textContent = result.data.name;
    document.querySelector("#mcp-host").textContent =
      `${window.location.origin}/mcp/`;
    document.querySelector("#member-content").hidden = false;
    memberStatus.hidden = true;
  } catch (error) {
    memberStatus.textContent = error.message;
  }
}

document
  .querySelector("#generate-token")
  .addEventListener("click", async (event) => {
    const button = event.currentTarget;
    const status = document.querySelector("#token-status");
    button.disabled = true;
    status.textContent = "正在更新金鑰…";
    try {
      const response = await fetch("/api/member/token", {
        method: "POST",
        headers: memberHeaders,
        cache: "no-store",
      });
      if (response.status === 403) {
        localStorage.removeItem("token");
        window.location.replace("/");
        return;
      }
      const result = await response.json();
      if (!response.ok) throw new Error(result.message || "金鑰更新失敗");
      document.querySelector("#mcp-token").textContent = result.token;
      status.textContent = "金鑰已更新，請使用新金鑰設定 MCP。";
    } catch (error) {
      status.textContent =
        error instanceof TypeError
          ? "連線中斷，金鑰可能已更新。請再次產生新金鑰。"
          : error.message;
    } finally {
      button.disabled = false;
    }
  });

document.querySelector("#member-signout").addEventListener("click", () => {
  localStorage.removeItem("token");
  window.location.replace("/");
});

loadMember();
