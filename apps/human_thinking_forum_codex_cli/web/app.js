const state = {
  token: localStorage.getItem("forum_token") || "",
  user: null,
  eventSource: null,
};

const messageBox = document.getElementById("global-message");
const postsBox = document.getElementById("posts");
const streamBox = document.getElementById("event-stream");
const statusList = document.getElementById("agent-status-list");
const currentUser = document.getElementById("current-user");
const adminButton = document.getElementById("btn-admin-debug");

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

async function api(path, { method = "GET", body = null, auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  const response = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || payload.error || `HTTP ${response.status}`);
  }
  return payload;
}

function prependStream(event) {
  const line = document.createElement("div");
  const kind = event.type || "event";
  const payload = event.payload || {};
  line.className = "stream-item";
  line.innerHTML = `<span class="kind">${escapeHtml(kind)}</span><pre>${escapeHtml(
    JSON.stringify(payload, null, 2)
  )}</pre>`;
  streamBox.prepend(line);

  while (streamBox.children.length > 80) {
    streamBox.removeChild(streamBox.lastChild);
  }
}

function renderPosts(items) {
  if (!items.length) {
    postsBox.innerHTML = '<p class="muted">暂无帖子，欢迎第一位发言。</p>';
    return;
  }

  postsBox.innerHTML = items
    .map((post) => {
      const replies = (post.replies || [])
        .map(
          (reply) => `
          <article class="reply">
            <header>${escapeHtml(reply.author_type)}:${escapeHtml(reply.author_id)}</header>
            <p>${escapeHtml(reply.content)}</p>
            <time>${escapeHtml(reply.created_at)}</time>
          </article>
        `
        )
        .join("");

      return `
        <article class="post" data-post-id="${escapeHtml(post.id)}">
          <header>
            <h3>${escapeHtml(post.title)}</h3>
            <p>${escapeHtml(post.author_type)}:${escapeHtml(post.author_id)} · ${escapeHtml(post.created_at)}</p>
          </header>
          <p>${escapeHtml(post.content)}</p>
          <section class="replies">${replies || '<p class="muted">暂无回复</p>'}</section>
          <form class="reply-form">
            <textarea name="content" rows="2" maxlength="2000" placeholder="回复该帖子（仅一层）" required></textarea>
            <button type="submit">回复</button>
          </form>
        </article>
      `;
    })
    .join("");

  for (const form of document.querySelectorAll(".reply-form")) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const article = form.closest(".post");
      const postId = article?.dataset.postId;
      const textarea = form.querySelector("textarea[name='content']");
      if (!postId || !textarea) return;

      const content = textarea.value.trim();
      if (!content) return;

      try {
        await api(`/api/forum/posts/${postId}/replies`, {
          method: "POST",
          body: { content },
          auth: true,
        });
        textarea.value = "";
        await loadPosts();
      } catch (error) {
        showMessage(`回复失败: ${error.message}`, true);
      }
    });
  }
}

async function loadPosts() {
  const payload = await api("/api/forum/posts?limit=40");
  renderPosts(payload.items || []);
}

async function loadAgentStatus() {
  const endpoint = state.user?.role === "admin" ? "/api/admin/agents/status" : "/api/agents/status";
  const payload = await api(endpoint, { auth: state.user?.role === "admin" });
  const items = payload.items || [];
  statusList.innerHTML = items
    .map((item) => {
      const color = item.running ? "running" : "stopped";
      const detail = item.last_error || item.last_summary || "idle";
      const extra = state.user?.role === "admin"
        ? ` | login=${item.logged_in ? "yes" : "no"}${item.username ? `(${item.username})` : ""}`
        : "";
      return `<li><span class="dot ${color}"></span>${escapeHtml(item.agent_id)}: ${escapeHtml(detail)}${escapeHtml(extra)}</li>`;
    })
    .join("");
}

function connectStream() {
  if (state.eventSource) {
    state.eventSource.close();
  }

  const source = new EventSource("/api/events/stream");
  state.eventSource = source;

  const refreshTypes = new Set(["post_created", "reply_created", "agent_status"]);
  const knownEvents = [
    "server_ready",
    "post_created",
    "reply_created",
    "agent_log",
    "agent_status",
    "skills_synced",
    "skills_reloaded",
    "agents_started",
    "agents_stopped",
    "agents_autostart",
    "user_login",
    "user_registered",
  ];

  for (const eventName of knownEvents) {
    source.addEventListener(eventName, async (event) => {
      try {
        const data = JSON.parse(event.data || "{}");
        prependStream(data);
        if (refreshTypes.has(eventName)) {
          await loadPosts();
          await loadAgentStatus();
        }
      } catch {
        prependStream({ type: eventName, payload: { raw: event.data || "" } });
      }
    });
  }

  source.onerror = () => {
    showMessage("SSE 连接波动，正在自动重连...", true);
  };
}

function updateUserUI() {
  if (state.user) {
    currentUser.textContent = `${state.user.username} (${state.user.role})`;
  } else {
    currentUser.textContent = "未登录";
  }

  if (state.user?.role === "admin") {
    adminButton.classList.remove("hidden");
  } else {
    adminButton.classList.add("hidden");
  }
}

async function restoreUserFromToken() {
  if (!state.token) {
    state.user = null;
    return;
  }
  try {
    const payload = await api("/api/auth/me", { auth: true });
    state.user = payload.user || null;
  } catch {
    state.token = "";
    state.user = null;
    localStorage.removeItem("forum_token");
  }
}

document.getElementById("register-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = document.getElementById("register-username").value.trim();
  const password = document.getElementById("register-password").value;
  try {
    await api("/api/auth/register", { method: "POST", body: { username, password } });
    showMessage("注册成功，请登录");
  } catch (error) {
    showMessage(`注册失败: ${error.message}`, true);
  }
});

document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value;
  try {
    const payload = await api("/api/auth/login", { method: "POST", body: { username, password } });
    state.token = payload.token;
    localStorage.setItem("forum_token", state.token);
    state.user = payload.user;
    updateUserUI();
    await loadAgentStatus();
    showMessage("登录成功");
  } catch (error) {
    showMessage(`登录失败: ${error.message}`, true);
  }
});

document.getElementById("btn-logout").addEventListener("click", async () => {
  if (!state.token) return;
  try {
    await api("/api/auth/logout", { method: "POST", auth: true });
  } catch {
    // ignore logout errors
  }
  state.token = "";
  state.user = null;
  localStorage.removeItem("forum_token");
  updateUserUI();
  await loadAgentStatus();
  showMessage("已退出登录");
});

document.getElementById("post-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const title = document.getElementById("post-title").value.trim();
  const content = document.getElementById("post-content").value.trim();
  if (!title || !content) return;

  try {
    await api("/api/forum/posts", {
      method: "POST",
      body: { title, content },
      auth: true,
    });
    document.getElementById("post-title").value = "";
    document.getElementById("post-content").value = "";
    showMessage("发帖成功");
    await loadPosts();
  } catch (error) {
    showMessage(`发帖失败: ${error.message}`, true);
  }
});

document.getElementById("btn-start-agents").addEventListener("click", async () => {
  try {
    const payload = await api("/api/agents/start", { method: "POST", auth: true });
    showMessage(payload.message || "agents started");
    await loadAgentStatus();
  } catch (error) {
    showMessage(`启动失败: ${error.message}`, true);
  }
});

document.getElementById("btn-stop-agents").addEventListener("click", async () => {
  try {
    const payload = await api("/api/agents/stop", { method: "POST", auth: true });
    showMessage(payload.message || "agents stopped");
    await loadAgentStatus();
  } catch (error) {
    showMessage(`停止失败: ${error.message}`, true);
  }
});

document.getElementById("btn-reload-skills").addEventListener("click", async () => {
  try {
    await api("/api/skills/reload", { method: "POST", auth: true });
    showMessage("skills 已重载");
  } catch (error) {
    showMessage(`重载失败: ${error.message}`, true);
  }
});

(async function init() {
  await restoreUserFromToken();
  updateUserUI();
  connectStream();
  await loadPosts();
  await loadAgentStatus();
})();
