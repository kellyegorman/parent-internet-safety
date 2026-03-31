// ============================================================
//  data/db.js — Dummy data store (replace with real API/DB)
//  In production: swap fetchSearchHistory(), fetchAlerts(),
//  fetchStats(), fetchTopics(), fetchActivity() with real
//  fetch() calls to your backend or Chrome Extension bridge.
// ============================================================
 
export const db = {
 
    child: {
      name: "CHILD NAME EXAmple",
      age: 12,
      device: "CHILD NAME's Computer"
    },
   
    stats: {
      searches:    { value: 47,   label: "Searches this week" },
      flagged:     { value: 3,    label: "Flagged items" },
      blocked:     { value: 8,    label: "Sites blocked" }
    },
   
    alerts: [
      {
        id: "a1",
        timestamp: "Today · 3:47 PM",
        query: "inappropriate content",
        dismissed: false
      }
    ],
   
    searches: [
      { id: "s1", query: "inappropriate content",        time: "Today · 3:47 PM",    category: "flagged",  status: "review"  },
      { id: "s2", query: "when is superbowl 2026",       time: "Today · 2:30 PM",    category: "sports",   status: "safe"    },
      { id: "s3", query: "minecraft best seeds 2026",    time: "Today · 1:15 PM",    category: "gaming",   status: "safe"    },
      { id: "s4", query: "spider-man no way home watch", time: "Yesterday · 7:02 PM",category: "celeb",    status: "safe"    },
      { id: "s5", query: "lebron james net worth",       time: "Yesterday · 5:44 PM",category: "celeb",    status: "safe"    },
      { id: "s6", query: "how do black holes form",      time: "Mon · 4:10 PM",      category: "default",  status: "safe"    }
    ],
   
    topics: [
      { label: "Sports",       count: 18, swatch: "swatch-sports"  },
      { label: "Gaming",       count: 14, swatch: "swatch-gaming"  },
      { label: "Celebrities",  count: 9,  swatch: "swatch-celeb"   },
      { label: "Science",      count: 4,  swatch: "swatch-science" },
      { label: "Other",        count: 2,  swatch: "swatch-other"   }
    ],
   
    activity: [
      { type: "rose",  icon: "alert",  action: "Flagged search detected",       when: "Today · 3:47 PM"   },
      { type: "teal",  icon: "globe",  action: "Visited youtube.com — 38 min",  when: "Today · 2:00 PM"   },
      { type: "sage",  icon: "check",  action: "Daily limit updated to 3 hrs",  when: "Yesterday · 9:00 AM"},
      { type: "amber", icon: "block",  action: "Site blocked: tiktok.com",      when: "Mon · 6:30 PM"     }
    ]
  };
   
  // ── API bridge placeholder ────────────────────────────────────
  // When the Chrome extension is ready, replace these stubs:
   
  export async function fetchSearchHistory() {
    // return await fetch('/api/searches').then(r => r.json());
    return db.searches;
  }
   
  export async function fetchAlerts() {
    // return await fetch('/api/alerts').then(r => r.json());
    return db.alerts.filter(a => !a.dismissed);
  }
   
  export async function fetchStats() {
    // return await fetch('/api/stats').then(r => r.json());
    return db.stats;
  }
   
  export async function fetchTopics() {
    // return await fetch('/api/topics').then(r => r.json());
    return db.topics;
  }
   
  export async function fetchActivity() {
    // return await fetch('/api/activity').then(r => r.json());
    return db.activity;
  }
   