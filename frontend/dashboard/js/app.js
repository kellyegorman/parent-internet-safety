// ============================================================
//  app.js — Main entry point; orchestrates data + rendering
// ============================================================
 
import { fetchAlerts, fetchStats, fetchSearchHistory, fetchTopics, fetchActivity, db } from './data/db.js';
import { renderHeader }        from './components/header.js';
import { renderAlertBanner }   from './components/alert-banner.js';
import { renderStats }         from './components/stats.js';
import { renderSearchHistory } from './components/search-history.js';
import { renderTopics, renderActivity } from './components/topics-activity.js';
 
async function init() {
  const [alerts, stats, searches, topics, activity] = await Promise.all([
    fetchAlerts(),
    fetchStats(),
    fetchSearchHistory(),
    fetchTopics(),
    fetchActivity()
  ]);
 
  renderHeader(alerts.length);
  renderAlertBanner(alerts);
  renderStats(stats);
  renderSearchHistory(searches);
  renderTopics(topics);
  renderActivity(activity);
 
  // Connection bar device name
  const deviceEl = document.getElementById('connection-device');
  if (deviceEl) deviceEl.textContent = db.child.device;
}
 
document.addEventListener('DOMContentLoaded', init);
 