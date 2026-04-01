chrome.extension.inIncognitoContext = true;

var loggedIn = false;

// Form submission handlers for login and device addition
document.getElementById("loginForm").addEventListener("submit", logIn);
document.getElementById("deviceForm").addEventListener("submit", addDevice);

// Log in user
function logIn(event) {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const message = document.getElementById("message");
    message.style.color = "green";
    message.textContent = "Attempting login with email: " + email;

    fetch("https://senior-project-production-4c90.up.railway.app/login", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            "email": email,
            "password": password
        })
    })
    .then(async (res) => {
        console.log("status:", res.status);
        const loginBody = await res.text();
        console.log("body:", loginBody);
    })
    .catch(err => console.error("fetch error:", err));

    message.textContent = loginBody;

    if (loginBody.stringify.includes("access_token")) {
        message.style.color = "green";
        message.textContent = "Redirecting...";
        loggedIn = true;
        document.getElementById("loginContainer").hidden = loggedIn;
        document.getElementById("deviceContainer").hidden = !loggedIn;
    } 
    else {
        message.style.color = "red";
        message.textContent = "Invalid email or password.";
    }
};

// Add device for monitoring
function addDevice(event) {
    event.preventDefault();
    const deviceName = document.getElementById("deviceName").value;
    const message = document.getElementById("deviceMessage");
    const deviceID = chrome.enterprise.networkingAttributes.getNetworkDetailes().macAddress || "unknown_device_id";
    deviceID = deviceID.replace(/:/g, ""); // Remove colons from MAC address for cleaner and shorter ID
    const userID = "example_user_id"; // This should be retrieved from the login response in a real implementation

    fetch("https://senior-project-production-4c90.up.railway.app/devices", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            "deviceid": deviceID,
            "userid": userID,
            "device_name": deviceName,
            "device_token": 
        })
    })
    .then(async (res) => {
        console.log("status:", res.status);
        const deviceBody = await res.text();
        console.log("body:", deviceBody);
    })
    .catch(err => console.error("fetch error:", err));

    if (!deviceBody.stringify.includes("detail")) {
        document.getElementById("deviceContainer").hidden = true;
        document.getElementById("deviceTitle").textContent = deviceName;
        document.getElementById("successContainer").hidden = false;
    }
}