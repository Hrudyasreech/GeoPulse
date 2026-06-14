// Local client data-store cache to completely eliminate mousemove network spam
const mapDataCache = {};

// 1. Fetch and load the Map Assets
fetch("assets/india.svg")
    .then(response => response.text())
    .then(svgData => {
        const mapContainer = document.getElementById("map");
        if (mapContainer) {
            mapContainer.innerHTML = svgData;
        }
        attachMapEvents();
        loadStateSentiments();
    })
    .catch(err => console.error("Error loading SVG map asset file:", err));

// 2. Event Routing Controller Module
function attachMapEvents() {
    const states = document.querySelectorAll("#map path");
    const tooltip = document.getElementById("tooltip");

    states.forEach(state => {
        // Redirection Context
        state.addEventListener("click", () => {
            const stateName = state.getAttribute("title");
            if (!stateName) return;
            
            console.log(`Routing to dashboard region: ${stateName}`);
            window.location.href = `news.html?state=${encodeURIComponent(stateName)}`;
        });

        // High Performance Mouse Hover Logic
        state.addEventListener("mousemove", (e) => {
            const stateName = state.getAttribute("title");
            if (!stateName || !tooltip) return;

            // Instantly extract from client cache memory (0 network requests made here!)
            const cachedData = mapDataCache[stateName];

            if (cachedData) {
                tooltip.innerHTML = `
                    <strong>${stateName}</strong><br>
                    Sentiment: ${cachedData.sentiment}<br>
                    Topic: ${cachedData.topic}<br>
                    Articles: ${cachedData.count}
                `;
            } else {
                // Fallback Layout structure if backend has no records yet for this state
                tooltip.innerHTML = `
                    <strong>${stateName}</strong><br>
                    <span style="color: #94a3b8;">No data streaming yet</span>
                `;
            }

            // Standardize dynamic positioning offsets relative to cursor pointer coordinates
            tooltip.style.left = `${e.pageX + 15}px`;
            tooltip.style.top = `${e.pageY + 15}px`;
            tooltip.style.opacity = 1;
        });

        // Hide overlay elements cleanly when boundary tracks clear out
        state.addEventListener("mouseleave", () => {
            if (tooltip) tooltip.style.opacity = 0;
        });
    });
}

// 3. Centralized Batch Data Intake
async function loadStateSentiments() {
    try {
        const response = await fetch("http://127.0.0.1:8000/state-summary");
        if (!response.ok) throw new Error(`HTTP Error Code: ${response.status}`);
        
        const summaries = await response.json();

        summaries.forEach(summary => {
            const stateName = summary.state;
            const sentiment = summary.overall_sentiment;
            
            // Map records directly onto our local client dictionary lookup cache
            mapDataCache[stateName] = {
                sentiment: sentiment.charAt(0).toUpperCase() + sentiment.slice(1),
                topic: summary.top_category || "General",
                count: summary.article_count || 0
            };

            // SVG Map Path Aesthetics Layer
            const statePath = document.querySelector(`#map path[title="${stateName}"]`);
            if (statePath) {
                let score = Math.max(Math.abs(summary.sentiment_score), 0.5);

                if (sentiment === "positive") {
                    statePath.style.fill = `rgba(76, 175, 80, ${score})`;
                } else if (sentiment === "negative") {
                    statePath.style.fill = `rgba(244, 67, 54, ${score})`;
                } else {
                    statePath.style.fill = `rgba(158, 158, 158, ${score})`;
                }
            }
        });
    } catch (error) {
        console.warn("Backend not running or state data could not be pulled. Using UI standalone modes.", error);
        // Tip: You can insert mock data into mapDataCache here if you want to test hover styles offline!
    }
}