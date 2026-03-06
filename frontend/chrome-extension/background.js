console.log("Background script loaded");
chrome.history.onVisited.addListener(visit);
console.log("History listener added");

function visit(result) {
    setTimeout(() => {
        console.log("Visited " + result.title + 
        " at " + timeFormat(result?.lastVisitTime) + 
        "\nURL:" + result.url);
    }, 500);
};

function timeFormat(time) {
    var d = new Date(time);
    return d.toLocaleString();
}
// chrome.history.onVisited.addListener((result) => {
//     chrome.runtime.sendMessage({ type: "historyUpdate", data: result });
// });

