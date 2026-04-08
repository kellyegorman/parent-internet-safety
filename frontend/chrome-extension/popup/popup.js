const API_BASE = "http://127.0.0.1:8000";
// make sure this is the same as API_KEY in backend .env !!
const API_KEY  = "api_key_1234567";  
 
// if already logged in, skip straight to success screen
chrome.storage.local.get(["deviceid", "deviceName"], (data) => {
    if (data.deviceid) {
        showSuccess(data.deviceName || "Your Device");
    }
});
 
// login
document.getElementById("loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();
 
    const email    = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const message  = document.getElementById("message");
 
    message.style.color = "#888";
    message.textContent = "Logging in…";
 
    try {
        const res = await fetch(`${API_BASE}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
        });
 
        if (res.ok) {
            const data = await res.json();
            // get the userid -> register a device
            const uidRes = await fetch(
                `${API_BASE}/userid?email=${encodeURIComponent(email)}`,
                { headers: { "x-api-key": API_KEY } }
            );
            const uidData = await uidRes.json();
            await chrome.storage.local.set({
                token:  data.access_token,
                userid: uidData.userid,
                email:  email,
            });
 
            message.style.color = "green";
            message.textContent = "Logged in!";
            document.getElementById("loginContainer").hidden = true;
            document.getElementById("deviceContainer").hidden = false;
 
        } else {
            message.style.color = "red";
            message.textContent = "Invalid email or password.";
        }
    } catch (e) {
        message.style.color = "red";
        message.textContent = "Cannot reach server — is it running?";
        console.error(e);
    }
});
 
// register device
document.getElementById("deviceForm").addEventListener("submit", async (event) => {
    event.preventDefault();
 
    const deviceName    = document.getElementById("deviceName").value.trim();
    const deviceMessage = document.getElementById("deviceMessage");
 
    deviceMessage.style.color = "#888";
    deviceMessage.textContent = "Registering…";
 
    const { userid, deviceid: existingId } = await chrome.storage.local.get(["userid", "deviceid"]);
    const deviceid = existingId || ("D" + Math.random().toString(36).slice(2, 14).toUpperCase());
 
    try {
        const res = await fetch(`${API_BASE}/devices`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                deviceid:     deviceid,
                userid:       userid,
                device_name:  deviceName,
                device_token: deviceid + "_token",
            }),
        });
 
        const data = await res.json();
 
        // "already registered" is fine — just continue
        if (res.ok || (data.detail && data.detail.includes("already registered"))) {
            await chrome.storage.local.set({ deviceid, deviceName });
            showSuccess(deviceName);
        } else {
            deviceMessage.style.color = "red";
            deviceMessage.textContent = data.detail || "Registration failed.";
        }
    } catch (e) {
        deviceMessage.style.color = "red";
        deviceMessage.textContent = "Cannot reach server.";
        console.error(e);
    }
});
 
// ── Helpers ───────────────────────────────────────────────────────────────────
function showSuccess(deviceName) {
    document.getElementById("loginContainer").hidden  = true;
    document.getElementById("deviceContainer").hidden = true;
    document.getElementById("successContainer").hidden = false;
    document.getElementById("deviceTitle").textContent = deviceName;
}
 
const logoutBtn = document.getElementById("logoutBtn");
if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
        await chrome.storage.local.clear();
        location.reload();
    });
}
