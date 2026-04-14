// connect to API and use actual data instead of using synthetic data like we did in testing

const API    = 'https://senior-project-production-4c90.up.railway.app';
const APIKEY = 'myapikey123';

// read auth from sessionStorage 
function getAuth() {
  return {
    token:  sessionStorage.getItem('token')  || '',
    userid: sessionStorage.getItem('userid') || '',
    email:  sessionStorage.getItem('email')  || '',
  };
}

async function apiFetch(path) {
  const { token } = getAuth();
  const headers = { 'Content-Type': 'application/json', 'x-api-key': APIKEY };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(API + path, { headers });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

function fmtTime(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const diff = Date.now() - d;
  const m = Math.floor(diff / 60000);
  const h = Math.floor(diff / 3600000);
  const day = Math.floor(diff / 86400000);
  if (m < 1)   return 'just now';
  if (m < 60)  return `${m}m ago`;
  if (h < 24)  return `${h}h ago`;
  if (day < 7) return `${day}d ago`;
  return d.toLocaleDateString();
}

export const db = {
  child: { name: '', age: '', device: '' }
};

export async function fetchSearchHistory() {
  const { userid } = getAuth();
  if (!userid) return [];
  try {
    const data = await apiFetch(`/users/${userid}/searches`);
    return (data.searches || []).slice(0, 30).map(s => ({
      id:       s.searchid,
      query:    s.url
                  ? s.url.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]
                  : (s.query_text || '—'),
      time:     fmtTime(s.searched_at),
      status:   s.flagged ? 'review' : 'safe',
      category: 'default',
    }));
  } catch (e) {
    console.error('[db] fetchSearchHistory:', e);
    return [];
  }
}

export async function fetchAlerts() {
  const { userid } = getAuth();
  if (!userid) return [];
  try {
    const data = await apiFetch(`/users/${userid}/alerts`);
    return (data.alerts || [])
      .filter(a => a.severity === 'moderate' || a.severity === 'severe')
      .slice(0, 10)
      .map(a => ({
        id:        a.alertid,
        timestamp: fmtTime(a.created_at),
        query:     a.domain || a.reason_code || 'unknown',
        severity:  a.severity,
        dismissed: false,
      }));
  } catch (e) {
    console.error('[db] fetchAlerts:', e);
    return [];
  }
}

export async function fetchStats() {
  const { userid } = getAuth();
  if (!userid) return {
    searches: { value: '—', label: 'Total searches' },
    flagged:  { value: '—', label: 'Flagged pages' },
    blocked:  { value: '—', label: 'Devices monitored' },
  };
  try {
    const [searchData, alertData, deviceData] = await Promise.all([
      apiFetch(`/users/${userid}/searches`),
      apiFetch(`/users/${userid}/alerts`),
      apiFetch(`/users/${userid}/devices`),
    ]);
    return {
      searches: { value: (searchData.searches || []).length, label: 'Total searches' },
      flagged:  { value: (alertData.alerts   || []).length, label: 'Flagged pages'   },
      blocked:  { value: (deviceData.devices || []).length, label: 'Devices monitored'},
    };
  } catch (e) {
    console.error('[db] fetchStats:', e);
    return {
      searches: { value: '—', label: 'Total searches' },
      flagged:  { value: '—', label: 'Flagged pages'  },
      blocked:  { value: '—', label: 'Devices monitored' },
    };
  }
}

export async function fetchTopics() {
  const { userid } = getAuth();
  if (!userid) return [];
  try {
    const data = await apiFetch(`/users/${userid}/alerts`);
    const counts = {};
    (data.alerts || []).forEach(a => {
      if (a.reason_code && a.reason_code.startsWith('TOPICS:')) {
        a.reason_code.replace('TOPICS:', '').split('|').forEach(t => {
          const word = t.trim();
          if (word) counts[word] = (counts[word] || 0) + 1;
        });
      }
    });
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([label, count]) => ({ label, count, swatch: 'swatch-other' }));
  } catch (e) {
    return [];
  }
}

export async function fetchActivity() {
  const { userid } = getAuth();
  if (!userid) return [];
  try {
    const data = await apiFetch(`/users/${userid}/alerts`);
    return (data.alerts || []).slice(0, 8).map(a => ({
      type:   a.severity === 'severe' ? 'rose' : a.severity === 'moderate' ? 'amber' : 'subtle',
      icon:   a.severity === 'severe' || a.severity === 'moderate' ? 'alert' : 'globe',
      action: `${a.domain || 'Page'} — ${a.reason_code || a.severity}`,
      when:   fmtTime(a.created_at),
    }));
  } catch (e) {
    return [];
  }
}
