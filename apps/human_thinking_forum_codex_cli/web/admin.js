const token = localStorage.getItem("forum_token") || "";

const messageBox = document.getElementById("admin-message");
const panelRoot = document.getElementById("agent-panels");
const dbUsers = document.getElementById("db-users");
const dbCred = document.getElementById("db-credentials");
const dbSessions = document.getElementById("db-sessions");
const dbContent = document.getElementById("db-content");

const agentIds = ["socrates", "ada", "laozi", "turing"];
const filters = new Set(["chat", "thinking", "tool", "system"]);
const panels = new Map();

function showMessage(text, isError = false) {
  messageBox.textContent = text;
  messageBox.className = isError ? "error" : "ok";
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function api(path, { method = "GET", body = null } = {}) {
  if (!token) {
    throw new Error("未登录，请先回论坛登录 admin/1234");
  }

  const response = await fetch(path, {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: body ? JSON.stringify(body) : null,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || payload.error || `HTTP ${response.status}`);
  }
  return payload;
}

function ensurePanels() {
  panelRoot.innerHTML = agentIds
    .map(
      (agentId) => `
      <article class="card agent-panel" data-agent-id="${agentId}">
        <h3>${agentId}</h3>
        <p class="muted" id="status-${agentId}">等待事件...</p>
        <div class="stream" id="stream-${agentId}"></div>
      </article>
    `
    )
    .join("");

  for (const agentId of agentIds) {
    panels.set(agentId, {
      status: document.getElementById(`status-${agentId}`),
      stream: document.getElementById(`stream-${agentId}`),
    });
  }
}

function appendAgentEvent(agentId, payload) {
  const panel = panels.get(agentId);
  if (!panel) return;

  const kind = payload.kind || "system";
  if (!filters.has(kind)) return;

  const line = document.createElement("div");
  line.className = "stream-item";
  line.innerHTML = `<span class="kind">${escapeHtml(kind)}</span><pre>${escapeHtml(
    `[${payload.ts || ""}] ${payload.text || ""}`
  )}</pre>`;
  panel.stream.prepend(line);
  while (panel.stream.children.length > 120) {
    panel.stream.removeChild(panel.stream.lastChild);
  }
}

function updateAgentStatus(item) {
  const panel = panels.get(item.agent_id);
  if (!panel) return;
  const status = item.running ? "running" : "stopped";
  const error = item.last_error || "none";
  const user = item.username ? `user=${item.username}` : "user=-";
  panel.status.textContent = `${status} | ${user} | error=${error}`;
}

async function loadStatus() {
  const payload = await api("/api/admin/agents/status");
  for (const item of payload.items || []) {
    updateAgentStatus(item);
  }
}

async function loadSnapshot() {
  const payload = await api("/api/admin/db/snapshot");
  const data = payload.data || {};
  dbUsers.textContent = JSON.stringify(data.users || [], null, 2);
  dbCred.textContent = JSON.stringify(data.agent_credentials || [], null, 2);
  dbSessions.textContent = JSON.stringify(
    {
      sessions: data.sessions || [],
      agent_sessions: data.agent_sessions || [],
    },
    null,
    2
  );
  dbContent.textContent = JSON.stringify(
    {
      posts: data.posts || [],
      replies: data.replies || [],
    },
    null,
    2
  );
}

function connectThoughtsStream() {
  const source = new EventSource(`/api/admin/agents/thoughts/stream?admin_token=${encodeURIComponent(token)}`);

  source.onerror = async () => {
    source.close();
    showMessage("思维流连接波动，切换为状态轮询。", true);
    setInterval(async () => {
      try {
        await loadStatus();
      } catch {
        // ignore
      }
    }, 2000);
  };

  const knownEvents = ["agent_log", "agent_status", "agents_started", "agents_stopped", "skills_synced", "skills_reloaded"];
  for (const eventName of knownEvents) {
    source.addEventListener(eventName, (event) => {
      try {
        const message = JSON.parse(event.data || "{}");
        const payload = message.payload || {};
        if (eventName === "agent_log") {
          appendAgentEvent(payload.agent_id, payload);
        }
        if (eventName === "agent_status") {
          updateAgentStatus(payload);
        }
      } catch {
        // ignore malformed events
      }
    });
  }
}

function bindFilters() {
  for (const input of document.querySelectorAll("input[data-kind]")) {
    input.addEventListener("change", () => {
      const kind = input.getAttribute("data-kind");
      if (!kind) return;
      if (input.checked) filters.add(kind);
      else filters.delete(kind);
    });
  }
}

document.getElementById("btn-refresh-db").addEventListener("click", async () => {
  try {
    await loadSnapshot();
    showMessage("数据库快照已刷新");
  } catch (error) {
    showMessage(`刷新失败: ${error.message}`, true);
  }
});

(async function init() {
  ensurePanels();
  bindFilters();

  try {
    const me = await api("/api/auth/me");
    if (me.user?.role !== "admin") {
      throw new Error("仅超级管理员可访问此页面");
    }

    await loadStatus();
    await loadSnapshot();
    showMessage("已连接管理员视图");
    connectThoughtsStream();
  } catch (error) {
    showMessage(`初始化失败: ${error.message}`, true);
  }
})();
