// Nirbhaya SafeTrack - Explanation Module

const FACTOR_COLORS = {
    crime: '#ef4444',
    lighting: '#fbbf24',
    isolation: '#a78bfa',
    crowd: '#34d399',
    emergency: '#60a5fa',
    transit: '#f472b6',
    community: '#ec4899',
};

const MODE_LABELS = {
    fastest: 'Fastest Route',
    safest: 'Safest Route',
    balanced: 'Balanced Route',
};

function showExplanation(mode, routeData) {
    if (!routeData) {
        console.warn('[Explain] No route data for', mode);
        return;
    }

    var sheet = document.getElementById('explanation-sheet');
    var badge = document.getElementById('route-mode-badge');
    var confBadge = document.getElementById('confidence-badge');
    var text = document.getElementById('explanation-text');

    if (!sheet || !badge || !confBadge || !text) {
        console.warn('[Explain] Missing DOM elements for explanation');
        return;
    }

    badge.textContent = MODE_LABELS[mode] || mode.charAt(0).toUpperCase() + mode.slice(1) + ' Route';
    badge.className = 'mode-badge ' + mode;

    var safetyScore = typeof routeData.safety_score === 'number' ? routeData.safety_score : 0;
    var confidence = safetyScore < 0.3 ? 'high' : safetyScore < 0.5 ? 'medium' : 'low';
    confBadge.textContent = confidence.charAt(0).toUpperCase() + confidence.slice(1) + ' Confidence';
    confBadge.className = 'confidence-badge ' + confidence;

    text.textContent = routeData.explanation || 'No explanation available.';

    var safetyDisplay = (1 - safetyScore).toFixed(2);
    var safetyScoreEl = document.getElementById('safety-score');
    if (safetyScoreEl) {
        safetyScoreEl.textContent = safetyDisplay;
        safetyScoreEl.style.color = getSafetyBarColor(safetyScore);
    }

    var dist = typeof routeData.distance_m === 'number' ? routeData.distance_m : 0;
    var distEl = document.getElementById('route-distance');
    if (distEl) {
        distEl.textContent = dist > 1000 ? (dist / 1000).toFixed(1) + ' km' : Math.round(dist) + ' m';
    }

    var walkTime = Math.round(dist / 80);
    var walkEl = document.getElementById('route-walk-time');
    if (walkEl) {
        walkEl.textContent = walkTime < 60 ? walkTime + ' min' : Math.floor(walkTime / 60) + 'h ' + walkTime % 60 + 'm';
    }

    var timeInput = document.getElementById('departure-time');
    if (timeInput) {
        var hour = parseInt(timeInput.value.split(':')[0]) || 0;
        var periods = ['Late Night', 'Late Night', 'Late Night', 'Late Night', 'Late Night',
                       'Dawn', 'Dawn', 'Morning', 'Morning', 'Daytime', 'Daytime', 'Daytime',
                       'Daytime', 'Daytime', 'Daytime', 'Daytime', 'Evening', 'Evening',
                       'Evening', 'Night', 'Night', 'Night', 'Night', 'Night'];
        var ctxEl = document.getElementById('time-context');
        if (ctxEl) ctxEl.textContent = hour.toString().padStart(2, '0') + ':00 \u2014 ' + periods[hour];
    }

    try {
        renderFactorBars(routeData.factor_breakdowns || []);
    } catch (e) {
        console.warn('[Explain] renderFactorBars failed:', e);
    }

    setTimeout(function () { sheet.classList.add('visible'); }, 100);
}

function renderFactorBars(breakdowns) {
    if (!breakdowns || !breakdowns.length) return;

    var avgFactors = {};
    var factorNames = ['crime', 'lighting', 'isolation', 'crowd', 'emergency', 'transit', 'community'];

    factorNames.forEach(function (name) {
        var values = breakdowns.map(function (f) { return typeof f[name] === 'number' ? f[name] : 0; });
        avgFactors[name] = values.reduce(function (a, b) { return a + b; }, 0) / values.length;
    });

    var total = Object.values(avgFactors).reduce(function (a, b) { return a + b; }, 0) || 1;

    var barsEl = document.getElementById('factor-bars');
    if (!barsEl) {
        console.warn('[Explain] factor-bars element not found');
        return;
    }
    barsEl.innerHTML = '';

    var sortedFactors = factorNames.slice().sort(function (a, b) { return avgFactors[b] - avgFactors[a]; });

    sortedFactors.forEach(function (factor, idx) {
        try {
            var pct = Math.round((avgFactors[factor] / total) * 100);
            var label = factor.charAt(0).toUpperCase() + factor.slice(1);
            var color = FACTOR_COLORS[factor] || '#888';

            var bar = document.createElement('div');
            bar.className = 'factor-bar-row';
            bar.innerHTML = '\
                <span class="factor-bar-label">' + label + '</span>\
                <span class="factor-bar-value">' + pct + '%</span>\
                <div class="factor-bar-track">\
                    <div class="factor-bar-fill" style="--target-width: ' + pct + '%; background: ' + color + ';"></div>\
                </div>';

            barsEl.appendChild(bar);

            requestAnimationFrame(function () {
                setTimeout(function () {
                    var fill = bar.querySelector('.factor-bar-fill');
                    if (fill) fill.style.width = pct + '%';
                }, idx * 80);
            });
        } catch (e) {
            console.warn('[Explain] Error rendering factor bar for', factor, ':', e);
        }
    });
}

function getSafetyBarColor(score) {
    if (score < 0.2) return '#10b981';
    if (score < 0.35) return '#34d399';
    if (score < 0.5) return '#fbbf24';
    return '#ef4444';
}

function hideExplanation() {
    var sheet = document.getElementById('explanation-sheet');
    if (sheet) sheet.classList.remove('visible');
}

document.addEventListener('DOMContentLoaded', function () {
    var closeBtn = document.getElementById('sheet-close');
    if (closeBtn) closeBtn.addEventListener('click', hideExplanation);
});
