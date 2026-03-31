chrome.extension.inIncognitoContext = true;

var loggedIn = false;
document.getElementById("loginForm").addEventListener("submit", logIn);
function logIn(event) {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const message = document.getElementById("message");

   
    if (email === "parent@example.com" && password === "123456") {
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

document.getElementById("deviceForm").addEventListener("submit", addDevice);
function addDevice(event) {
    event.preventDefault();
    const deviceName = document.getElementById("deviceName").value;
    const message = document.getElementById("deviceMessage");
    document.getElementById("deviceContainer").hidden = true;
    document.getElementById("deviceTitle").textContent = deviceName;
    document.getElementById("successContainer").hidden = false;
    // // open history tab when extension icon clicked
    // chrome.tabs.create({
    //     url: chrome.runtime.getURL("history/history.html")
    // });
}