const params = new URLSearchParams(window.location.search);
const state = params.get("state") || "Global";
let cachedNewsData = [];

const stateTitleEl = document.getElementById("state-title");
if (stateTitleEl) stateTitleEl.innerText = `Latest News from ${state}`;

function goBack() {
    window.location.href = "index.html";
}

function switchTab(tabId, event) {
    document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));
    if (event && event.currentTarget) event.currentTarget.classList.add('active');

    document.querySelectorAll('.tab-content').forEach(section => section.classList.remove('active'));
    const activeSection = document.getElementById(`${tabId}-section`);
    if (activeSection) activeSection.classList.add('active');

    if (tabId === 'News' && cachedNewsData) renderNews(cachedNewsData);

    if (tabId === 'Analytics' && !window.analyticsLoaded) {
        fetchAnalytics();
        window.analyticsLoaded = true;
    }
}

// ── News ─────────────────────────────────────────────────────

async function fetchNews() {
    try {
        const response = await fetch(`http://127.0.0.1:8000/news/${state}`);
        if (!response.ok) throw new Error(`HTTP Error Status: ${response.status}`);
        const newsData = await response.json();
        cachedNewsData = newsData;
        renderNews(newsData);
    } catch (error) {
        console.error("Error fetching news feed:", error);
    }
}

function renderNews(newsData) {
    newsData.sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt));
    const container = document.getElementById("news-container");
    if (!container) return;
    container.innerHTML = "";

    const sentimentColors = { positive: "#22c55e", negative: "#ef4444", neutral: "#94a3b8" };

    newsData.forEach(news => {
        const card = document.createElement("div");
        card.classList.add("news-card");

        const sentimentType = Array.isArray(news.sentiment) ? news.sentiment[0] : news.sentiment;
        card.style.borderTop = `4px solid ${sentimentColors[sentimentType] || sentimentColors.neutral}`;

        const dateStr = news.publishedAt ? new Date(news.publishedAt).toLocaleDateString() : 'Recent';
        const categoryStr = news.category && news.category !== "Pending..." ? news.category : "General";

        card.innerHTML = `
            <div class="card-meta">
                <span class="card-date">${dateStr}</span>
                <span class="card-category-badge">${categoryStr}</span>
            </div>
            <h2>${news.title}</h2>
            <p class="card-teaser">${news.summary || "No details available."}</p>
            <button class="read-more-btn">Read Brief</button>
        `;

        card.querySelector(".read-more-btn").addEventListener("click", () => {
            openModal(news.title, news.summary, news.image, news.url, dateStr);
        });

        container.appendChild(card);
    });
}

function filterNews() {
    const query = document.getElementById("search-input").value.toLowerCase();
    const filtered = cachedNewsData.filter(news =>
        news.title.toLowerCase().includes(query) ||
        (news.summary && news.summary.toLowerCase().includes(query))
    );
    renderNews(filtered);
}

// ── Analytics (single fetch) ──────────────────────────────────

async function fetchAnalytics() {
    try {
        const response = await fetch(`http://127.0.0.1:8000/analytics/${state}`);
        if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
        const data = await response.json();

        // AI Insight
        const insightEl = document.getElementById("state-ai-summary");
        if (insightEl) insightEl.innerText = data.summary?.ai_insights
            || "Analyzing regional data... Please refresh shortly.";

        // Sentiment card
        const sentimentEl = document.getElementById("overall-sentiment");
        if (sentimentEl && data.summary?.overall_sentiment) {
            const s = data.summary.overall_sentiment;
            sentimentEl.innerText = s.charAt(0).toUpperCase() + s.slice(1);
            sentimentEl.className = `sentiment-text-${s}`;
        }

        const articleCountEl = document.getElementById("article-count");
        if (articleCountEl) articleCountEl.innerText = `${data.summary?.article_count || 0} articles analyzed`;

        // Metric cards
        renderCoverageIntensity(data.coverage);
        renderTopicDiversity(data.topic_diversity);
        renderSentimentShift(data.sentiment_shift);
        renderNewsFreshness(data.news_freshness);
        renderNewsAlertLevel(data.alert_level);

        // Charts
        renderEntities(data.entities);
        renderCategoryChart(data.categories);
        renderSentimentChart(data.sentiments);
        renderTrendChart(data.sentiment_trend);
        renderActivityChart(data.activity_trend);

    } catch(error) {
        console.error("Analytics fetch failed:", error);
    }
}

// ── Metric Card Renderers ─────────────────────────────────────

function renderCoverageIntensity(data) {
    const el = document.getElementById("coverage-intensity");
    if (!el) return;
    el.innerText = `${data.coverage} (${data.ratio}x)`;
    el.className = `coverage-intensity-${data.coverage === "High" ? "high" : data.coverage === "Low" ? "low" : "normal"}`;
}

function renderTopicDiversity(data) {
    const el = document.getElementById("topic-diversity");
    if (!el) return;
    el.innerText = data.category_count === 0
        ? "No articles to analyze."
        : `${data.diversity} (${data.category_count})`;
}

function renderSentimentShift(data) {
    const el = document.getElementById("sentiment-shift");
    if (!el) return;
    const icon = data.shift === "Positive" ? "↗" : data.shift === "Negative" ? "↘" : "→";
    const symbol = data.change > 0 ? "+" : "-";
    el.innerText = `${icon} ${data.shift} (${symbol}${Math.abs(data.change)})`;
}

function renderNewsFreshness(data) {
    const el = document.getElementById("news-freshness");
    if (!el) return;
    el.innerText = `${data.freshness} (${data.age})`;
}

function renderNewsAlertLevel(data) {
    const el = document.getElementById("news-alert-level");
    if (!el) return;
    el.innerText = `${data.level} (${data.score}%)`;
}

// ── Chart Renderers ───────────────────────────────────────────

function renderEntities(data) {
    const entityCloud = document.getElementById("entity-cloud");
    if (!entityCloud) return;
    entityCloud.innerHTML = "";

    data.forEach(item => {
        const tag = document.createElement("span");
        tag.classList.add("entity-tag");
        tag.innerText = item.entity;
        tag.style.fontSize = `${12 + Math.log(item.count + 1) * 6}px`;
        entityCloud.appendChild(tag);
    });
}

function renderCategoryChart(data) {
    const canvas = document.getElementById("categoryChart");
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (window.categoryChartInstance) window.categoryChartInstance.destroy();

    window.categoryChartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: data.map(item => item.category),
            datasets: [{
                data: data.map(item => item.count),
                backgroundColor: ["#22c55e","#ef4444","#94a3b8","#3b82f6","#f59e0b","#8b5cf6","#ec4899","#14b8a6"],
                borderWidth: 2,
                borderColor: "#ffffff"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1, precision: 0 } }
            }
        }
    });
}

function renderSentimentChart(data) {
    const canvas = document.getElementById("sentimentChart");
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (window.sentimentChartInstance) window.sentimentChartInstance.destroy();

    // Fix color swap — map colors to labels correctly
    const colorMap = { positive: "#22c55e", negative: "#ef4444", neutral: "#94a3b8" };
    const colors = data.map(item => colorMap[item.sentiment] || "#94a3b8");

    window.sentimentChartInstance = new Chart(ctx, {
        type: "pie",
        data: {
            labels: data.map(item => item.sentiment),
            datasets: [{
                data: data.map(item => item.count),
                backgroundColor: colors,      // ← fixed
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: "bottom" } }
        }
    });
}

function renderTrendChart(data) {
    const canvas = document.getElementById('trendChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (window.trendChartInstance) window.trendChartInstance.destroy();

    const scores = data.map(t => t.score);

    window.trendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(t => t.date),
            datasets: [{
                label: 'Sentiment Score',
                data: scores,
                borderColor: '#3f6f59',
                borderWidth: 2,
                tension: 0.3,
                fill: false,
                pointBackgroundColor: scores.map(s => s > 0 ? '#22c55e' : s < 0 ? '#ef4444' : '#94a3b8'),
                pointBorderColor: '#ffffff',
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: -1, max: 1,
                    ticks: {
                        stepSize: 0.5,
                        callback: v => v === 1 ? 'Positive' : v === 0 ? 'Neutral' : v === -1 ? 'Negative' : v
                    }
                },
                x: { grid: { display: false } }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const val = ctx.raw;
                            return ` Score: ${val} (${val > 0 ? 'Positive' : val < 0 ? 'Negative' : 'Neutral'})`;
                        }
                    }
                }
            }
        }
    });
}

function renderActivityChart(data) {
    const canvas = document.getElementById('activityChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (window.activityChartInstance) window.activityChartInstance.destroy();

    window.activityChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(t => t.date),
            datasets: [{
                label: 'Articles',
                data: data.map(t => t.count),
                borderColor: '#3f6f59',
                backgroundColor: 'rgba(63, 111, 89, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1, precision: 0 }, grid: { display: false } },
                x: { grid: { display: false } }
            }
        }
    });
}

// In news.js
async function refreshStateData() {
    const btn = document.querySelector('.refresh-btn');
    const status = document.getElementById('refresh-status');
    
    btn.disabled = true;
    btn.innerText = "Clearing...";
    status.innerText = "";

    try {
        // Clear cache
        const deleteRes = await fetch(
            `http://127.0.0.1:8000/cache/${state}`,
            { method: "DELETE" }
        );
        if (!deleteRes.ok) throw new Error("Clear failed");

        btn.innerText = "Fetching...";

        // Refetch news
        const newsRes = await fetch(`http://127.0.0.1:8000/news/${state}`);
        if (!newsRes.ok) throw new Error("Fetch failed");

        const newsData = await newsRes.json();
        cachedNewsData = newsData;
        renderNews(newsData);

        // Reset analytics so it reloads on next tab switch
        window.analyticsLoaded = false;

        status.innerText = "Updated successfully";
        btn.innerText = "↻ Refresh Data";
        btn.disabled = false;

    } catch(error) {
        status.innerText = "Refresh failed. Try again.";
        btn.innerText = "↻ Refresh Data";
        btn.disabled = false;
        console.error("Refresh error:", error);
    }
}

function openModal(title, summary, img, url, date) {
    document.getElementById('modal-title').innerText = title;
    document.getElementById('modal-description').innerText = summary || "No summary available.";

    const modalImg = document.getElementById('modal-img');
    if (modalImg) modalImg.style.backgroundImage = img ? `url(${img})` : 'none';

    const linkEl = document.getElementById('modal-link');
    const dateEl = document.getElementById('modal-date');
    const modalView = document.getElementById('article-modal');

    if (linkEl) linkEl.href = url || "#";
    if (dateEl) dateEl.innerText = date;
    if (modalView) modalView.style.display = 'flex';
}

function closeModal() {
    const modalView = document.getElementById('article-modal');
    if (modalView) modalView.style.display = 'none';
}

window.onclick = function(event) {
    const modal = document.getElementById('article-modal');
    if (event.target === modal) closeModal();
}


fetchNews();