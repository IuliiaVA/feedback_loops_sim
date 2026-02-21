// ============================================================================
//  Feedback Loops Simulation — Frontend
//  Pure vanilla JS with HTML Canvas charts (no external libraries).
// ============================================================================

// ── Slider wiring ──────────────────────────────────────────────────────────
var SLIDERS = [
  ["s-tu",  "v-tu",  2], ["s-au",  "v-au",  2], ["s-ru",  "v-ru",  2],
  ["s-thr", "v-thr", 2], ["s-bhr", "v-bhr", 2],
  ["s-lr",  "v-lr",  2], ["s-dr",  "v-dr",  2],
  ["s-fw",  "v-fw",  2], ["s-it",  "v-it",  0], ["s-n",   "v-n",   0],
  ["s-gi",  "v-gi",  2],
];
SLIDERS.forEach(function(s) {
  var el = document.getElementById(s[0]);
  el.addEventListener("input", function() {
    document.getElementById(s[1]).textContent =
      s[2] > 0 ? parseFloat(el.value).toFixed(s[2]) : el.value;
  });
});

// ── Gather params ──────────────────────────────────────────────────────────
function getParams() {
  return {
    t_user:           parseFloat(document.getElementById("s-tu").value),
    a_user:           parseFloat(document.getElementById("s-au").value),
    r_user:           parseFloat(document.getElementById("s-ru").value),
    t_hr:             parseFloat(document.getElementById("s-thr").value),
    b_hr:             parseFloat(document.getElementById("s-bhr").value),
    lr:               parseFloat(document.getElementById("s-lr").value),
    diversity_reg:    parseFloat(document.getElementById("s-dr").value),
    feedback_weight:  parseFloat(document.getElementById("s-fw").value),
    iterations:       parseInt(document.getElementById("s-it").value),
    n_agents:         parseInt(document.getElementById("s-n").value),
    group_imbalance:  parseFloat(document.getElementById("s-gi").value),
    seed:             42,
  };
}

// ── Pure Canvas Mini-Chart Engine ──────────────────────────────────────────
// Draws line charts on a <canvas> element.  No external dependencies.

var COLORS = {
  blue: "#4a9eff",
  red: "#ff6b6b",
  green: "#4ecb71",
  orange: "#f0a050",
  gray: "#a0a4b8",
  purple: "#b07aff",
};

// Chart config: { canvas, series: [{data:[], color, label}], yLabel, xLabel }
function drawChart(cfg) {
  var canvas = cfg.canvas;
  var ctx = canvas.getContext("2d");
  var W = canvas.width = canvas.offsetWidth * (window.devicePixelRatio || 1);
  var H = canvas.height = canvas.offsetHeight * (window.devicePixelRatio || 1);
  ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
  var w = canvas.offsetWidth;
  var h = canvas.offsetHeight;

  var pad = { l: 46, r: 14, t: 10, b: 26 };
  var plotW = w - pad.l - pad.r;
  var plotH = h - pad.t - pad.b;

  ctx.clearRect(0, 0, w, h);

  // Compute Y range across all series
  var allVals = [];
  cfg.series.forEach(function(s) { s.data.forEach(function(v) { allVals.push(v); }); });
  var yMin = Math.min.apply(null, allVals);
  var yMax = Math.max.apply(null, allVals);
  // Add margin
  var yRange = yMax - yMin;
  if (yRange < 0.001) { yMin -= 0.05; yMax += 0.05; yRange = 0.1; }
  yMin -= yRange * 0.08;
  yMax += yRange * 0.08;
  yRange = yMax - yMin;

  var n = cfg.series[0].data.length;

  // Map functions
  function xMap(i) { return pad.l + (i / Math.max(n - 1, 1)) * plotW; }
  function yMap(v) { return pad.t + plotH - ((v - yMin) / yRange) * plotH; }

  // Grid lines
  ctx.strokeStyle = "#2e3348";
  ctx.lineWidth = 0.5;
  var nTicks = 5;
  for (var ti = 0; ti <= nTicks; ti++) {
    var yv = yMin + (ti / nTicks) * yRange;
    var yy = yMap(yv);
    ctx.beginPath(); ctx.moveTo(pad.l, yy); ctx.lineTo(w - pad.r, yy); ctx.stroke();
    // Label
    ctx.fillStyle = "#6a6e85";
    ctx.font = "9px Consolas, monospace";
    ctx.textAlign = "right";
    ctx.fillText(yv.toFixed(2), pad.l - 4, yy + 3);
  }

  // X axis labels
  ctx.fillStyle = "#6a6e85";
  ctx.font = "9px Consolas, monospace";
  ctx.textAlign = "center";
  var xStep = Math.max(1, Math.floor(n / 8));
  for (var xi = 0; xi < n; xi += xStep) {
    ctx.fillText(xi.toString(), xMap(xi), h - 4);
  }
  // Last tick
  if ((n - 1) % xStep !== 0) {
    ctx.fillText((n - 1).toString(), xMap(n - 1), h - 4);
  }

  // Draw series
  cfg.series.forEach(function(s) {
    ctx.strokeStyle = s.color;
    ctx.lineWidth = 1.8;
    ctx.lineJoin = "round";
    ctx.beginPath();
    for (var i = 0; i < s.data.length; i++) {
      var px = xMap(i);
      var py = yMap(s.data[i]);
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.stroke();

    // Dots
    ctx.fillStyle = s.color;
    for (var i = 0; i < s.data.length; i++) {
      ctx.beginPath();
      ctx.arc(xMap(i), yMap(s.data[i]), 2.2, 0, Math.PI * 2);
      ctx.fill();
    }
  });

  // Legend (top-right, outside plot area to avoid overlap)
  ctx.font = "9px 'Segoe UI', sans-serif";
  var legendW = 0;
  // Measure widest label
  cfg.series.forEach(function(s) {
    var tw = ctx.measureText(s.label).width + 16;
    if (tw > legendW) legendW = tw;
  });
  var lx = w - pad.r - legendW - 2;
  var ly = pad.t + 2;
  // Draw semi-transparent background so legend is readable over grid
  var lh = cfg.series.length * 13 + 4;
  ctx.fillStyle = "rgba(26,29,39,0.85)";
  ctx.fillRect(lx - 4, ly - 6, legendW + 8, lh);
  cfg.series.forEach(function(s, idx) {
    var y = ly + idx * 13;
    ctx.fillStyle = s.color;
    ctx.fillRect(lx, y - 3, 8, 3);
    ctx.fillStyle = "#c0c4d8";
    ctx.textAlign = "left";
    ctx.fillText(s.label, lx + 12, y + 1);
  });
}

// ── Render results ─────────────────────────────────────────────────────────

function render(data) {
  var iters = data.iterations;
  var area = document.getElementById("charts-area");

  // Extract arrays
  var n = iters.length;
  function col(key) { var a = []; for (var i = 0; i < n; i++) a.push(iters[i][key]); return a; }

  var expA = col("exposure_high_A");
  var expB = col("exposure_high_B");
  var choA = col("choice_high_A");
  var choB = col("choice_high_B");
  var accA = col("acceptance_rate_A");
  var accB = col("acceptance_rate_B");
  var divA = col("diversity_entropy_A");
  var divB = col("diversity_entropy_B");
  var phA  = col("p_high_A");
  var phB  = col("p_high_B");
  var dExp = col("disparity_exposure");
  var dAcc = col("disparity_accept");
  var rIdx = col("reinforcement_index");

  area.innerHTML = ""
    // Group-level comparisons
    + '<div class="section-label">Group-Level Dynamics</div>'
    + '<div class="row3">'
    + '  <div class="card"><h3>Exposure to HIGH</h3><canvas id="c-exp"></canvas></div>'
    + '  <div class="card"><h3>Choice of HIGH</h3><canvas id="c-cho"></canvas></div>'
    + '  <div class="card"><h3>Diversity Entropy</h3><canvas id="c-div"></canvas></div>'
    + '</div>'
    // System-level
    + '<div class="section-label">System-Level Dynamics</div>'
    + '<div class="row3">'
    + '  <div class="card"><h3>Learned Recommendation Probability</h3><canvas id="c-ph"></canvas></div>'
    + '  <div class="card"><h3>Inequality (Exposure &amp; Acceptance)</h3><canvas id="c-disp"></canvas></div>'
    + '  <div class="card"><h3>Reinforcement Index</h3><canvas id="c-ri"></canvas></div>'
    + '</div>';

  // Render all charts after DOM paint
  requestAnimationFrame(function() {
    drawChart({ canvas: document.getElementById("c-exp"), series: [
      { data: expA, color: COLORS.blue, label: "Group A" },
      { data: expB, color: COLORS.red, label: "Group B" },
    ]});
    drawChart({ canvas: document.getElementById("c-cho"), series: [
      { data: choA, color: COLORS.blue, label: "Group A" },
      { data: choB, color: COLORS.red, label: "Group B" },
    ]});
    drawChart({ canvas: document.getElementById("c-div"), series: [
      { data: divA, color: COLORS.blue, label: "Group A" },
      { data: divB, color: COLORS.red, label: "Group B" },
    ]});
    drawChart({ canvas: document.getElementById("c-ph"), series: [
      { data: phA, color: COLORS.blue, label: "Group A" },
      { data: phB, color: COLORS.red, label: "Group B" },
    ]});
    drawChart({ canvas: document.getElementById("c-disp"), series: [
      { data: dExp, color: COLORS.orange, label: "Exposure gap" },
      { data: dAcc, color: COLORS.purple, label: "Accept. gap" },
    ]});
    drawChart({ canvas: document.getElementById("c-ri"), series: [
      { data: rIdx, color: COLORS.gray, label: "Reinforcement" },
    ]});
  });
}

// ── Run simulation ─────────────────────────────────────────────────────────

function runSim() {
  var btn = document.getElementById("btn-run");
  var st = document.getElementById("status");
  btn.disabled = true;
  st.className = "status";
  st.textContent = "Running...";

  var params = getParams();

  var xhr = new XMLHttpRequest();
  xhr.open("POST", "/api/run", true);
  xhr.setRequestHeader("Content-Type", "application/json");
  xhr.onload = function() {
    if (xhr.status === 200) {
      var data = JSON.parse(xhr.responseText);
      render(data);
      st.className = "status ok";
      st.textContent = "Done — " + params.iterations + " iterations, " + params.n_agents + " agents";
    } else {
      st.className = "status err";
      st.textContent = "Error: " + xhr.statusText;
    }
    btn.disabled = false;
  };
  xhr.onerror = function() {
    st.className = "status err";
    st.textContent = "Network error";
    btn.disabled = false;
  };
  xhr.send(JSON.stringify(params));
}

document.getElementById("btn-run").addEventListener("click", runSim);

// Auto-run on load
window.addEventListener("DOMContentLoaded", function() {
  setTimeout(runSim, 200);
});
