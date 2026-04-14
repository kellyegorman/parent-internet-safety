const API_BASE = "https://senior-project-production-4c90.up.railway.app"

document.getElementById("loginForm").addEventListener("submit", async function(event) {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const message = document.getElementById("message");

    try {
    const res = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (!res.ok) {
        message.style.color = "red";
        message.textContent = data.detail || "Login failed";
        return;
    }

    // save token
    localStorage.setItem("token", data.token);
    localStorage.setItem("userid", data.userid);

    message.style.color = "green";
    message.textContent = "Redirecting...";

    setTimeout(() => {
        window.location.href = "../dashboard/";
    }, 1500);

} catch (err) {
    console.error(err);
    message.style.color = "red";
    message.textContent = "Server error";
}
    // if (email === "parent@example.com" && password === "123456") {
    //     message.style.color = "green";
    //     message.textContent = "Redirecting...";
        
    //     setTimeout(() => {
    //         window.location.href = "dashboard.html"; // future page
    //     }, 1500);
    // } else {
    //     message.style.color = "red";
    //     message.textContent = "Invalid email or password.";
    // }
});
