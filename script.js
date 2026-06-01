const API = "http://127.0.0.1:8000";

let token = null;

function showChat() {
    document.getElementById("loginBox").style.display = "none";
    document.getElementById("chatBox").style.display = "block";
}

async function register() {
    await fetch(API + "/register", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            username: user.value,
            password: pass.value
        })
    });

    alert("Registered");
}

async function login() {
    const res = await fetch(API + "/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            username: user.value,
            password: pass.value
        })
    });

    const data = await res.json();

    if (data.ok) {
        token = data.token;
        showChat();
    } else {
        alert("wrong login");
    }
}

async function send() {
    const msg = document.getElementById("msg").value;
    const box = document.getElementById("messages");

    if (!msg) return;

    box.innerHTML += "You: " + msg + "<br>";

    const res = await fetch(API + "/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            message: msg,
            token: token
        })
    });

    const data = await res.json();

    box.innerHTML += "AI: " + (data.response || "error") + "<br>";

    document.getElementById("msg").value = "";
    box.scrollTop = box.scrollHeight;
}