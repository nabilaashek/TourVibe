/* TourVibe — small progressive-enhancement scripts (the site also works without JS). */

function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^|;\\s*)' + name + '=([^;]*)'));
  return match ? decodeURIComponent(match[2]) : null;
}

function readJson(id, fallback) {
  const el = document.getElementById(id);
  if (!el) return fallback;
  try { return JSON.parse(el.textContent); } catch (e) { return fallback; }
}

const taka = (n) => '৳' + Math.round(Number(n) || 0).toLocaleString('en-IN');

/* Wishlist heart: toggle without reloading the page. */
document.addEventListener('submit', async (event) => {
  const form = event.target.closest('form.js-wishlist');
  if (!form) return;
  event.preventDefault();
  try {
    const response = await fetch(form.action, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin',
    });
    if (response.redirected || !response.ok) { form.submit(); return; }
    const data = await response.json();
    const icon = form.querySelector('i');
    if (icon) icon.className = data.saved ? 'bi bi-heart-fill' : 'bi bi-heart';
    const label = form.querySelector('.wish-label');
    if (label) label.textContent = data.saved ? 'Saved' : 'Save';
    document.querySelectorAll('.js-wishlist-count').forEach((el) => { el.textContent = data.count; });
  } catch (e) {
    form.submit();
  }
});

/* Charts (Chart.js) — data comes from Django's json_script tag. */
function drawChart(canvasId, type, labels, values, options = {}) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === 'undefined') return;
  const palette = ['#0f766e', '#f59e0b', '#ef4444', '#0ea5e9', '#8b5cf6', '#22c55e', '#64748b', '#ec4899'];
  const round = type === 'doughnut' || type === 'pie';
  new Chart(canvas, {
    type,
    data: {
      labels,
      datasets: [{
        label: options.label || '',
        data: values,
        backgroundColor: round ? palette : 'rgba(15,118,110,.15)',
        borderColor: round ? '#fff' : '#0f766e',
        borderWidth: 2,
        fill: type === 'line',
        tension: .35,
        borderRadius: type === 'bar' ? 8 : 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: round, position: 'bottom' } },
      scales: round ? {} : { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
}

/* Trip planner: live cost preview through the REST API (/api/planner/estimate/). */
(function livePlanner() {
  const form = document.getElementById('planner-form');
  const box = document.getElementById('live-estimate');
  if (!form || !box) return;
  let timer;

  async function update() {
    const destinations = Array.from(form.querySelectorAll('[name=places]:checked')).map((o) => o.value);
    const body = {
      places: destinations,
      days: Number(form.days.value),
      travelers: Number(form.travelers.value),
      budget: form.budget.value,
      transport: form.transport.value,
    };
    if (!destinations.length || !body.days || !body.travelers) {
      box.innerHTML = '<span class="text-muted">Choose destinations to see a live estimate.</span>';
      return;
    }
    try {
      const response = await fetch(box.dataset.url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        credentials: 'same-origin',
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (!response.ok) {
        const message = data.detail || Object.values(data).flat().join(' ');
        box.innerHTML = '<span class="text-danger"></span>';
        box.firstChild.textContent = message;
        return;
      }
      box.innerHTML =
        '<div class="small text-muted">Live estimate</div>' +
        '<div class="cost-total">' + taka(data.total) + '</div>' +
        '<div class="small">' + taka(data.per_person) + ' per person · about ' +
        data.distance_km.toLocaleString() + ' km of travel</div>';
    } catch (e) {
      box.innerHTML = '<span class="text-muted">Live estimate is unavailable right now.</span>';
    }
  }

  form.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(update, 300); });
  form.addEventListener('change', () => { clearTimeout(timer); timer = setTimeout(update, 100); });
  update();
})();
