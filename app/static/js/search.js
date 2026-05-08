// Nirbhaya SafeTrack - Search with Nominatim Geocoding + Local Nodes

let nodesData = [];
let nodeSafetyCache = {};

const NOMINATIM_SEARCH = {
    enabled: true,
    viewbox: [77.15, 28.65, 77.28, 28.58],
    countrycodes: 'in',
};

function getSafetyColorForNode(node) {
    const zone = node.zone_id;
    if (nodeSafetyCache[zone] !== undefined) return nodeSafetyCache[zone];
    return 'neutral';
}

function highlightMatch(text, query) {
    if (!query) return text;
    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
}

function haversineDistance(lat1, lon1, lat2, lon2) {
    const R = 6371000;
    const toRad = x => x * Math.PI / 180;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function findNearestNode(lat, lon) {
    let nearest = null;
    let minDist = Infinity;
    for (const node of nodesData) {
        const dist = haversineDistance(lat, lon, node.lat, node.lon);
        if (dist < minDist) {
            minDist = dist;
            nearest = node;
        }
    }
    return { node: nearest, distance_m: Math.round(minDist) };
}

async function searchNominatim(query) {
    if (!NOMINATIM_SEARCH.enabled) return [];

    const params = new URLSearchParams({
        q: query,
        format: 'json',
        limit: '5',
        addressdetails: '1',
        viewbox: NOMINATIM_SEARCH.viewbox.join(','),
        bounded: '0',
        countrycodes: NOMINATIM_SEARCH.countrycodes,
        'accept-language': 'en',
    });

    try {
        const resp = await fetch(`https://nominatim.openstreetmap.org/search?${params}`, {
            headers: { 'User-Agent': 'NirbhayaSafeTrack/1.0' }
        });
        if (!resp.ok) return [];
        const results = await resp.json();
        return results.map(r => ({
            display_name: r.display_name,
            lat: parseFloat(r.lat),
            lon: parseFloat(r.lon),
            type: r.type || r.class || 'place',
            importance: parseFloat(r.importance || 0),
        }));
    } catch (err) {
        console.warn('Nominatim search failed:', err);
        return [];
    }
}

function initSearch(inputId, dropdownId, hiddenId) {
    const input = document.getElementById(inputId);
    const dropdown = document.getElementById(dropdownId);
    const hidden = document.getElementById(hiddenId);

    if (!input || !dropdown || !hidden) return;

    let selectedIndex = -1;
    let currentItems = [];
    let searchTimeout;

    function renderDropdown(results, type) {
        selectedIndex = -1;
        dropdown.innerHTML = '';
        currentItems = [];

        if (!results.length) {
            dropdown.innerHTML = `
                <div class="dropdown-empty">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
                    </svg>
                    <span>No locations found</span>
                </div>`;
            dropdown.classList.add('active');
            return;
        }

        const query = input.value.toLowerCase().trim();

        if (type === 'nominatim') {
            const header = document.createElement('div');
            header.className = 'dropdown-section-header';
            header.textContent = 'Search Results';
            dropdown.appendChild(header);
        }

        results.forEach((item, idx) => {
            const isNom = type === 'nominatim';
            const name = isNom ? (item.display_name.split(',')[0]) : item.name;
            const subtitle = isNom ? (item.display_name.split(',').slice(1, 3).join(',').trim()) : `${item.zone_id}`;

            const itemEl = document.createElement('div');
            itemEl.className = `dropdown-item ${isNom ? 'nominatim-result' : ''}`;
            itemEl.dataset.index = idx;
            itemEl.innerHTML = `
                <div class="dropdown-left">
                    <svg class="dropdown-pin" width="14" height="14" viewBox="0 0 24 24" fill="${isNom ? 'currentColor' : 'currentColor'}" opacity="0.5">
                        ${isNom
                            ? '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>'
                            : '<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>'
                        }
                    </svg>
                    <div class="dropdown-info">
                        <span class="dropdown-name">${highlightMatch(name, query)}</span>
                        <span class="dropdown-meta">
                            ${isNom
                                ? `<span class="dropdown-badge nom">${item.type}</span><span class="dropdown-coords">${item.lat.toFixed(4)}, ${item.lon.toFixed(4)}</span>`
                                : `<span class="dropdown-badge">${item.zone_id}</span><span class="dropdown-coords">${item.lat.toFixed(4)}, ${item.lon.toFixed(4)}</span>`
                            }
                        </span>
                    </div>
                </div>
                ${!isNom ? `<div class="dropdown-right"><span class="safety-dot ${getSafetyColorForNode(item)}"></span></div>` : ''}
            `;

            itemEl.addEventListener('click', () => {
                if (isNom) {
                    selectNominatimResult(item, input, hidden, dropdown);
                } else {
                    selectNode(item, input, hidden, dropdown);
                }
            });

            itemEl.addEventListener('mouseenter', () => {
                currentItems.forEach(el => el.classList.remove('highlighted'));
                itemEl.classList.add('highlighted');
                selectedIndex = idx;
            });

            dropdown.appendChild(itemEl);
            currentItems.push(itemEl);
        });

        dropdown.classList.add('active');
    }

    async function performSearch(query) {
        if (!query || query.length < 2) {
            dropdown.classList.remove('active');
            return;
        }

        const localMatches = nodesData.filter(n =>
            n.name.toLowerCase().includes(query) ||
            n.zone_id.toLowerCase().includes(query)
        ).slice(0, 5);

        const nominatimResults = await searchNominatim(query);

        const allResults = [...localMatches, ...nominatimResults];
        const hasNom = nominatimResults.length > 0;

        if (!allResults.length) {
            dropdown.innerHTML = `
                <div class="dropdown-empty">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
                    </svg>
                    <span>No locations found</span>
                </div>`;
            dropdown.classList.add('active');
            return;
        }

        renderDropdown(allResults, hasNom && localMatches.length ? 'mixed' : (hasNom ? 'nominatim' : 'local'));
    }

    function selectNode(node, inputEl, hiddenEl, dropdownEl) {
        inputEl.value = node.name;
        hiddenEl.value = node.id;
        dropdownEl.classList.remove('active');
        dropdownEl.innerHTML = '';
        currentItems = [];
        selectedIndex = -1;

        inputEl.classList.add('selected');
        setTimeout(() => inputEl.classList.remove('selected'), 300);

        window.dispatchEvent(new CustomEvent('node-selected', {
            detail: { field: inputId, nodeId: node.id, nodeName: node.name, node }
        }));
    }

    function selectNominatimResult(result, inputEl, hiddenEl, dropdownEl) {
        const { node, distance_m } = findNearestNode(result.lat, result.lon);
        if (!node) {
            inputEl.value = result.display_name.split(',')[0];
            hiddenEl.value = '';
            dropdownEl.classList.remove('active');
            console.warn('[Search] Nearest node not found for', result.display_name);
            return;
        }

        if (distance_m > 500) {
            console.warn('[Search] Nearest node', node.id, 'is', distance_m, 'm from', result.display_name);
        }

        const shortName = result.display_name.split(',')[0];
        inputEl.value = `${shortName} → ${node.name}`;
        hiddenEl.value = node.id;
        dropdownEl.classList.remove('active');
        dropdownEl.innerHTML = '';
        currentItems = [];
        selectedIndex = -1;

        inputEl.classList.add('selected');
        setTimeout(() => inputEl.classList.remove('selected'), 300);

        window.dispatchEvent(new CustomEvent('node-selected', {
            detail: { field: inputId, nodeId: node.id, nodeName: node.name, node, nominatimResult: result, distance_m }
        }));
    }

    input.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        const query = input.value.trim();
        searchTimeout = setTimeout(() => performSearch(query.toLowerCase()), 300);
    });

    input.addEventListener('keydown', (e) => {
        if (!dropdown.classList.contains('active') || !currentItems.length) {
            if (e.key === 'ArrowDown' && input.value.trim().length >= 2) {
                performSearch(input.value.toLowerCase().trim());
            }
            return;
        }

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            selectedIndex = Math.min(selectedIndex + 1, currentItems.length - 1);
            currentItems.forEach((el, i) => el.classList.toggle('highlighted', i === selectedIndex));
            if (currentItems[selectedIndex]) currentItems[selectedIndex].scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            selectedIndex = Math.max(selectedIndex - 1, 0);
            currentItems.forEach((el, i) => el.classList.toggle('highlighted', i === selectedIndex));
            if (currentItems[selectedIndex]) currentItems[selectedIndex].scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (selectedIndex >= 0 && currentItems[selectedIndex]) {
                currentItems[selectedIndex].click();
            }
        } else if (e.key === 'Escape') {
            dropdown.classList.remove('active');
        }
    });

    input.addEventListener('focus', () => {
        if (input.value.length >= 2) {
            performSearch(input.value.toLowerCase().trim());
        }
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest(`#${inputId}`) && !e.target.closest(`#${dropdownId}`)) {
            dropdown.classList.remove('active');
        }
    });
}

function loadNodesForSearch() {
    return fetch('/api/nodes')
        .then(res => res.json())
        .then(data => {
            nodesData = data.nodes;

            fetch('/api/safety/heatmap?hour=20')
                .then(r => r.json())
                .then(heatmapData => {
                    heatmapData.zones.forEach(z => {
                        nodeSafetyCache[z.zone_id] = z.score < 0.25 ? 'safe' : z.score < 0.45 ? 'caution' : z.score < 0.6 ? 'warning' : 'danger';
                    });
                })
                .catch(() => {
                    nodesData.forEach(n => { nodeSafetyCache[n.zone_id] = 'neutral'; });
                });

            initSearch('origin-search', 'origin-dropdown', 'origin');
            initSearch('destination-search', 'destination-dropdown', 'destination');
        })
        .catch(err => console.error('Failed to load nodes:', err));
}
