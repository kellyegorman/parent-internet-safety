chrome.extension.inIncognitoContext = true;

// Put in your API key here
const apiKey = "";

// Populating popup on load based on login and device registration status
getLoggedIn().then(loggedIn => {
    getDeviceName().then(deviceName => {
        const registered = deviceName.length > 0;
        
        if (loggedIn) {
            document.getElementById("loginContainer").hidden = true;
            if (registered) {
                document.getElementById("deviceContainer").hidden = true;
                document.getElementById("successContainer").hidden = true;
                document.getElementById("deviceCurrentName").textContent = deviceName;
                document.getElementById("idleContainer").hidden = false;
            }
            else {
                document.getElementById("deviceContainer").hidden = false;
            }
        }

    });
});


// Form submission handlers for login and device addition
document.getElementById("loginForm").addEventListener("submit", logIn);
document.getElementById("deviceForm").addEventListener("submit", addDevice);

// Log in user
function logIn(event) {
    event.preventDefault();
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const message = document.getElementById("message");
    message.style.color = "gray";
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
        var loginBody = await res.text();
        if (res.status == 200) {
            var token = JSON.parse(loginBody).access_token;
            message.style.color = "green";
            message.textContent = "Login successful! Fetching information...";
            const url = "https://senior-project-production-4c90.up.railway.app/userid";
            const params = new URLSearchParams({ email: email });
            fetch(`${url}?${params.toString()}`, {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                    "x-api-key": apiKey
                }
            })
            .then(async (res) => {
                const userIDBody = await res.text();
                if (res.status == 200) {
                    const userID = JSON.parse(userIDBody).userid;
                    chrome.storage.local.set({ loggedIn: true, token: token, email: email, userID: userID });
                    document.getElementById("loginContainer").hidden = true;
                    document.getElementById("deviceContainer").hidden = false;
                }
                else {
                    message.style.color = "red";
                    message.textContent = "User information retrieval failed.";
                }
            })
            .catch(err => console.error("fetch error:", err))
        } 
        else {
            message.style.color = "red";
            message.textContent = "Invalid email or password.";
        }
    })
    .catch(err => console.error("fetch error:", err));

    
};


// Add device for monitoring
function addDevice(event) {
    event.preventDefault();
    const deviceName = document.getElementById("deviceName").value;
    const message = document.getElementById("deviceMessage");
    message.style.color = "gray";
    message.textContent = "Adding device...";
    getUserID().then(userID => {
        fetch("https://senior-project-production-4c90.up.railway.app/devices", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                "userid": userID,
                "device_name": deviceName
            })
        })
        .then(async (res) => {
            const deviceBody = await res.text();
            if (res.status == 200) {
                const deviceID = JSON.parse(deviceBody).deviceid;
                chrome.storage.local.set({ deviceID: deviceID, deviceName: deviceName });
                message.style.color = "green";
                message.textContent = "Device added successfully!";
                document.getElementById("deviceContainer").hidden = true;
                document.getElementById("deviceTitle").textContent = deviceName;
                document.getElementById("successContainer").hidden = false;
            }
            else {
                message.style.color = "red";
                message.textContent = "Device addition failed.";
            }
        })
        .catch(err => console.error("fetch error:", err));
    });
}

async function getLoggedIn() {
    const result = await chrome.storage.local.get("loggedIn");
    const loggedIn = result.loggedIn || false;
    console.log("Retrieved login status: ", loggedIn);
    return loggedIn;
}

async function getToken() {
    const result = await chrome.storage.local.get("token");
    const token = result.token || "";
    console.log("Retrieved token:", token.substring(0, 3) + "...");
    return token;
}

async function getUserID() {
    const result = await chrome.storage.local.get("userID");
    const userID = result.userID || "";
    console.log("Retrieved user ID: ", userID);
    return userID;
}

async function getDeviceID() {
    const result = await chrome.storage.local.get("deviceID");
    const deviceID = result.deviceID || "";
    console.log("Retrieved device ID: ", deviceID);
    return deviceID;
}

async function getDeviceName() {
    const result = await chrome.storage.local.get("deviceName");
    const deviceName = result.deviceName || "";
    console.log("Retrieved device name: ", deviceName);
    return deviceName;
}
