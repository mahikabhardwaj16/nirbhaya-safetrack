// Nirbhaya SafeTrack - Route Module

let currentRoutes = {};
let selectedRouteMode = null;
let previousSafetyScores = {};
let lastRenderSuccess = false;

function getSelectedMode() {
    const selected = document.querySelector('input[name="mode"]:checked');
    return selected ? selected.value : 'balanced';
}

function getUserPreferences() {
    return {
        crime: parseFloat(document.getElementById('crime-weight').value),
        lighting: parseFloat(document.getElementById('lighting-weight').value),
        isolation: parseFloat(document.getElementById('isolation-weight').value),
        crowd: parseFloat(document.getElementById('crowd-weight').value),
        emergency: parseFloat(document.getElementById('emergency-weight').value),
        transit: parseFloat(document.getElementById('transit-weight').value),
    };
}

function normalizeWeights(weights) {
    const total = Object.values(weights).reduce((a, b) => a + b, 0);
    if (total === 0) return { crime: 0.3, lighting: 0.2, isolation: 0.2, crowd: 0.1, emergency: 0.1, transit: 0.1 };
    return Object.fromEntries(Object.entries(weights).map(([k, v]) => [k, v / total]));
}

function setButtonLoading(loading) {
    const btn = document.getElementById('compute-btn');
    if (!btn) return;
    const textEl = btn.querySelector('.btn-text');
    if (loading) {
        btn.classList.add('loading');
        btn.classList.remove('success');
        if (textEl) textEl.textContent = 'Computing...';
    } else {
        btn.classList.remove('loading');
        btn.classList.add('success');
        if (textEl) textEl.textContent = 'Routes Ready!';
        setTimeout(() => {
            btn.classList.remove('success');
            if (textEl) textEl.textContent = 'Compute Routes';
        }, 2000);
    }
}

function triggerButtonRipple() {
    const btn = document.getElementById('compute-btn');
    if (!btn) return;
    btn.classList.remove('ripple');
    void btn.offsetWidth;
    btn.classList.add('ripple');
    setTimeout(() => btn.classList.remove('ripple'), 600);
}

function showToast(message, type) {
    const container = document.getElementById('feedback-notification');
    if (!container) return;
    const icons = { error: '\u26A0\uFE0F', success: '\u2705', info: '\u2139\uFE0F', warning: '\u26A0\uFE0F' };
    const notif = document.createElement('div');
    notif.className = 'fn-entry';
    notif.innerHTML = '<div class="fn-icon" style="color: ' + (type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#3b82f6') + ';">' + (icons[type] || '\u2139\uFE0F') + '</div><div class="fn-body"><div class="fn-msg">' + message + '</div></div>';
    container.appendChild(notif);
    requestAnimationFrame(function () { notif.classList.add('fn-visible'); });
    setTimeout(function () {
        notif.classList.remove('fn-visible');
        setTimeout(function () { notif.remove(); }, 300);
    }, 4000);
}

function computeRoutes() {
    if (typeof dismissHero === 'function') dismissHero();
    const origin = document.getElementById('origin').value;
    const destination = document.getElementById('destination').value;
    const time = document.getElementById('departure-time').value;
    const weights = normalizeWeights(getUserPreferences());

    if (!origin || !destination) {
        shakeInput('origin-search');
        shakeInput('destination-search');
        return;
    }

    if (origin === destination) {
        showToast('Origin and destination must be different.', 'warning');
        return;
    }

    triggerButtonRipple();
    setButtonLoading(true);
    hideExplanation();
    hideRouteSummary();
    hideWhyNotPanel();
    lastRenderSuccess = false;

    fetch('/api/route/compute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            origin: origin,
            destination: destination,
            departure_time: time,
            mode: 'all',
            user_preferences: weights,
        }),
    })
        .then(function (res) {
            if (!res.ok) {
                console.error('[Route] Server returned', res.status, res.statusText);
                throw new Error('Server returned ' + res.status);
            }
            return res.json();
        })
        .then(function (data) {
            var modesAvailable = [];
            ['fastest', 'safest', 'balanced'].forEach(function (m) {
                if (data[m]) modesAvailable.push(m);
            });
            if (modesAvailable.length === 0) {
                console.error('[Route] No route modes in response');
                showToast('No route found between these locations.', 'warning');
                setButtonLoading(false);
                return;
            }

            currentRoutes = data;
            displayRoutes(data);
            setButtonLoading(false);

            if (lastRenderSuccess) {
                showToast('Route found \u2014 safety score computed', 'success');
            } else {
                console.warn('[Route] Route render had partial failures');
            }
        })
        .catch(function (err) {
            console.error('[Route] Error:', err.message);
            if (err instanceof TypeError && err.message.includes('fetch')) {
                showToast('Network error \u2014 server may be down.', 'error');
            } else if (!lastRenderSuccess) {
                showToast('Route computation failed \u2014 ' + err.message, 'error');
            } else {
                showToast('Route displayed with some issues.', 'warning');
            }
            setButtonLoading(false);
        });
}

function displayRoutes(data) {
    lastRenderSuccess = false;
    var renderedCount = 0;
    var totalModes = 0;

    try {
        clearRoutes();
    } catch (e) {
        console.warn('[Route] clearRoutes failed:', e);
    }

    try {
        if (data._safety_intelligence) {
            updateSafetyIntelligence(data._safety_intelligence);
        }
    } catch (e) {
        console.warn('[Route] updateSafetyIntelligence failed:', e);
    }

    var modes = ['fastest', 'safest', 'balanced'];

    modes.forEach(function (mode) {
        try {
            if (!data[mode]) {
                return;
            }
            totalModes++;

            var coords = data[mode].coordinates;
            if (!coords || !Array.isArray(coords) || coords.length < 2) {
                console.warn('[Route]', mode, 'has invalid coordinates:', coords ? coords.length : null);
                return;
            }

            drawRoute(coords, mode);
            renderedCount++;

            if (data[mode].nearby_emergency && Array.isArray(data[mode].nearby_emergency) && data[mode].nearby_emergency.length > 0) {
                try {
                    addEmergencyMarkers(data[mode].nearby_emergency);
                } catch (e) {
                    console.warn('[Route] addEmergencyMarkers failed:', e);
                }
            }

            try {
                highlightRiskySegments(data[mode].high_risk_segments || []);
            } catch (e) {
                console.warn('[Route] highlightRiskySegments failed:', e);
            }
        } catch (e) {
            console.error('[Route] Error processing mode', mode, ':', e);
        }
    });

    try {
        if (data._comparison) {
            showWhyNotPanel(data._comparison);
        }
    } catch (e) {
        console.warn('[Route] showWhyNotPanel failed:', e);
    }

    try {
        showRouteSummary(data);
    } catch (e) {
        console.warn('[Route] showRouteSummary failed:', e);
    }

    try {
        updateComparisonTable(data);
    } catch (e) {
        console.warn('[Route] updateComparisonTable failed:', e);
    }

    try {
        fitMapToRoutes();
    } catch (e) {
        console.warn('[Route] fitMapToRoutes failed:', e);
    }

    if (renderedCount > 0) {
        lastRenderSuccess = true;
        try {
            if (data.safest) {
                selectRoute('safest');
            } else if (data.fastest) {
                selectRoute('fastest');
            } else if (data.balanced) {
                selectRoute('balanced');
            }
        } catch (e) {
            console.warn('[Route] selectRoute failed:', e);
        }
    } else {
        console.error('[Route] No routes rendered at all');
    }
}

function showRouteSummary(data) {
    var panel = document.getElementById('route-summary');
    if (!panel) {
        console.warn('[Route] route-summary element not found');
        return;
    }

    var container = document.getElementById('route-summary-content');
    if (!container) {
        console.warn('[Route] route-summary-content element not found');
        return;
    }

    container.innerHTML = '';

    var modes = ['fastest', 'safest', 'balanced'];
    modes.forEach(function (mode) {
        try {
            if (!data[mode]) return;
            var route = data[mode];
            var safetyScore = typeof route.safety_score === 'number' ? route.safety_score : 0;
            var safetyPct = Math.round((1 - safetyScore) * 100);
            var safetyColor = getSafetyBarColor(safetyScore);
            var dist = typeof route.distance_m === 'number' ? route.distance_m : 0;
            var walkTime = Math.round(dist / 80);

            var emergencyCount = route.nearby_emergency && Array.isArray(route.nearby_emergency) ? route.nearby_emergency.length : 0;

            var card = document.createElement('div');
            card.className = 'summary-card ' + (selectedRouteMode === mode ? 'active' : '');
            card.dataset.mode = mode;
            card.innerHTML = '\
                <div class="summary-card-header">\
                    <span class="summary-mode-tag ' + mode + '">' + mode.charAt(0).toUpperCase() + mode.slice(1) + '</span>\
                </div>\
                <div class="summary-card-body">\
                    <div class="summary-stat">\
                        <span class="summary-stat-value">' + (dist / 1000).toFixed(2) + '</span>\
                        <span class="summary-stat-unit">km</span>\
                    </div>\
                    <div class="summary-stat">\
                        <span class="summary-stat-value" style="color: ' + safetyColor + ';">' + safetyPct + '%</span>\
                        <span class="summary-stat-unit">safe</span>\
                        <div class="safety-bar-mini" style="width: 28px;">\
                            <div class="safety-bar-fill" style="width: ' + safetyPct + '%; background: ' + safetyColor + ';"></div>\
                        </div>\
                    </div>\
                    <div class="summary-stat">\
                        <span class="summary-stat-value">' + walkTime + '</span>\
                        <span class="summary-stat-unit">min</span>\
                    </div>\
                    ' + (emergencyCount > 0 ? '<div class="summary-stat"><span class="summary-stat-value" style="color: #3b82f6;">' + emergencyCount + '</span><span class="summary-stat-unit">checkpoints</span></div>' : '') + '\
                </div>';

            card.addEventListener('click', function () { selectRoute(mode); });
            card.addEventListener('mouseenter', function () { highlightRoute(mode); });
            card.addEventListener('mouseleave', resetRouteHighlights);

            container.appendChild(card);
        } catch (e) {
            console.warn('[Route] Error creating summary card for', mode, ':', e);
        }
    });

    panel.style.display = 'block';
}

function hideRouteSummary() {
    var panel = document.getElementById('route-summary');
    if (panel) panel.style.display = 'none';
}

function showWhyNotPanel(comparison) {
    var container = document.getElementById('why-not-panel');
    if (!container) return;

    container.innerHTML = '';

    try {
        Object.entries(comparison).forEach(function (_ref) {
            var mode = _ref[0];
            var comp = _ref[1];
            if (!comp.tradeoffs || !Array.isArray(comp.tradeoffs)) return;
            comp.tradeoffs.forEach(function (tradeoff) {
                if (mode === 'safest' && tradeoff.compared_to === 'fastest') {
                    if (tradeoff.is_faster) {
                        var card = document.createElement('div');
                        card.className = 'why-not-card';
                        var safetyDiff = tradeoff.safety_diff_pct > 10 ? '<li>Safety score drops by ' + tradeoff.safety_diff_pct + '%</li>' : '';
                        card.innerHTML = '\
                            <div class="why-not-header">\
                                <span class="why-not-icon">\u26A1</span>\
                                <span class="why-not-title">Why not the Fastest route?</span>\
                            </div>\
                            <div class="why-not-content">\
                                <p class="why-not-tradeoff">\
                                    <span class="tradeoff-faster">Faster by ' + Math.abs(tradeoff.time_diff_min) + ' min</span>\
                                    <span class="tradeoff-but">But</span>\
                                </p>\
                                <ul class="why-not-reasons">\
                                    <li>Passes through low-light corridors</li>\
                                    <li>Higher nighttime isolation risk</li>\
                                    ' + safetyDiff + '\
                                </ul>\
                            </div>';
                        container.appendChild(card);
                    }
                }
            });
        });
    } catch (e) {
        console.warn('[Route] showWhyNotPanel error:', e);
    }

    if (container.children.length > 0) {
        container.style.display = 'block';
    }
}

function hideWhyNotPanel() {
    var container = document.getElementById('why-not-panel');
    if (container) {
        container.style.display = 'none';
        container.innerHTML = '';
    }
}

function updateComparisonTable(data) {
    var panel = document.getElementById('comparison-panel');
    var rows = document.getElementById('comparison-rows');
    if (!panel || !rows) return;

    if (!Object.keys(data).filter(function (k) { return k !== '_comparison' && k !== '_safety_intelligence'; }).length) {
        panel.style.display = 'none';
        return;
    }

    panel.style.display = 'block';
    rows.innerHTML = '';

    var modes = ['fastest', 'safest', 'balanced'];
    modes.forEach(function (mode) {
        try {
            if (!data[mode]) return;
            var route = data[mode];
            var safetyScore = typeof route.safety_score === 'number' ? route.safety_score : 0;
            var safetyPct = Math.round((1 - safetyScore) * 100);
            var safetyColor = getSafetyBarColor(safetyScore);
            var dist = typeof route.distance_m === 'number' ? route.distance_m : 0;
            var walkTime = Math.round(dist / 80);

            var row = document.createElement('div');
            row.className = 'comparison-row ' + (selectedRouteMode === mode ? 'active' : '');
            row.dataset.mode = mode;
            row.innerHTML = '\
                <span class="route-mode-tag ' + mode + '">' + mode.charAt(0).toUpperCase() + mode.slice(1) + '</span>\
                <span class="comparison-val">' + (dist / 1000).toFixed(2) + ' km</span>\
                <span class="comparison-val">\
                    <div class="safety-bar-mini">\
                        <div class="safety-bar-fill" style="width: ' + safetyPct + '%; background: ' + safetyColor + ';"></div>\
                    </div>\
                    ' + safetyPct + '%\
                </span>\
                <span class="comparison-val">~' + walkTime + ' min</span>';

            row.addEventListener('click', function () { selectRoute(mode); });
            row.addEventListener('mouseenter', function () { highlightRoute(mode); });
            row.addEventListener('mouseleave', resetRouteHighlights);

            rows.appendChild(row);
        } catch (e) {
            console.warn('[Route] Error in comparison row for', mode, ':', e);
        }
    });
}

function selectRoute(mode) {
    selectedRouteMode = mode;
    try {
        highlightRoute(mode);
    } catch (e) {
        console.warn('[Route] highlightRoute failed:', e);
    }

    try {
        document.querySelectorAll('.summary-card').forEach(function (card) {
            card.classList.toggle('active', card.dataset.mode === mode);
        });
    } catch (e) {
        console.warn('[Route] summary-card toggle failed:', e);
    }

    if (currentRoutes[mode]) {
        try {
            showExplanation(mode, currentRoutes[mode]);
        } catch (e) {
            console.warn('[Route] showExplanation failed:', e);
        }
    }
}

function showLoading(show) {
    var overlay = document.getElementById('loading-overlay');
    if (!overlay) return;
    if (show) {
        overlay.classList.add('visible');
    } else {
        overlay.classList.remove('visible');
    }
}

function hideExplanation() {
    var sheet = document.getElementById('explanation-sheet');
    if (sheet) sheet.classList.remove('visible');
}

function shakeInput(id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.style.animation = 'shake 0.4s ease';
    el.style.borderColor = '#ef4444';
    setTimeout(function () {
        el.style.animation = '';
        el.style.borderColor = '';
    }, 600);
}

function selectNodeById(nodeId, fieldId) {
    var searchInput = document.getElementById(fieldId);
    var hiddenInput = document.getElementById(fieldId.replace('-search', ''));
    var node = typeof nodesData !== 'undefined' ? nodesData.find(function (n) { return n.id === nodeId; }) : null;
    if (!node || !searchInput || !hiddenInput) return false;

    searchInput.value = node.name;
    hiddenInput.value = node.id;

    window.dispatchEvent(new CustomEvent('node-selected', {
        detail: { field: fieldId, nodeId: node.id, nodeName: node.name, node: node }
    }));
    return true;
}

function runDemoRoute(originId, destId, chipEl) {
    if (typeof dismissHero === 'function') dismissHero();
    document.querySelectorAll('.demo-chip').forEach(function (c) { return c.classList.remove('active'); });
    if (chipEl) chipEl.classList.add('active');

    var ok1 = selectNodeById(originId, 'origin-search');
    var ok2 = selectNodeById(destId, 'destination-search');

    if (ok1 && ok2) {
        var originNode = typeof nodesData !== 'undefined' ? nodesData.find(function (n) { return n.id === originId; }) : null;
        var destNode = typeof nodesData !== 'undefined' ? nodesData.find(function (n) { return n.id === destId; }) : null;
        if (originNode && destNode) {
            cinematicDemo(originNode, destNode);
        }
        setTimeout(function () { computeRoutes(); }, 1800);
    }
}

function recomputeWithNewHour(hour) {
    var origin = document.getElementById('origin').value;
    var destination = document.getElementById('destination').value;
    if (!origin || !destination || !Object.keys(currentRoutes).length) return;

    var timeStr = hour.toString().padStart(2, '0') + ':00';
    var weights = normalizeWeights(getUserPreferences());

    fetch('/api/route/compute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            origin: origin,
            destination: destination,
            departure_time: timeStr,
            mode: 'all',
            user_preferences: weights,
        }),
    })
        .then(function (res) {
            if (!res.ok) throw new Error('Timeline route failed: ' + res.status);
            return res.json();
        })
        .then(function (data) {
            var oldScores = {};
            try {
                Object.entries(currentRoutes).forEach(function (_ref2) {
                    var m = _ref2[0];
                    var r = _ref2[1];
                    if (m[0] !== '_') oldScores[m] = r.safety_score;
                });
            } catch (e) { /* ignore */ }

            currentRoutes = data;

            try {
                if (data._safety_intelligence) {
                    updateSafetyIntelligence(data._safety_intelligence);
                }
            } catch (e) {
                console.warn('[Route] timeline safety intel failed:', e);
            }

            try { clearRoutes(); } catch (e) { console.warn('[Route] timeline clearRoutes failed:', e); }

            var modes = ['fastest', 'safest', 'balanced'];
            modes.forEach(function (mode) {
                try {
                    if (!data[mode]) return;
                    var coords = data[mode].coordinates;
                    if (!coords || !Array.isArray(coords) || coords.length < 2) return;
                    drawRoute(coords, mode);
                    if (data[mode].nearby_emergency && Array.isArray(data[mode].nearby_emergency)) {
                        addEmergencyMarkers(data[mode].nearby_emergency);
                    }
                    highlightRiskySegments(data[mode].high_risk_segments || []);
                } catch (e) {
                    console.warn('[Route] timeline mode', mode, 'failed:', e);
                }
            });

            try { if (data._comparison) showWhyNotPanel(data._comparison); } catch (e) { /* ignore */ }
            try { showRouteSummary(data); } catch (e) { /* ignore */ }
            try { updateComparisonTable(data); } catch (e) { /* ignore */ }

            try {
                var scores = {};
                Object.entries(data).forEach(function (_ref3) {
                    var m = _ref3[0];
                    var route = _ref3[1];
                    if (m[0] !== '_') {
                        scores[m] = route.safety_score;
                        updateScoreWithTransition('summary-score-' + m, route.safety_score, oldScores[m]);
                    }
                });
            } catch (e) { /* ignore */ }

            var periods = ['Late Night', 'Late Night', 'Late Night', 'Late Night', 'Late Night',
                           'Dawn', 'Dawn', 'Morning', 'Morning', 'Daytime', 'Daytime', 'Daytime',
                           'Daytime', 'Daytime', 'Daytime', 'Daytime', 'Evening', 'Evening',
                           'Evening', 'Night', 'Night', 'Night', 'Night', 'Night'];
            var label = document.getElementById('timeline-label');
            if (label) label.textContent = timeStr + ' \u2014 ' + periods[hour];

            if (typeof updateTimeContext === 'function') updateTimeContext();

            if (selectedRouteMode && data[selectedRouteMode]) {
                try { showExplanation(selectedRouteMode, data[selectedRouteMode]); } catch (e) { /* ignore */ }
            }
        })
        .catch(function (err) {
            console.error('[Route] Timeline update failed:', err);
        });
}

document.addEventListener('DOMContentLoaded', function () {
    var sliderIds = [
        ['crime-weight', 'crime-weight-val'],
        ['lighting-weight', 'lighting-weight-val'],
        ['isolation-weight', 'isolation-weight-val'],
        ['crowd-weight', 'crowd-weight-val'],
        ['emergency-weight', 'emergency-weight-val'],
        ['transit-weight', 'transit-weight-val'],
    ];

    sliderIds.forEach(function (_ref4) {
        var sliderId = _ref4[0];
        var valId = _ref4[1];
        var slider = document.getElementById(sliderId);
        var valDisplay = document.getElementById(valId);
        if (slider && valDisplay) {
            slider.addEventListener('input', function () {
                valDisplay.textContent = Math.round(parseFloat(slider.value) * 100) + '%';
            });
        }
    });

    document.getElementById('route-form').addEventListener('submit', function (e) {
        e.preventDefault();
        computeRoutes();
    });

    var timelineSlider = document.getElementById('timeline-slider');
    if (timelineSlider) {
        timelineSlider.addEventListener('input', function () {
            var hour = parseInt(timelineSlider.value);
            var timeInput = document.getElementById('departure-time');
            if (timeInput) timeInput.value = hour.toString().padStart(2, '0') + ':00';
            recomputeWithNewHour(hour);
        });
    }

    var prefToggle = document.getElementById('pref-toggle');
    var prefContent = document.getElementById('pref-content');
    if (prefToggle && prefContent) {
        prefToggle.addEventListener('click', function () {
            prefContent.classList.toggle('collapsed');
            var arrow = prefToggle.querySelector('.toggle-arrow');
            if (arrow) arrow.classList.toggle('rotated');
        });
    }

    document.querySelectorAll('.demo-chip').forEach(function (chip) {
        chip.addEventListener('click', function () {
            var origin = chip.dataset.origin;
            var dest = chip.dataset.dest;
            runDemoRoute(origin, dest, chip);
        });
    });
});
