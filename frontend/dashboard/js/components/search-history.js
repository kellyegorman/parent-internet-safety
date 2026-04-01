// ============================================================
//  components/search-history.js — Search list rendering
// ============================================================
 
const MARK_CLASS = {
    sports:  'mark-sports',
    gaming:  'mark-gaming',
    celeb:   'mark-celeb',
    flagged: 'mark-flagged',
    default: 'mark-default'
  };
   
  const STATUS_BADGE = {
    safe:    { cls: 'badge-safe',    label: 'Safe'    },
    review:  { cls: 'badge-review',  label: 'Review'  },
    blocked: { cls: 'badge-blocked', label: 'Blocked' }
  };
   
  export function renderSearchHistory(searches) {
    const el = document.getElementById('search-list');
    if (!el) return;
   
    el.innerHTML = searches.map(s => {
      const mark  = MARK_CLASS[s.category] || 'mark-default';
      const badge = STATUS_BADGE[s.status] || STATUS_BADGE.safe;
      const isFlagged = s.status === 'review' || s.status === 'blocked';
   
      return `
        <div class="search-item ${isFlagged ? 'search-item--flagged' : ''}" data-id="${s.id}">
          <span class="search-type-mark ${mark}"></span>
          <div class="search-text">
            <div class="search-query-text">${s.query}</div>
            <div class="search-timestamp">${s.time}</div>
          </div>
          <span class="badge ${badge.cls} search-item-badge">${badge.label}</span>
        </div>
      `;
    }).join('');
  }
   