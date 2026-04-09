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

function isLoggedIn() {
    chrome.storage.local.get("loggedIn", (result) => {
        const loggedIn = result.loggedIn || false;
        console.log("Checked login status: ", loggedIn);
    });
    return loggedIn;
}

function getToken() {
    chrome.storage.local.get("token", (result) => {
        const token = result.token || "";
        console.log("Retrieved token: Z", token.length>0 ? "length " + token.length : "none");
    });
    return token;
}

function getDeviceID() {
    chrome.storage.local.get("deviceID", (result) => {
        const deviceID = result.deviceID || "";
        console.log("Retrieved device ID: ", deviceID);
    });
    return deviceID;
}


var loggedIn = isLoggedIn();

var token = chrome.storage.local.get("token", (result) => {
    token = result.token || "";
    console.log("Initial token:", token.substring(0, 3) + "...");
});

// Record user history activity
function visit(result) {
    //console.log("Last Visited URL:", result.url);
    if (result.url === (lastVisitedURL)) {
        //console.log("URL already visited, skipping");
        return;
    }
    lastVisitedURL = result.url;
    const title = result.title ? result.title : "";
    if (title.length == 0){
        chrome.history.addUrl({url: result.url}, () => {console.log("Trying again for title")});
        return;
    }

    // Reset the debouncing timeout to handle the most recent visit
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
        console.log("Visited " + title + " at " + timeFormat(result?.lastVisitTime) + 
        "\nURL:" + result.url);
    },100); // 0.1 second delay to clean up (you can adjust this)
    

    if (isLoggedIn()) {
        // Add search to database
        fetch("https://senior-project-production-4c90.up.railway.app/searches", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "x-api-key": getToken()
            },
            body: JSON.stringify({
                deviceid: "d01",
                query_text: "test search",
                url: window.location.href
            })
        })
        .then(async (res) => {
            console.log("status:", res.status);
            const body = await res.text();
            console.log("body:", body);
        })
        .catch(err => console.error("fetch error:", err));
    }
}

