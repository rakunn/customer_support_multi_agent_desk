const chatForm = document.querySelector("#chatForm");
const chatLog = document.querySelector("#chatLog");
const messageInput = document.querySelector("#messageInput");
const customerEmail = document.querySelector("#customerEmail");
const ticketList = document.querySelector("#ticketList");
const approvalList = document.querySelector("#approvalList");
const traceList = document.querySelector("#traceList");

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function appendMessage(role, label, text) {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  article.innerHTML = `
    <div class="message-meta">${escapeHtml(label)}</div>
    <p>${escapeHtml(text)}</p>
  `;
  chatLog.appendChild(article);
  chatLog.scrollTop = chatLog.scrollHeight;
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function refreshTickets() {
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
}

async function refreshApprovals() {
  const approvals = await fetchJson("/api/approvals");
  if (!approvals.length) {
    approvalList.innerHTML = '<div class="empty-state">No pending approval requests.</div>';
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
}

async function refreshTraces() {
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
}

async function refreshAll() {
  await Promise.all([refreshTickets(), refreshApprovals(), refreshTraces()]);
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message) {
    return;
  }
  appendMessage("customer", "Customer", message);
  const response = await fetchJson("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: `ui_${Date.now()}`,
      customer_email: customerEmail.value.trim(),
      message,
    }),
  });
  appendMessage("agent", response.agent, response.message);
  await refreshAll();
});

approvalList.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-approval]");
  if (!button) {
    return;
  }
  const approvalId = button.dataset.approval;
  const action = button.dataset.action;
  const result = await fetchJson(`/api/approvals/${approvalId}/${action}`, { method: "POST" });
  const label = action === "approve" ? "Approval Queue" : "Escalation";
  const message = result.refund_result
    ? `Refund for order #${result.refund_result.order_id} was processed in the mock system.`
    : `Approval ${approvalId} was rejected and escalated for human follow-up.`;
  appendMessage("agent", label, message);
  await refreshAll();
});

document.querySelector("#refreshTickets").addEventListener("click", refreshTickets);
document.querySelector("#refreshApprovals").addEventListener("click", refreshApprovals);
document.querySelector("#refreshTraces").addEventListener("click", refreshTraces);

refreshAll();
