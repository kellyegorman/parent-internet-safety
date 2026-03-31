document.getElementById("loginForm").addEventListener("submit", function(event) {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const message = document.getElementById("message");

   
    if (email === "parent@example.com" && password === "123456") {
        message.style.color = "green";
        message.textContent = "Redirecting...";
        
        setTimeout(() => {
            window.location.href = "dashboard.html"; // future page
        }, 1500);
    } else {
        message.style.color = "red";
        message.textContent = "Invalid email or password.";
    }
});
