// Nirbhaya SafeTrack - Map Module

let map;
let nodeMarkers = [];
let routeLayers = {};
let heatmapLayer = null;
let heatmapZoneLayers = [];
let originMarker = null;
let destMarker = null;
let segmentRiskLayers = [];
let emergencyMarkers = [];

let segmentRiskData = [];
let emergencyFacilities = [];
let safetyIntelligence = null;

const ROUTE_STYLES = {
    fastest: { color: '#f59e0b', glow: 'rgba(245, 158, 11, 0.25)' },
    safest: { color: '#10b981', glow: 'rgba(16, 185, 129, 0.25)' },
    balanced: { color: '#8b5cf6', glow: 'rgba(139, 92, 246, 0.25)' },
};

let zoneSafetyData = {};

function initMap() {
    map = L.map('map', { zoomControl: false, attributionControl: true })
        .setView([28.6139, 77.2090], 15);

    L.control.zoom({ position: 'topright' }).addTo(map);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
        maxZoom: 19,
        subdomains: 'abcd',
    }).addTo(map);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png', {
        maxZoom: 19, subdomains: 'abcd', pane: 'overlayPane',
    }).addTo(map);
}

function createRippleIcon(color) {
    return L.divIcon({
        html: `<div class="custom-marker ${color}"><div class="marker-dot"></div><div class="marker-ripple"></div><div class="marker-ripple"></div><div class="marker-ripple"></div></div>`,
        className: 'custom-marker-wrapper',
        iconSize: [36, 36], iconAnchor: [18, 18],
    });
}

function setOriginMarker(node) {
    if (originMarker) map.removeLayer(originMarker);
    originMarker = L.marker([node.lat, node.lon], { icon: createRippleIcon('origin'), zIndexOffset: 1000 }).addTo(map);
    originMarker.bindTooltip(`Origin: ${node.name}`, { direction: 'top', offset: [0, -20] });
    map.flyTo([node.lat, node.lon], 15, { duration: 0.8 });
}

function setDestMarker(node) {
    if (destMarker) map.removeLayer(destMarker);
    destMarker = L.marker([node.lat, node.lon], { icon: createRippleIcon('destination'), zIndexOffset: 1000 }).addTo(map);
    destMarker.bindTooltip(`Destination: ${node.name}`, { direction: 'top', offset: [0, -20] });
}

function clearRoutes() {
    Object.values(routeLayers).forEach(layers => {
        if (layers.glow) map.removeLayer(layers.glow);
        if (layers.base) map.removeLayer(layers.base);
    });
    routeLayers = {};
    clearSegmentRisks();
}

function clearSegmentRisks() {
    segmentRiskLayers.forEach(l => map.removeLayer(l));
    segmentRiskLayers = [];
}

function parseCoordsToLatLngs(coordinates) {
    if (!coordinates || coordinates.length < 2) return null;
    const latlngs = [];
    for (var i = 0; i < coordinates.length; i++) {
        var c = coordinates[i];
        if (c == null || typeof c.lat !== 'number' || typeof c.lon !== 'number') {
            console.warn('[Map] BAD COORD at index', i, ':', JSON.stringify(c));
            return null;
        }
        latlngs.push([c.lat, c.lon]);
    }
    return latlngs;
}

function drawRoute(coordinates, mode) {
    const latlngs = parseCoordsToLatLngs(coordinates);
    if (!latlngs) return null;

    const style = ROUTE_STYLES[mode] || ROUTE_STYLES.balanced;

    const glowLine = L.polyline(latlngs, {
        color: style.glow,
        weight: 14,
        opacity: 0.3,
        lineCap: 'round',
        lineJoin: 'round',
        interactive: false,
    }).addTo(map);

    const baseLine = L.polyline(latlngs, {
        color: style.color,
        weight: 4,
        opacity: 1,
        lineCap: 'round',
        lineJoin: 'round',
    }).addTo(map);

    routeLayers[mode] = { glow: glowLine, base: baseLine };
    baseLine.bindTooltip(mode.charAt(0).toUpperCase() + mode.slice(1) + ' Route', { sticky: true });

    return baseLine;
}

function highlightRoute(mode) {
    Object.entries(routeLayers).forEach(([m, layers]) => {
        if (!layers.base || !layers.glow) return;
        if (m === mode) {
            layers.base.setStyle({ weight: 5.5, opacity: 1 });
            layers.glow.setStyle({ weight: 16, opacity: 0.4 });
            layers.base.bringToFront();
            layers.glow.bringToFront();
        } else {
            layers.base.setStyle({ weight: 2.5, opacity: 0.3 });
            layers.glow.setStyle({ weight: 8, opacity: 0.08 });
        }
    });
}

function resetRouteHighlights() {
    Object.entries(routeLayers).forEach(([m, layers]) => {
        if (!layers.base || !layers.glow) return;
        layers.base.setStyle({ weight: 4, opacity: 1 });
        layers.glow.setStyle({ weight: 14, opacity: 0.3 });
    });
}

function highlightRiskySegments(segments) {
    clearSegmentRisks();
    if (!segments || !segments.length) return;

    const isNight = parseInt(document.getElementById('departure-time').value.split(':')[0]) >= 20;

    segments.forEach(seg => {
        if (seg.risk_score < 0.45 && !seg.is_low_visibility) return;

        const risk = seg.risk_score;
        const color = risk > 0.65 ? '#ef4444' : risk > 0.5 ? '#f97316' : seg.is_low_visibility ? '#f59e0b' : '#fbbf24';
        const weight = risk > 0.65 ? 8 : seg.is_low_visibility ? 6 : 5;
        const opacity = isNight ? 0.7 : 0.4;

        const line = L.polyline([[seg.lat_start, seg.lon_start], [seg.lat_end, seg.lon_end]], {
            color, weight, opacity,
            lineCap: 'round', dashArray: seg.is_low_visibility ? '4, 4' : null,
        }).addTo(map);

        let tooltipMsg;
        if (seg.is_low_visibility) {
            tooltipMsg = `⚠ Low visibility after 8 PM<br><small>${seg.name} • Lighting: ${(seg.lighting_score * 100).toFixed(0)}%</small>`;
        } else if (risk > 0.65) {
            tooltipMsg = `🔴 High risk segment<br><small>${seg.name} • Isolation: ${(seg.isolation_index * 100).toFixed(0)}%</small>`;
        } else {
            tooltipMsg = `🟡 Moderate risk<br><small>${seg.name} • Score: ${(risk * 100).toFixed(0)}%</small>`;
        }

        line.bindTooltip(tooltipMsg, { sticky: true, className: 'zone-tooltip' });
        segmentRiskLayers.push(line);
    });
}

function addEmergencyMarkers(facilities) {
    emergencyMarkers.forEach(m => map.removeLayer(m));
    emergencyMarkers = [];

    const iconMap = {
        police_station: { emoji: '🛡️', color: '#3b82f6', label: 'Police' },
        hospital: { emoji: '🏥', color: '#ef4444', label: 'Hospital' },
        emergency_helpdesk: { emoji: '📞', color: '#f59e0b', label: 'Help Desk' },
    };

    facilities.forEach(fac => {
        const info = iconMap[fac.type] || { emoji: '📍', color: '#888', label: fac.type };
        const icon = L.divIcon({
            html: `<div class="checkpoint-marker" style="background: ${info.color}; border-color: white;">
                        <span>${info.emoji}</span>
                    </div>`,
            className: 'checkpoint-wrapper',
            iconSize: [24, 24], iconAnchor: [12, 12],
        });

        const marker = L.marker([fac.lat, fac.lon], { icon, zIndexOffset: 500 }).addTo(map);
        const opTag = fac.operational_24h ? '24/7' : 'Limited hours';
        marker.bindTooltip(`<b>${fac.name}</b><br>${info.label} • ${opTag}`, { direction: 'top', offset: [0, -14] });
        emergencyMarkers.push(marker);
    });
}

function toggleHeatmap() {
    const hour = parseInt(document.getElementById('departure-time').value.split(':')[0]);

    if (heatmapLayer) {
        map.removeLayer(heatmapLayer);
        heatmapZoneLayers.forEach(l => map.removeLayer(l));
        heatmapLayer = null;
        heatmapZoneLayers = [];
        return;
    }

    fetch(`/api/safety/heatmap?hour=${hour}`)
        .then(res => res.json())
        .then(data => {
            zoneSafetyData = {};
            data.zones.forEach(z => { zoneSafetyData[z.zone_id] = z; });

            const group = L.layerGroup();

            data.zones.forEach(zone => {
                const risk = zone.score;
                const color = getHeatmapColor(risk);
                const radius = 60 + risk * 80;
                const opacity = 0.08 + risk * 0.22;

                const circle = L.circle([zone.lat, zone.lon], {
                    radius, fillColor: color, color, weight: 1,
                    fillOpacity: opacity, opacity: opacity * 0.5,
                });

                const riskLabel = risk < 0.25 ? 'Safe' : risk < 0.45 ? 'Moderate Caution' : risk < 0.6 ? 'High Caution' : 'High Risk';
                const za = zone.attributes || {};

                const communityReports = zone.zone_reports || 0;
                const communityPenalty = zone.community_penalty || 0;
                const commHtml = communityReports > 0
                    ? `<div class="tooltip-factor"><span class="tf-label">Community</span><span class="tf-val" style="color: #ec4899;">${communityReports} report${communityReports > 1 ? 's' : ''}</span></div>`
                    : '';

                circle.bindTooltip(`
                    <div class="zone-tooltip-content">
                        <div class="zone-tooltip-header">
                            <span class="zone-tooltip-name">${zone.name}</span>
                            <span class="zone-tooltip-risk" style="color: ${color}">${riskLabel}</span>
                        </div>
                        <div class="zone-tooltip-score">Safety: ${(1 - risk).toFixed(2)} / 1.00</div>
                        <div class="zone-tooltip-factors">
                            <div class="tooltip-factor"><span class="tf-label">Lighting</span><span class="tf-val">${za.lighting_score ? (za.lighting_score * 100).toFixed(0) + '%' : '—'}</span></div>
                            <div class="tooltip-factor"><span class="tf-label">Isolation</span><span class="tf-val">${za.isolation_index ? (za.isolation_index * 100).toFixed(0) + '%' : '—'}</span></div>
                            <div class="tooltip-factor"><span class="tf-label">Emergency</span><span class="tf-val">${za.emergency_facility_within_500m ? 'Nearby' : 'None'}</span></div>
                            <div class="tooltip-factor"><span class="tf-label">Transit</span><span class="tf-val">${za.transit_accessibility ? (za.transit_accessibility * 100).toFixed(0) + '%' : '—'}</span></div>
                            ${commHtml}
                        </div>
                    </div>
                `, { sticky: true, className: 'zone-tooltip', direction: 'top', offset: [0, -10] });

                circle.addTo(group);
                heatmapZoneLayers.push(circle);
            });

            heatmapLayer = group.addTo(map);
        })
        .catch(err => console.error('Heatmap failed:', err));
}

function getHeatmapColor(score) {
    if (score < 0.2) return '#10b981';
    if (score < 0.35) return '#84cc16';
    if (score < 0.5) return '#fbbf24';
    if (score < 0.65) return '#f97316';
    return '#ef4444';
}

function fitMapToRoutes() {
    const allLayers = Object.values(routeLayers).map(l => l.base).filter(Boolean);
    if (!allLayers.length) return;
    map.fitBounds(L.featureGroup(allLayers).getBounds().pad(0.12));
}

let checkpointsVisible = false;

function toggleCheckpoints() {
    checkpointsVisible = !checkpointsVisible;
    const btn = document.getElementById('toggle-checkpoints');
    if (btn) btn.classList.toggle('active', checkpointsVisible);

    if (checkpointsVisible && emergencyFacilities.length) {
        addEmergencyMarkers(emergencyFacilities);
    } else {
        emergencyMarkers.forEach(m => map.removeLayer(m));
        emergencyMarkers = [];
    }
}

function cinematicDemo(originNode, destNode) {
    if (!originNode || !destNode) return;

    map.flyTo([originNode.lat, originNode.lon], 14, { duration: 1 });

    setTimeout(() => {
        map.flyTo([destNode.lat, destNode.lon], 15, { duration: 1.2 });
    }, 1200);

    setTimeout(() => {
        const midLat = (originNode.lat + destNode.lat) / 2;
        const midLon = (originNode.lon + destNode.lon) / 2;
        map.flyTo([midLat, midLon], 14.5, { duration: 1 });
    }, 2600);
}

function updateSafetyIntelligence(data) {
    safetyIntelligence = data;
    const bar = document.getElementById('safety-intelligence-bar');
    if (!bar || !data) return;

    const pulseClass = data.high_risk_zones > 3 ? 'alert' : '';
    bar.className = `safety-intelligence-bar ${pulseClass}`;

    document.getElementById('si-incidents').textContent = data.total_incidents;
    document.getElementById('si-zones').textContent = data.total_zones;
    document.getElementById('si-risk').textContent = data.high_risk_zones;
    document.getElementById('si-period').textContent = data.time_period;

    const communityEl = document.getElementById('si-community');
    if (data.community_reports !== undefined) {
        if (!communityEl) {
            const barEl = bar;
            const commSpan = document.createElement('span');
            commSpan.className = 'si-stat';
            commSpan.id = 'si-community';
            commSpan.innerHTML = `| <strong id="si-comm-count">${data.community_reports}</strong> community reports`;
            commSpan.style.marginLeft = '4px';
            barEl.appendChild(commSpan);
        } else {
            document.getElementById('si-comm-count').textContent = data.community_reports;
        }
    }

    bar.style.display = 'flex';
}

function updateScoreWithTransition(elementId, newScore, oldScore) {
    const el = document.getElementById(elementId);
    if (!el) return;

    const start = oldScore || 0;
    const end = newScore;
    const duration = 800;
    const startTime = performance.now();

    function animate(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = start + (end - start) * eased;
        const pct = Math.round((1 - current) * 100);

        el.textContent = `${pct}%`;
        el.style.color = getSafetyBarColor(current);

        if (progress < 1) {
            requestAnimationFrame(animate);
        } else {
            el.classList.add('score-pulse');
            setTimeout(() => el.classList.remove('score-pulse'), 600);
        }
    }

    requestAnimationFrame(animate);
}

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    document.getElementById('toggle-heatmap').addEventListener('click', toggleHeatmap);
    document.getElementById('toggle-checkpoints').addEventListener('click', toggleCheckpoints);

    window.addEventListener('node-selected', (e) => {
        const { node, field } = e.detail;
        if (field === 'origin-search') setOriginMarker(node);
        if (field === 'destination-search') setDestMarker(node);
    });

    updateTimeContext();
    document.getElementById('departure-time').addEventListener('change', updateTimeContext);

    loadNodesForSearch().then(() => {
        fetch('/api/safety/emergency')
            .then(res => res.json())
            .then(data => {
                emergencyFacilities = data.facilities || [];
            })
            .catch(() => {});

        setTimeout(() => {
            runDemoRoute('N001', 'N007', null);
        }, 500);
    });
});

function updateTimeContext() {
    const hour = parseInt(document.getElementById('departure-time').value.split(':')[0]);
    const el = document.getElementById('time-context-text');
    if (!el) return;

    let msg;
    if (hour >= 22 || hour < 5) {
        msg = '<strong>Nighttime risk elevated</strong> — community reports note low visibility after 10 PM. Lighting concerns factor into route scoring.';
    } else if (hour >= 18 && hour < 22) {
        msg = '<strong>Evening transition</strong> — community reports highlight lighting concerns and limited emergency access as visibility drops.';
    } else if (hour >= 5 && hour < 8) {
        msg = '<strong>Early morning</strong> — moderate risk with increasing commuter traffic improving natural surveillance.';
    } else if (hour >= 8 && hour < 12) {
        msg = '<strong>Daytime peak safety</strong> — high foot traffic and full visibility create optimal conditions for safe routes.';
    } else if (hour >= 12 && hour < 18) {
        msg = '<strong>Afternoon conditions</strong> — good visibility maintained, moderate crowd density supports safer corridors.';
    } else {
        msg = '<strong>Current conditions</strong> — safety scores adjusted for time-based risk factors and community feedback.';
    }

    el.innerHTML = msg;
}

function getSafetyBarColor(score) {
    if (score < 0.2) return '#10b981';
    if (score < 0.35) return '#34d399';
    if (score < 0.5) return '#fbbf24';
    return '#ef4444';
}
