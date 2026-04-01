// ============================================================
//  components/header.js — Site header rendering & behavior
// ============================================================
 
import { db } from '../data/db.js';
 
export function renderHeader(alertCount) {
  const el = document.getElementById('header');
  if (!el) return;
 
  el.innerHTML = `
    <div class="header-brand">
      <div class="brand-logotype">Parent+Child<em>   Internet Safety</em></div>
      <div class="brand-sub">Parental Oversight</div>
    </div>
    <div class="header-controls">
      <div class="child-pill" role="button" aria-label="Switch child profile">
        <div class="child-avatar">${db.child.name[0]}</div>
        <div>
          <div class="child-name">${db.child.name}</div>
          <div class="child-age">Age ${db.child.age}</div>
        </div>
      </div>
      <div class="notif-wrap">
        <button class="notif-btn" id="notif-btn" aria-label="View alerts">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        ${alertCount > 0 ? `<span class="notif-badge">${alertCount}</span>` : ''}
      </div>
    </div>
  `;
 
  document.getElementById('notif-btn')?.addEventListener('click', () => {
    const banner = document.getElementById('alert-banner');
    if (banner) {
      banner.style.display = banner.style.display === 'none' ? 'flex' : 'none';
    }
  });
}
 