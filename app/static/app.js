// app.js — Incident Triage Assistant dashboard.
// Plain JS, no framework. Talks to /sample_incidents and /analyze.

const $ = (sel) => document.querySelector(sel);

const select = $("#incident-select");
const shortInput = $("#short-desc");
const longInput = $("#long-desc");
const analyzeBtn = $("#analyze-btn");
const statusEl = $("#status");
const resultsBlock = $("#results");
const artifactBody = $("#artifact-body");

let lastResult = null;
let activeTab = "user_summary";

// ---- 1. Populate the dropdown ----------------------------------------------
async function loadIncidents() {
  try {
    const res = await fetch("/sample_incidents");
    const items = await res.json();
    select.innerHTML = '<option value="">— pick an incident —</option>';
    for (const it of items) {
      const opt = document.createElement("option");
      opt.value = it.number;
      opt.textContent = `${it.number}  ·  ${it.short_description}`;
      select.appendChild(opt);
    }
  } catch (err) {
    select.innerHTML = '<option value="">— failed to load —</option>';
    console.error(err);
  }
}

// ---- 2. Click handler ------------------------------------------------------
analyzeBtn.addEventListener("click", async () => {
  analyzeBtn.disabled = true;
  statusEl.textContent = "Analyzing…";
  resultsBlock.classList.add("hidden");

  try {
    const body = select.value
      ? { incident_number: select.value }
      : {
          short_description: shortInput.value.trim(),
          description: longInput.value.trim(),
        };

    const res = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Analyze failed");

    lastResult = data;
    renderResults(data);
    statusEl.textContent = "Done";
    resultsBlock.classList.remove("hidden");
  } catch (err) {
    statusEl.textContent = "Error: " + err.message;
  } finally {
    analyzeBtn.disabled = false;
  }
});

// ---- 3. Renderers ----------------------------------------------------------
function renderResults(data) {
  renderPredictions(data.predictions);
  renderKbas(data.kba_matches, data.kba_threshold);
  renderSimilar(data.similar_incidents);
  showArtifact(activeTab, data.rendered);
}

function renderPredictions(preds) {
  $("#ag-top").innerHTML = predBlock(preds.assignment_group);
  $("#bs-top").innerHTML = predBlock(preds.business_service);

  $("#ag-list").innerHTML = preds.assignment_group.top3
    .map((p) => `<li><span>${escapeHtml(p.label)}</span><span>${(p.prob * 100).toFixed(1)}%</span></li>`)
    .join("");
  $("#bs-list").innerHTML = preds.business_service.top3
    .map((p) => `<li><span>${escapeHtml(p.label)}</span><span>${(p.prob * 100).toFixed(1)}%</span></li>`)
    .join("");
}

function predBlock(p) {
  return `
    <span class="pred-top">${escapeHtml(p.top1)}</span>
    <span class="pred-conf">${(p.top1_prob * 100).toFixed(1)}% confidence</span>
  `;
}

function renderKbas(matches, threshold) {
  const note = `Threshold: similarity ≥ ${threshold}. Below this, no recommendation is shown.`;
  $("#kba-threshold-note").textContent = note;

  const list = $("#kba-list");
  if (!matches || matches.length === 0) {
    list.innerHTML = `<div class="no-match">⚠️  No strong KBA match found. The IT team will work on this directly.</div>`;
    return;
  }
  list.innerHTML = matches
    .map((m) => {
      const lowClass = m.score < (window.KBA_THRESHOLD + 0.05) ? " low" : "";
      return `
        <div class="kba-card">
          <div class="kba-header">
            <strong>${escapeHtml(m.short_description)}</strong>
            <span class="score-pill${lowClass}">${m.score.toFixed(3)}</span>
          </div>
          <div class="kba-id">${escapeHtml(m.kb_number)}</div>
          <div>${escapeHtml(m.introduction || "")}</div>
        </div>
      `;
    })
    .join("");
}

function renderSimilar(items) {
  const list = $("#similar-list");
  if (!items || items.length === 0) {
    list.innerHTML = `<div class="muted">No similar incidents found.</div>`;
    return;
  }
  list.innerHTML = items
    .map((s) => `
      <div class="similar-card">
        <div class="similar-header">
          <strong>${escapeHtml(s.short_description)}</strong>
          <span class="score-pill">${s.score.toFixed(3)}</span>
        </div>
        <div class="similar-id">${escapeHtml(s.number)} · ${escapeHtml(s.assignment_group)} · close: ${escapeHtml(s.close_code)}</div>
        <div class="muted" style="margin-top:6px">${escapeHtml(s.close_notes_excerpt || "")}</div>
      </div>
    `)
    .join("");
}

// ---- 4. Tabs ---------------------------------------------------------------
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    activeTab = btn.dataset.tab;
    if (lastResult) showArtifact(activeTab, lastResult.rendered);
  });
});

function showArtifact(tab, rendered) {
  artifactBody.textContent = rendered[tab] || "(empty)";
}

// ---- 5. Utilities ----------------------------------------------------------
function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

loadIncidents();
