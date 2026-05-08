// Nirbhaya SafeTrack - Community Feedback Module

const FEEDBACK_ICONS = {
    lighting: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"/></svg>`,
    visibility: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`,
    emergency_access: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
    crowd_safety: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
    incident_report: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
};

const FEEDBACK_LABELS = {
    lighting: 'Lighting',
    visibility: 'Visibility',
    emergency_access: 'Emergency',
    crowd_safety: 'Crowd Safety',
    incident_report: 'Incident',
};

const SEVERITY_COLORS = {
    1: { bg: 'rgba(251, 191, 36, 0.1)', dot: '#fbbf24', label: 'Minor' },
    2: { bg: 'rgba(247, 127, 0, 0.1)', dot: '#f77f00', label: 'Moderate' },
    3: { bg: 'rgba(239, 68, 68, 0.1)', dot: '#ef4444', label: 'Critical' },
};

let feedbackPollInterval = null;
let lastFeedbackTimestamp = null;

function initCommunityFeedback() {
    loadFeedbackStats();
    loadRecentFeedback();

    document.getElementById('btn-report-concern').addEventListener('click', openFeedbackModal);
    document.getElementById('feedback-modal-close').addEventListener('click', closeFeedbackModal);
    document.getElementById('feedback-modal').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeFeedbackModal();
    });
    document.getElementById('feedback-report-form').addEventListener('submit', submitFeedbackReport);

    populateZoneDropdown();

    feedbackPollInterval = setInterval(pollNewFeedback, 15000);
}

function loadRecentFeedback() {
    fetch('/api/feedback/recent?limit=8')
        .then(res => res.json())
        .then(data => {
            renderFeedbackFeed(data.feedback);
            if (data.feedback.length > 0) {
                lastFeedbackTimestamp = data.feedback[0].timestamp;
            }
            simulateLiveNotification();
        })
        .catch(() => {});
}

function loadFeedbackStats() {
    fetch('/api/feedback/stats')
        .then(res => res.json())
        .then(data => {
            document.getElementById('fs-total').textContent = data.total_reports;
            document.getElementById('fs-zones').textContent = Object.keys(data.zone_concern_count || {}).length;

            if (data.by_type) {
                const sorted = Object.entries(data.by_type).sort((a, b) => b[1] - a[1]);
                if (sorted.length > 0) {
                    const topLabel = FEEDBACK_LABELS[sorted[0][0]] || sorted[0][0];
                    document.getElementById('fs-top-type').textContent = topLabel;
                }
            }
        })
        .catch(() => {});
}

function renderFeedbackFeed(items) {
    const feed = document.getElementById('feedback-feed');
    if (!items || items.length === 0) {
        feed.innerHTML = '<div class="feedback-empty">No community reports yet. Be the first!</div>';
        return;
    }

    feed.innerHTML = '';
    items.forEach((item, idx) => {
        const icon = FEEDBACK_ICONS[item.type] || FEEDBACK_ICONS.incident_report;
        const label = FEEDBACK_LABELS[item.type] || item.type;
        const sev = SEVERITY_COLORS[item.severity] || SEVERITY_COLORS[1];
        const timeAgo = getTimeAgo(item.timestamp);
        const upvoteLabel = item.upvotes > 0 ? `<span class="fb-upvotes">+${item.upvotes}</span>` : '';

        const el = document.createElement('div');
        el.className = `feedback-item ${idx < 2 ? 'fresh' : ''}`;
        el.style.setProperty('--idx', idx);
        el.innerHTML = `
            <div class="fb-icon" style="color: ${sev.dot};">${icon}</div>
            <div class="fb-body">
                <div class="fb-header">
                    <span class="fb-type">${label}</span>
                    <span class="fb-severity-dot" style="background: ${sev.dot};"></span>
                    <span class="fb-zone">${item.zone_name || item.zone_id}</span>
                    ${upvoteLabel}
                </div>
                <div class="fb-message">${item.message}</div>
                <div class="fb-time">${timeAgo}</div>
            </div>
        `;
        feed.appendChild(el);
    });
}

function pollNewFeedback() {
    let url = '/api/feedback/recent?limit=3';
    if (lastFeedbackTimestamp) {
        url += '&since=' + encodeURIComponent(lastFeedbackTimestamp);
    }
    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (data.feedback && data.feedback.length > 0) {
                const latest = data.feedback[0];
                if (latest.timestamp !== lastFeedbackTimestamp) {
                    lastFeedbackTimestamp = latest.timestamp;
                    loadRecentFeedback();
                    loadFeedbackStats();
                    showLiveNotification(latest);
                }
            }
        })
        .catch(() => {});
}

function showLiveNotification(item) {
    const container = document.getElementById('feedback-notification');
    if (!container) return;

    const icon = FEEDBACK_ICONS[item.type] || FEEDBACK_ICONS.incident_report;
    const label = FEEDBACK_LABELS[item.type] || item.type;
    const sev = SEVERITY_COLORS[item.severity] || SEVERITY_COLORS[1];

    const notif = document.createElement('div');
    notif.className = 'fn-entry';
    notif.innerHTML = `
        <div class="fn-icon" style="color: ${sev.dot};">${icon}</div>
        <div class="fn-body">
            <div class="fn-header">
                <span class="fn-type">${label}</span>
                <span class="fn-zone">${item.zone_name || item.zone_id}</span>
            </div>
            <div class="fn-msg">${item.message}</div>
        </div>
    `;
    container.appendChild(notif);

    requestAnimationFrame(() => notif.classList.add('fn-visible'));

    setTimeout(() => {
        notif.classList.remove('fn-visible');
        setTimeout(() => notif.remove(), 300);
    }, 5000);
}

function simulateLiveNotification() {
    setTimeout(() => {
        const feed = document.getElementById('feedback-feed');
        const items = feed.querySelectorAll('.feedback-item');
        if (items.length > 0) {
            const firstItems = Array.from(items).slice(0, 2);
            firstItems.forEach(el => el.classList.add('fresh'));
        }
    }, 1000);
}

function openFeedbackModal() {
    const modal = document.getElementById('feedback-modal');
    modal.classList.add('visible');
    document.getElementById('feedback-submitted').style.display = 'none';
    document.getElementById('feedback-report-form').style.display = 'block';
    document.getElementById('feedback-report-form').reset();
    document.getElementById('feedback-submit-btn').querySelector('.btn-text').textContent = 'Submit Report';
    document.getElementById('feedback-submit-btn').classList.remove('loading');
    populateZoneDropdown();
}

function closeFeedbackModal() {
    document.getElementById('feedback-modal').classList.remove('visible');
}

function populateZoneDropdown() {
    if (typeof nodesData !== 'undefined' && nodesData.length) {
        const select = document.getElementById('feedback-zone');
        const currentVal = select.value;
        select.innerHTML = '<option value="">Select a zone...</option>';
        const seen = new Set();
        nodesData.forEach(node => {
            const zid = node.zone_id || node.id;
            if (seen.has(zid)) return;
            seen.add(zid);
            const opt = document.createElement('option');
            opt.value = zid;
            opt.textContent = `${node.name || zid} (${zid})`;
            select.appendChild(opt);
        });
        if (currentVal) select.value = currentVal;
    }
}

function submitFeedbackReport(e) {
    e.preventDefault();
    const btn = document.getElementById('feedback-submit-btn');
    btn.querySelector('.btn-text').textContent = 'Submitting...';
    btn.classList.add('loading');

    const zone_id = document.getElementById('feedback-zone').value;
    const type = document.getElementById('feedback-type').value;
    const message = document.getElementById('feedback-message').value.trim();
    const severity = parseInt(document.querySelector('input[name="severity"]:checked').value);

    fetch('/api/feedback/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, zone_id, message, severity }),
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('feedback-report-form').style.display = 'none';
                document.getElementById('feedback-submitted').style.display = 'block';

                loadRecentFeedback();
                loadFeedbackStats();

                showLiveNotification(data.feedback);

                setTimeout(closeFeedbackModal, 2500);
            } else {
                if (typeof showToast === 'function') showToast(data.error || 'Failed to submit report', 'error');
                btn.querySelector('.btn-text').textContent = 'Submit Report';
                btn.classList.remove('loading');
            }
        })
        .catch(() => {
            if (typeof showToast === 'function') showToast('Failed to submit. Please try again.', 'error');
            btn.querySelector('.btn-text').textContent = 'Submit Report';
            btn.classList.remove('loading');
        });
}

function getTimeAgo(timestamp) {
    if (!timestamp) return '';
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now - then;
    const diffMin = Math.floor(diffMs / 60000);

    if (diffMin < 1) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHrs = Math.floor(diffMin / 60);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    const diffDays = Math.floor(diffHrs / 24);
    return `${diffDays}d ago`;
}

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(initCommunityFeedback, 1500);
});
