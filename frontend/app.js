const chatForm = document.querySelector("#chatForm");
const chatLog = document.querySelector("#chatLog");
const messageInput = document.querySelector("#messageInput");
const customerEmail = document.querySelector("#customerEmail");
const sendButton = chatForm.querySelector('button[type="submit"]');
const ticketList = document.querySelector("#ticketList");
const approvalList = document.querySelector("#approvalList");
const traceList = document.querySelector("#traceList");
const navItems = document.querySelectorAll(".nav-item[data-view]");
const ticketSection = document.querySelector(".ticket-section");
const approvalPanel = document.querySelector("#approvalPanel");
const evaluationPanel = document.querySelector("#evaluationPanel");
const ordersPanel = document.querySelector("#ordersPanel");
const databaseAdminPanel = document.querySelector("#databaseAdminPanel");
const runEvalsButton = document.querySelector("#runEvals");
const evalResults = document.querySelector("#evalResults");
const createOrderForm = document.querySelector("#createOrderForm");
const ordersList = document.querySelector("#ordersList");
const adminStats = document.querySelector("#adminStats");
const resetDatabaseButton = document.querySelector("#resetDatabase");
const purgeWorkflowButton = document.querySelector("#purgeWorkflow");
const runtimeStatus = document.querySelector("#runtimeStatus");
const CHAT_SESSION_STORAGE_KEY = "supportDeskChatSessionId";
const chatSessionId = getChatSessionId();

function getChatSessionId() {
  const existingSessionId = sessionStorage.getItem(CHAT_SESSION_STORAGE_KEY);
  if (existingSessionId) {
    return existingSessionId;
  }
  const generatedSessionId = window.crypto?.randomUUID
    ? `ui_${window.crypto.randomUUID()}`
    : `ui_${Date.now()}_${Math.random().toString(16).slice(2)}`;
  sessionStorage.setItem(CHAT_SESSION_STORAGE_KEY, generatedSessionId);
  return generatedSessionId;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function scrollChatToLatest() {
  chatLog.scrollTop = chatLog.scrollHeight;
}

function createMessageArticle(role, label) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.textContent = label;

  const paragraph = document.createElement("p");

  article.append(meta, paragraph);
  return article;
}

function appendMessage(role, label, text) {
  const article = createMessageArticle(role, label);
  article.querySelector("p").textContent = text;
  chatLog.appendChild(article);
  scrollChatToLatest();
  return article;
}

function appendThinkingMessage() {
  const article = createMessageArticle("agent pending", "Agent");
  article.setAttribute("role", "status");
  article.setAttribute("aria-live", "polite");
  article.setAttribute("aria-busy", "true");

  article.querySelector("p").innerHTML = `
    <span class="thinking-copy">Agent is thinking
      <span class="thinking-dots" aria-hidden="true">
        <span class="thinking-dot"></span>
        <span class="thinking-dot"></span>
        <span class="thinking-dot"></span>
      </span>
    </span>
  `;

  chatLog.appendChild(article);
  scrollChatToLatest();
  return article;
}

function shouldReduceMotion() {
  return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function wait(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

async function typeMessageText(article, label, text) {
  const meta = article.querySelector(".message-meta");
  const paragraph = article.querySelector("p");
  const message = String(text);

  article.classList.remove("pending");
  article.classList.add("typing");
  article.removeAttribute("role");
  article.removeAttribute("aria-busy");
  article.removeAttribute("aria-live");
  meta.textContent = label;
  paragraph.className = "";
  paragraph.textContent = "";

  if (shouldReduceMotion()) {
    paragraph.textContent = message;
    article.classList.remove("typing");
    scrollChatToLatest();
    return;
  }

  for (let index = 0; index < message.length; index += 1) {
    paragraph.textContent += message[index];
    if (index % 4 === 0 || index === message.length - 1) {
      scrollChatToLatest();
    }
    await wait(/[.!?]/.test(message[index]) ? 42 : 12);
  }

  article.classList.remove("typing");
  scrollChatToLatest();
}

function showInlineError(container, message) {
  container.innerHTML = `<div class="inline-error">${escapeHtml(message)}</div>`;
}

function focusPanel(panel) {
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
  panel.focus({ preventScroll: true });
  panel.classList.add("is-focused-panel");
  window.setTimeout(() => panel.classList.remove("is-focused-panel"), 1400);
}

function formatPercent(value) {
  return `${Math.round(Number(value) * 100)}%`;
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function refreshRuntimeStatus() {
  try {
    const health = await fetchJson("/health");
    const label =
      health.agent_runtime === "openai"
        ? `OpenAI Agents SDK · ${health.openai_model}`
        : "Local deterministic runtime";
    runtimeStatus.innerHTML = `<span class="status-dot"></span>${escapeHtml(label)}`;
    runtimeStatus.dataset.runtime = health.agent_runtime;
  } catch (error) {
    runtimeStatus.innerHTML = '<span class="status-dot"></span>Runtime unavailable';
    runtimeStatus.dataset.runtime = "error";
  }
}

async function refreshTickets() {
  try {
    const tickets = await fetchJson("/api/tickets");
    if (!tickets.length) {
      ticketList.innerHTML = '<div class="empty-state">No tickets yet.</div>';
      return;
    }
    ticketList.innerHTML = tickets
      .map((ticket) => `
        <article class="ticket-card">
          <strong>${escapeHtml(ticket.summary)}</strong>
          <span>${escapeHtml(ticket.intent)} · ${escapeHtml(ticket.status)} · ${escapeHtml(ticket.assigned_team)}</span>
        </article>
      `)
      .join("");
  } catch (error) {
    showInlineError(ticketList, "Could not load tickets.");
  }
}

async function refreshApprovals() {
  try {
    const approvals = await fetchJson("/api/approvals?status=pending");
    if (!approvals.length) {
      approvalList.innerHTML = '<div class="empty-state">No pending approval requests. Send a refund request to create one.</div>';
      return;
    }
    approvalList.innerHTML = approvals
      .map((approval) => `
        <article class="approval-card">
          <strong>Refund ${escapeHtml(approval.order_id)} · $${Number(approval.amount).toFixed(2)}</strong>
          <span>${escapeHtml(approval.status)} · ${escapeHtml(approval.risk_reason)}</span>
          <div class="approval-actions">
            <button class="approve" type="button" data-approval="${escapeHtml(approval.id)}" data-action="approve">Approve</button>
            <button class="reject" type="button" data-approval="${escapeHtml(approval.id)}" data-action="reject">Reject</button>
            <button class="escalate" type="button" data-approval="${escapeHtml(approval.id)}" data-action="reject">Escalate</button>
          </div>
        </article>
      `)
      .join("");
  } catch (error) {
    showInlineError(approvalList, "Could not load approval requests.");
  }
}

async function refreshTraces() {
  try {
    const traces = await fetchJson("/api/traces");
    if (!traces.length) {
      traceList.innerHTML = '<div class="empty-state">No agent activity yet.</div>';
      return;
    }
    traceList.innerHTML = traces
      .slice()
      .reverse()
      .slice(0, 8)
      .map((trace) => `
        <article class="trace-item">
          <strong>${escapeHtml(trace.agent_name)}</strong>
          <span>${escapeHtml(trace.event_type)}</span>
        </article>
      `)
      .join("");
  } catch (error) {
    showInlineError(traceList, "Could not load agent trace.");
  }
}

async function refreshAll() {
  await Promise.all([refreshTickets(), refreshApprovals(), refreshTraces(), refreshOrders(), refreshAdminStats()]);
}

function renderEvalReport(report) {
  const metrics = [
    ["Cases", report.total_cases],
    ["Routing accuracy", formatPercent(report.routing_accuracy)],
    ["Specialist handoff", formatPercent(report.specialist_accuracy)],
    ["Tool call accuracy", formatPercent(report.required_tool_accuracy)],
    ["Refund decisions", formatPercent(report.refund_decision_accuracy)],
    ["Guardrail pass rate", formatPercent(report.guardrail_pass_rate)],
    ["Unsupported promises", formatPercent(report.unsupported_refund_promise_rate)],
  ];
  evalResults.innerHTML = `
    <div class="metric-grid">
      ${metrics
        .map(([label, value]) => `
          <article class="metric-card">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value)}</strong>
          </article>
        `)
        .join("")}
    </div>
  `;
}

async function runEvaluations() {
  runEvalsButton.disabled = true;
  evalResults.innerHTML = '<div class="empty-state">Running evals...</div>';
  try {
    const report = await fetchJson("/api/evals/run", { method: "POST" });
    renderEvalReport(report);
  } catch (error) {
    showInlineError(evalResults, "Could not run evaluations.");
  } finally {
    runEvalsButton.disabled = false;
  }
}

function renderStats(stats) {
  const rows = [
    ["Customers", stats.customers],
    ["Orders", stats.orders],
    ["Custom orders", stats.custom_orders],
    ["Tickets", stats.tickets],
    ["Approvals", stats.approvals],
    ["Trace events", stats.traces],
  ];
  adminStats.innerHTML = `
    <div class="metric-grid">
      ${rows
        .map(([label, value]) => `
          <article class="metric-card">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value)}</strong>
          </article>
        `)
        .join("")}
    </div>
  `;
}

async function refreshAdminStats() {
  try {
    const stats = await fetchJson("/api/admin/stats");
    renderStats(stats);
  } catch (error) {
    showInlineError(adminStats, "Could not load database stats.");
  }
}

async function refreshOrders() {
  try {
    const records = await fetchJson("/api/orders");
    if (!records.length) {
      ordersList.innerHTML = '<div class="empty-state">No orders found.</div>';
      return;
    }
    ordersList.innerHTML = records
      .map(({ order, is_seed: isSeed }) => `
        <article class="order-row">
          <div>
            <strong>#${escapeHtml(order.id)} · ${escapeHtml(order.items[0]?.name || "Item")} · $${Number(order.amount).toFixed(2)}</strong>
            <span>${escapeHtml(order.status)} · ${escapeHtml(order.shipping_status)} · ${isSeed ? "seed" : "custom"}</span>
          </div>
          ${isSeed ? "" : `<button type="button" data-order="${escapeHtml(order.id)}">Delete</button>`}
        </article>
      `)
      .join("");
  } catch (error) {
    showInlineError(ordersList, "Could not load orders.");
  }
}

function orderFormPayload() {
  const deliveredAt = document.querySelector("#newOrderDeliveredAt").value;
  return {
    id: document.querySelector("#newOrderId").value.trim(),
    customer_email: document.querySelector("#newOrderEmail").value.trim(),
    status: document.querySelector("#newOrderStatus").value,
    amount: Number(document.querySelector("#newOrderAmount").value),
    item_name: document.querySelector("#newOrderItem").value.trim(),
    shipping_status: document.querySelector("#newOrderShipping").value.trim(),
    delivered_at: deliveredAt ? new Date(deliveredAt).toISOString() : null,
    is_final_sale: document.querySelector("#newOrderFinalSale").checked,
  };
}

async function createOrder(event) {
  event.preventDefault();
  try {
    const order = await fetchJson("/api/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(orderFormPayload()),
    });
    appendMessage("agent", "Database Admin", `Order #${order.id} is ready for agent testing.`);
    await Promise.all([refreshOrders(), refreshAdminStats()]);
    focusPanel(ordersPanel);
  } catch (error) {
    showInlineError(ordersList, "Could not create order. Check the customer email and order ID.");
  }
}

async function resetDatabase() {
  resetDatabaseButton.disabled = true;
  try {
    await fetchJson("/api/admin/reset", { method: "POST" });
    appendMessage("agent", "Database Admin", "Database restored to the JSON seed state.");
    await refreshAll();
    focusPanel(databaseAdminPanel);
  } catch (error) {
    showInlineError(adminStats, "Could not restore seed data.");
  } finally {
    resetDatabaseButton.disabled = false;
  }
}

async function purgeWorkflow() {
  purgeWorkflowButton.disabled = true;
  try {
    await fetchJson("/api/admin/purge-workflow", { method: "POST" });
    appendMessage("agent", "Database Admin", "Tickets, approvals, traces, and refund markers were cleared.");
    await refreshAll();
    focusPanel(databaseAdminPanel);
  } catch (error) {
    showInlineError(adminStats, "Could not clear workflow data.");
  } finally {
    purgeWorkflowButton.disabled = false;
  }
}

async function setActiveView(view) {
  navItems.forEach((item) => {
    const isActive = item.dataset.view === view;
    item.classList.toggle("active", isActive);
    item.setAttribute("aria-pressed", String(isActive));
  });

  if (view === "tickets") {
    await refreshTickets();
    focusPanel(ticketSection);
  }
  if (view === "approvals") {
    await refreshApprovals();
    focusPanel(approvalPanel);
  }
  if (view === "orders") {
    await refreshOrders();
    focusPanel(ordersPanel);
  }
  if (view === "evaluations") {
    focusPanel(evaluationPanel);
    await runEvaluations();
  }
  if (view === "database-admin") {
    await refreshAdminStats();
    focusPanel(databaseAdminPanel);
  }
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message) {
    return;
  }
  sendButton.disabled = true;
  appendMessage("customer", "Customer", message);
  const pendingAgentMessage = appendThinkingMessage();
  const minimumThinkingTime = wait(320);
  try {
    const response = await fetchJson("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: chatSessionId,
        customer_email: customerEmail.value.trim(),
        message,
      }),
    });
    messageInput.value = "";
    await minimumThinkingTime;
    await typeMessageText(pendingAgentMessage, response.agent, response.message);
    await refreshAll();
  } catch (error) {
    await minimumThinkingTime;
    await typeMessageText(pendingAgentMessage, "System", "I could not send that message. Please try again.");
  } finally {
    sendButton.disabled = false;
  }
});

approvalList.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-approval]");
  if (!button) {
    return;
  }
  const approvalId = button.dataset.approval;
  const action = button.dataset.action;
  const actionLabel = button.textContent.trim();
  button.disabled = true;
  try {
    const result = await fetchJson(`/api/approvals/${approvalId}/${action}`, { method: "POST" });
    const label = action === "approve" ? "Approval Queue" : "Escalation";
    const pastTense = actionLabel === "Reject" ? "rejected" : "escalated";
    const message = result.refund_result
      ? `Refund for order #${result.refund_result.order_id} was processed in the mock system.`
      : `Approval ${approvalId} was ${pastTense} and queued for human follow-up.`;
    appendMessage("agent", label, message);
    await refreshAll();
  } catch (error) {
    appendMessage("agent", "System", "I could not update that approval request.");
  } finally {
    button.disabled = false;
  }
});

ordersList.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-order]");
  if (!button) {
    return;
  }
  button.disabled = true;
  try {
    await fetchJson(`/api/orders/${button.dataset.order}`, { method: "DELETE" });
    await Promise.all([refreshOrders(), refreshAdminStats()]);
  } catch (error) {
    showInlineError(ordersList, "Could not delete that custom order.");
  }
});

navItems.forEach((item) => {
  item.addEventListener("click", () => {
    setActiveView(item.dataset.view);
  });
});
document.querySelector("#refreshTickets").addEventListener("click", refreshTickets);
document.querySelector("#refreshApprovals").addEventListener("click", refreshApprovals);
document.querySelector("#refreshTraces").addEventListener("click", refreshTraces);
document.querySelector("#refreshOrders").addEventListener("click", refreshOrders);
document.querySelector("#refreshAdminStats").addEventListener("click", refreshAdminStats);
runEvalsButton.addEventListener("click", runEvaluations);
createOrderForm.addEventListener("submit", createOrder);
resetDatabaseButton.addEventListener("click", resetDatabase);
purgeWorkflowButton.addEventListener("click", purgeWorkflow);

refreshRuntimeStatus();
refreshAll();
