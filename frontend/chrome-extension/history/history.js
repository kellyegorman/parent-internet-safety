const history = document.getElementById("history");

chrome.history.onVisited.addListener((result) => {
    let div = document.createElement("div");
    div.textContent = result.url;

    container.appendChild(div);

});

// chrome.runtime.onMessage.addListener((message) => {
//     if (message.type === "historyUpdate") {
//         var newSearch = document.createElement("p");
//         newSearch.textContent = "there was a new search";
//         history.appendChild(newSearch);
//     }
// });


// const container = document.getElementById("history");

// chrome.storage.local.get(["historyList"], (data) => {
//     const list = data.historyList || [];

//     list.forEach(item => {

//         const div = document.createElement("div");
//         div.className = "item";

//         div.innerHTML = `
//         <div><a href="${item.url}" target="_blank">${item.title || item.url}</a></div>
//         <small>${item.time}</small>
//         `;

//         container.appendChild(div);
//     });

// });