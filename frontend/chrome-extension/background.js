chrome.extension.inIncognitoContext = true;

// Put in your API key here
const apiKey = "";
var lastVisitedURL = "";
let debounceTimeout;

console.log("Background script loaded");
chrome.history.onVisited.addListener(function(historyItem) {
    visit(historyItem);
});
console.log("History listener added");

function timeFormat(time) {
    var d = new Date(time);
    return d.toLocaleString();
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

// Record user history activity
function visit(result) {
    if (result.url === (lastVisitedURL)) {
        //console.log("URL already visited, skipping");
        return;
    }
    const title = result.title ? result.title : "";
    if (title.length == 0){
        chrome.history.addUrl({url: result.url}, () => {console.log("Trying again for title")});
        return;
    }
    lastVisitedURL = result.url;

    // Reset the debouncing timeout to handle the most recent visit
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
        console.log("Visited " + title + " at " + timeFormat(result?.lastVisitTime) + 
        "\nURL:" + result.url);
        getLoggedIn().then(loggedIn => {
            if (loggedIn) {
                console.log("Recording search in database...");
                getDeviceID().then(deviceID => {
                    // Add search to database
                    fetch("https://senior-project-production-4c90.up.railway.app/searches", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "x-api-key": apiKey
                        },
                        body: JSON.stringify({
                            deviceid: deviceID,
                            query_text: result.title,
                            url: result.url
                        })
                    })
                    .then(async (res) => {
                        const body = await res.text();
                        console.log("POST result:", body);
                    })
                    .catch(err => console.error("fetch error:", err));
                });
            }
        });
    },100); // 0.1 second delay to clean up (you can adjust this)
}

