// ============================================================
//  components/stats.js — Stat cards rendering
// ============================================================
 
const CARD_VARIANTS = ['teal', 'amber', 'rose'];
const STAT_KEYS = ['searches', 'flagged', 'blocked'];
 
export function renderStats(stats) {
  const el = document.getElementById('stats-grid');
  if (!el) return;
 
  el.innerHTML = STAT_KEYS.map((key, i) => {
    const s = stats[key];
    const variant = CARD_VARIANTS[i];
    return `
      <div class="stat-card stat-card--${variant} reveal reveal-${i + 1}">
        <div class="card-eyebrow">${s.label}</div>
        <div class="stat-numeral">${s.value}</div>
        <div class="stat-sub">this week</div>
      </div>
    `;
  }).join('');
}
 