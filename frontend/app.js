const API = "";

// Fixed layout for the known demo module set so the graph reads cleanly.
// Falls back to a simple grid for any unknown module names.
const LAYOUT = {
  "Coupon":       { x: 80,  y: 40 },
  "Cart":         { x: 80,  y: 140 },
  "Inventory":    { x: 320, y: 40 },
  "Checkout":     { x: 200, y: 240 },
  "Payment":      { x: 80,  y: 340 },
  "Order":        { x: 320, y: 340 },
  "Notification": { x: 320, y: 440 },
};

function layoutFor(nodes) {
  const positions = {};
  let gx = 0, gy = 0;
  nodes.forEach((n) => {
    if (LAYOUT[n]) {
      positions[n] = LAYOUT[n];
    } else {
      positions[n] = { x: 80 + (gx % 3) * 220, y: 500 + gy * 100 };
      gx++; if (gx % 3 === 0) gy++;
    }
  });
  return positions;
}

function renderGraph(container, graph) {
  const nodes = graph.nodes.map((n) => n.id);
  const impactedSet = new Set(graph.nodes.filter((n) => n.impacted).map((n) => n.id));
  const pos = layoutFor(nodes);

  const width = 460;
  const height = Math.max(...Object.values(pos).map((p) => p.y)) + 80;

  let svg = `<svg class="graph-svg" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg">`;
  svg += `<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
            <path d="M0,0 L0,6 L7,3 z" fill="#8b90a3" /></marker></defs>`;

  // edges
  graph.edges.forEach((e) => {
    const a = pos[e.from], b = pos[e.to];
    if (!a || !b) return;
    const impacted = impactedSet.has(e.from) && impactedSet.has(e.to);
    svg += `<line x1="${a.x + 45}" y1="${a.y + 16}" x2="${b.x + 45}" y2="${b.y}"
             class="${impacted ? "edge-line-impacted" : "edge-line"}" />`;
  });

  // nodes
  nodes.forEach((n) => {
    const p = pos[n];
    const impacted = impactedSet.has(n);
    svg += `<g>
      <rect x="${p.x}" y="${p.y}" width="90" height="32" rx="8"
        class="${impacted ? "node-impacted" : "node-normal"}" />
      <text x="${p.x + 45}" y="${p.y + 20}" text-anchor="middle" class="node-text">${n}</text>
    </g>`;
  });

  svg += `</svg>`;
  container.innerHTML = svg;
}

async function loadFullGraph() {
  const res = await fetch(`${API}/api/graph`);
  const graph = await res.json();
  renderGraph(document.getElementById("full-graph"), graph);
}

function renderScenarios(scenarios) {
  const ol = document.getElementById("scenarios-out");
  ol.innerHTML = scenarios.map((s) => `<li>${s}</li>`).join("");
}

function renderCauses(causes) {
  const el = document.getElementById("causes-out");
  el.innerHTML = causes.map((c) => `
    <div class="cause-row">
      <div class="cause-label">${c.cause}</div>
      <div class="bar-bg"><div class="bar-fill" style="width:${c.confidence_percent}%"></div></div>
      <div class="cause-pct">${c.confidence_percent}%</div>
    </div>
  `).join("") + `<p class="muted">Confidence = heuristic score from keyword signal (60%) + historical frequency for this module (40%). Not a trained-model probability.</p>`;
}

function renderRelated(related) {
  const el = document.getElementById("related-out");
  if (!related.length) {
    el.innerHTML = `<p class="muted">No sufficiently similar historical bug found.</p>`;
    return;
  }
  el.innerHTML = related.map((b) => `
    <div class="bug-chip">
      <span>⚠️ <strong>${b.code}</strong> — ${b.title} <span class="muted">(${b.module})</span></span>
      <span class="sim">${b.similarity_percent}% similar</span>
    </div>
  `).join("");
}

function renderRegression(impacted, tests) {
  const el = document.getElementById("regression-out");
  const pills = impacted.map((m) => `<span class="module-pill">✓ ${m}</span>`).join("");
  const rows = tests.map((t) => `
    <tr>
      <td>${t.name}</td>
      <td>${t.module}</td>
      <td class="priority-${t.priority}">${t.priority}</td>
    </tr>
  `).join("");
  el.innerHTML = `
    <p>${pills}</p>
    <p class="muted">${tests.length} regression tests recommended</p>
    <table class="reg-table">
      <thead><tr><th>Test case</th><th>Module</th><th>Priority</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

async function analyze() {
  const title = document.getElementById("title").value.trim();
  const description = document.getElementById("description").value.trim();
  if (!title || !description) {
    alert("Please enter both a title and a description.");
    return;
  }

  document.getElementById("loading").classList.remove("hidden");
  document.getElementById("results").classList.add("hidden");

  try {
    const res = await fetch(`${API}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, description }),
    });
    const data = await res.json();

    document.getElementById("module-out").textContent = data.detected_module;
    const kw = data.classification.matched_keywords || [];
    document.getElementById("keywords-out").textContent =
      kw.length ? `Matched keywords: ${kw.join(", ")}` : "";

    renderScenarios(data.scenarios);
    renderCauses(data.root_causes);
    renderRelated(data.related_bugs);
    renderGraph(document.getElementById("graph-out"), data.graph);
    renderRegression(data.impacted_modules, data.regression_tests);
    document.getElementById("strategy-out").textContent = data.strategy.recommendation;

    document.getElementById("results").classList.remove("hidden");
  } catch (err) {
    alert("Something went wrong: " + err.message);
  } finally {
    document.getElementById("loading").classList.add("hidden");
  }
}

document.getElementById("analyze-btn").addEventListener("click", analyze);
loadFullGraph();
