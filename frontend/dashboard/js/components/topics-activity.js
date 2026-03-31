// ============================================================
//  components/topics-activity.js — Topics cloud & timeline
// ============================================================
 
// ── SVG icon paths ────────────────────────────────────────────
const ICONS = {
    alert: `<polyline points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>`,
    globe: `<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>`,
    check: `<polyline points="20 6 9 17 4 12"/>`,
    block: `<circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>`
  };
   
  const DOT_VARIANT = { rose: 'tl-dot--rose', teal: 'tl-dot--teal', amber: 'tl-dot--amber', sage: 'tl-dot--sage', subtle: 'tl-dot--subtle' };
  const ICON_COLOR  = { rose: 'icon-rose', teal: 'icon-teal', amber: 'icon-amber', sage: 'icon-sage', dim: 'icon-dim' };
   
  export function renderTopics(topics) {
    const el = document.getElementById('topics-cloud');
    if (!el) return;
   
    el.innerHTML = topics.map(t => `
      <div class="topic-pill">
        <span class="topic-swatch ${t.swatch}"></span>
        <span class="topic-pill-label">${t.label}</span>
        <span class="topic-pill-count">${t.count}</span>
      </div>
    `).join('');
  }
   
  export function renderActivity(activity) {
    const el = document.getElementById('timeline');
    if (!el) return;
   
    el.innerHTML = activity.map(item => {
      const dotCls  = DOT_VARIANT[item.type]  || DOT_VARIANT.subtle;
      const iconCls = ICON_COLOR[item.type]   || ICON_COLOR.dim;
      const iconPath = ICONS[item.icon]       || ICONS.check;
   
      return `
        <div class="tl-row">
          <div class="tl-spine">
            <div class="tl-dot ${dotCls}">
              <svg class="tl-icon ${iconCls}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" stroke-linecap="round" stroke-linejoin="round">
                ${iconPath}
              </svg>
            </div>
          </div>
          <div class="tl-content">
            <div class="tl-action">${item.action}</div>
            <div class="tl-when">${item.when}</div>
          </div>
        </div>
      `;
    }).join('');
  }
   