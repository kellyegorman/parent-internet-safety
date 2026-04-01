console.log("Background script loaded");
chrome.history.onVisited.addListener(visit);
console.log("History listener added");

function visit(result) {
    setTimeout(() => {
        console.log("Visited " + result.title + 
        " at " + timeFormat(result?.lastVisitTime) + 
        "\nURL:" + result.url);
    }, 500);
    // fetch("https://senior-project-production-4c90.up.railway.app/searches", {
    //     method: "POST",
    //     headers: {
    //         "Content-Type": "application/json",
    //         "x-api-key": "4c133d290fadef7b21445b95694dda610f1741f083ad7e680c251c059f074dcf"
    //     },
    //     body: JSON.stringify({
    //         deviceid: "d01",
    //         query_text: "test search",
    //         url: window.location.href
    //     })
    // })
    // .then(async (res) => {
    //     console.log("status:", res.status);
    //     const body = await res.text();
    //     console.log("body:", body);
    // })
    // .catch(err => console.error("fetch error:", err));
};

function timeFormat(time) {
    var d = new Date(time);
    return d.toLocaleString();
}


