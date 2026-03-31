// ============================================================
//  components/toast.js — Toast notification utility
// ============================================================
 
let toastTimer = null;
 
export function showToast(title, body, duration = 3200) {
  const el = document.getElementById('toast');
  if (!el) return;
 
  el.querySelector('.toast-title').textContent = title;
  el.querySelector('.toast-body').textContent  = body;
 
  el.classList.add('visible');
 
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('visible'), duration);
}
 