chrome.extension.inIncognitoContext = true;

var loggedIn = getLoggedIn();
document.getElementById("loginContainer").hidden = loggedIn;


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
        var loginBody = await res.text();
        if (loginBody.includes("bearer")) {
            var token = JSON.parse(loginBody).access_token;
            message.style.color = "green";
            message.textContent = "Login Successful!";
            loggedIn = true;
            
            chrome.storage.local.set({ loggedIn: true, token: token, email: email, userID: await getUserID(email, token) });
            document.getElementById("loginContainer").hidden = loggedIn;
            document.getElementById("deviceContainer").hidden = !loggedIn;
        } 
        else {
            message.style.color = "red";
            message.textContent = "Invalid email or password.";
        }
    })
    .catch(err => console.error("fetch error:", err));

    
};

// Get userid from email
async function getUserID(email, token) {
    fetch("https://senior-project-production-4c90.up.railway.app/userid", {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            "email": email,
            "x-api-key": token
        })
    })
    .then(async (res) => {
        const userID = await res.text();
        return userID;
    })
    .catch(err => console.error("fetch error:", err));
}

// Add device for monitoring
function addDevice(event) {
    event.preventDefault();
    const deviceName = document.getElementById("deviceName").value;
    const message = document.getElementById("deviceMessage");
    const userID = getUserID(); // This should be retrieved from the login response in a real implementation

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
        console.log("status:", res.status);
        const deviceBody = await res.text();
        console.log("body:", deviceBody);
        if (!deviceBody.stringify.includes("detail")) {
            document.getElementById("deviceContainer").hidden = true;
            document.getElementById("deviceTitle").textContent = deviceName;
            document.getElementById("successContainer").hidden = false;
        }
    })
    .catch(err => console.error("fetch error:", err));

}

function getLoggedIn() {
    var loggedIn = false;
    chrome.storage.local.get("loggedIn", (result) => {
        loggedIn = result.loggedIn || false;
    });
    return loggedIn;
}

function getUserID() {
    var userID = "";
    chrome.storage.local.get("userID", (result) => {
        userID = result.userID || "";
    });
    return userID;
}

function getToken() {
    var token = "";
    chrome.storage.local.get("token", (result) => {
        token = result.token || "";
    });
    return token;
}