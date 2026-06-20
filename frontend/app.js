const chatForm = document.querySelector("#chatForm");
const chatLog = document.querySelector("#chatLog");
const messageInput = document.querySelector("#messageInput");
const customerEmail = document.querySelector("#customerEmail");
const ticketList = document.querySelector("#ticketList");
const approvalList = document.querySelector("#approvalList");
const traceList = document.querySelector("#traceList");
const navItems = document.querySelectorAll(".nav-item[data-view]");
const ticketSection = document.querySelector(".ticket-section");
const approvalPanel = document.querySelector("#approvalPanel");
const evaluationPanel = document.querySelector("#evaluationPanel");
const runEvalsButton = document.querySelector("#runEvals");
const evalResults = document.querySelector("#evalResults");

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
      approvalList.innerHTML = '<div class="empty-state">No pending approval requests. Send the sample refund message to create one.</div>';
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
  await Promise.all([refreshTickets(), refreshApprovals(), refreshTraces()]);
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
  if (view === "evaluations") {
    focusPanel(evaluationPanel);
    await runEvaluations();
  }
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message) {
    return;
  }
  appendMessage("customer", "Customer", message);
  try {
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
  } catch (error) {
    appendMessage("agent", "System", "I could not send that message. Please try again.");
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

navItems.forEach((item) => {
  item.addEventListener("click", () => {
    setActiveView(item.dataset.view);
  });
});
document.querySelector("#refreshTickets").addEventListener("click", refreshTickets);
document.querySelector("#refreshApprovals").addEventListener("click", refreshApprovals);
document.querySelector("#refreshTraces").addEventListener("click", refreshTraces);
runEvalsButton.addEventListener("click", runEvaluations);

refreshAll();
