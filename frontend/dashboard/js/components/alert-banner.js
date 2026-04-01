// ============================================================
//  components/alert-banner.js — Alert banner rendering & actions
// ============================================================
 
import { showToast } from './toast.js';
 
export function renderAlertBanner(alerts) {
  const el = document.getElementById('alert-banner');
  if (!el) return;
 
  if (!alerts || alerts.length === 0) {
    el.style.display = 'none';
    return;
  }
 
  const alert = alerts[0]; // Show most recent alert
  el.style.display = 'flex';
 
  el.innerHTML = `
    <div class="alert-indicator"></div>
    <div class="alert-content">
      <div class="alert-meta">Content Alert — ${alert.timestamp}</div>
      <div class="alert-headline">
        Jake searched for
        <span class="alert-query-tag">${alert.query}</span>
        on Chrome. This query was flagged by content filters.
      </div>
      <div class="alert-actions">
        <button class="btn btn-danger" id="btn-block">Block Site</button>
        <button class="btn btn-subtle" id="btn-ok">Mark as OK</button>
        <button class="btn btn-ghost" id="btn-dismiss">Dismiss</button>
      </div>
    </div>
  `;
 
  document.getElementById('btn-block')?.addEventListener('click', () => {
    dismissBanner();
    showToast('Site Blocked', 'The content source has been blocked for Jake.');
  });
 
  document.getElementById('btn-ok')?.addEventListener('click', () => {
    dismissBanner();
    showToast('Marked as OK', 'This search was approved and will not be flagged again.');
  });
 
  document.getElementById('btn-dismiss')?.addEventListener('click', dismissBanner);
}
 
function dismissBanner() {
  const el = document.getElementById('alert-banner');
  const badge = document.querySelector('.notif-badge');
  if (el) el.style.display = 'none';
  if (badge) badge.style.display = 'none';
}
 