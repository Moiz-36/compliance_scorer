let activeTab = "pdf";
let selectedFile = null;

document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    activeTab = btn.dataset.tab;
    document.querySelector(`.tab-panel[data-panel="${activeTab}"]`).classList.add("active");
  });
});

document.getElementById("pdf-input").addEventListener("change", (e) => {
  selectedFile = e.target.files[0] || null;
  document.getElementById("pdf-filename").textContent = selectedFile ? selectedFile.name : "";
});

const runBtn = document.getElementById("run-btn");
const progressEl = document.getElementById("progress");
const progressFill = document.getElementById("progress-fill");
const progressLabel = document.getElementById("progress-label");
const errorEl = document.getElementById("error-msg");
const reportEl = document.getElementById("report");

function showError(msg) { errorEl.textContent = msg; errorEl.hidden = false; }
function clearError() { errorEl.hidden = true; }

async function startJob() {
  clearError();
  reportEl.hidden = true;

  let response;
  try {
    if (activeTab === "pdf") {
      if (!selectedFile) return showError("Choose a PDF file first.");
      const formData = new FormData();
      formData.append("file", selectedFile);
      response = await fetch("/api/evaluate/pdf", { method: "POST", body: formData });
    } else if (activeTab === "text") {
      const text = document.getElementById("text-input").value.trim();
      if (!text) return showError("Paste some policy text first.");
      response = await fetch("/api/evaluate/text", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }),
      });
    } else {
      const url = document.getElementById("url-input").value.trim();
      if (!url) return showError("Paste a policy URL first.");
      response = await fetch("/api/evaluate/url", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url }),
      });
    }
  } catch (err) {
    return showError(`Network error: ${err.message}`);
  }
  if (response.status === 503) {
    return showError("The server is warming up (first load after inactivity) — please wait a few seconds and try again.");
  }

  const data = await response.json();
  if (!response.ok) return showError(data.error || "Something went wrong.");

  runBtn.disabled = true;
  progressEl.hidden = false;
  pollJob(data.job_id);
}

async function pollJob(jobId) {
  const poll = async () => {
    const res = await fetch(`/api/evaluate/status/${jobId}`);
    const job = await res.json();

    if (job.status === "processing" || job.status === "queued") {
      const pct = job.total ? Math.round((job.completed / job.total) * 100) : 0;
      progressFill.style.width = `${pct}%`;
      progressLabel.textContent = `Reviewing requirement ${job.completed} of ${job.total}…`;
      setTimeout(poll, 800);
    } else if (job.status === "done") {
      progressEl.hidden = true;
      runBtn.disabled = false;
      renderReport(job.report);
    } else if (job.status === "error") {
      progressEl.hidden = true;
      runBtn.disabled = false;
      showError(job.error || "Evaluation failed.");
    }
  };
  poll();
}

function renderReport(report) {
  reportEl.hidden = false;

  document.getElementById("stamp-score").textContent = `${Math.round(report.overall_score)}%`;
  const ring = document.getElementById("stamp-ring");
  const circumference = 2 * Math.PI * 80;
  ring.style.strokeDashoffset = circumference - (report.overall_score / 100) * circumference;

  const catEl = document.getElementById("categories");
  catEl.innerHTML = "";
  Object.entries(report.category_scores).forEach(([name, score]) => {
    const card = document.createElement("div");
    card.className = "category-card";
    card.innerHTML = `
      <p class="category-name">${name}</p>
      <p class="category-score">${score}%</p>
      <div class="category-track"><div class="category-fill" style="width:${score}%"></div></div>
    `;
    catEl.appendChild(card);
  });

  const ledgerEl = document.getElementById("ledger");
  ledgerEl.innerHTML = "";
  const icons = { SATISFIED: "✓", PARTIAL: "~", MISSING: "✕" };
  const classes = { SATISFIED: "satisfied", PARTIAL: "partial", MISSING: "missing" };

  report.evaluations.forEach(e => {
    const row = document.createElement("div");
    row.className = "finding";
    row.innerHTML = `
      <div class="finding-head">
        <span class="finding-status ${classes[e.status]}">${icons[e.status]}</span>
        <span class="finding-id">${e.requirement_id}</span>
        <span class="finding-desc">${e.requirement_desc}</span>
      </div>
      <div class="finding-body">
        ${e.evidence_text ? `<strong>Evidence:</strong> "${e.evidence_text.slice(0, 280)}${e.evidence_text.length > 280 ? "…" : ""}"` : "No matching evidence found in the policy."}
        <br><strong>Confidence:</strong> ${(e.confidence_score * 100).toFixed(1)}%
      </div>
    `;
    row.querySelector(".finding-head").addEventListener("click", () => row.classList.toggle("expanded"));
    ledgerEl.appendChild(row);
  });
}

runBtn.addEventListener("click", startJob);

document.getElementById("reset-btn").addEventListener("click", async () => {
  await fetch("/api/reset", { method: "POST" });
  reportEl.hidden = true;
  document.getElementById("text-input").value = "";
  document.getElementById("url-input").value = "";
  document.getElementById("pdf-filename").textContent = "";
  selectedFile = null;
  document.getElementById("pdf-input").value = "";
});