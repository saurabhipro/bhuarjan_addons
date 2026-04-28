/** @odoo-module **/

/**
 * Award Action Loader
 * Shows a full-screen loading overlay when heavy award actions (generate / download)
 * are triggered from any Odoo form view button.
 */

const LOADER_ID = 'bhu_award_action_loader';

// Button method names that warrant a loading overlay
const HEAVY_ACTIONS = new Set([
    'action_generate_award',
    'action_download_award',
    'action_download_excel_components',
    'apply_generate_from_download_wizard',
    'action_generate_award_notification',
    'action_download_award_notification',
    'action_download_consolidated_excel',
    'action_consolidated_report',
]);

function _showLoader(label) {
    if (document.getElementById(LOADER_ID)) return;
    const el = document.createElement('div');
    el.id = LOADER_ID;
    el.style.cssText = [
        'position:fixed!important', 'inset:0!important', 'z-index:999999!important',
        'display:flex!important', 'align-items:center!important',
        'justify-content:center!important', 'flex-direction:column!important',
        'background:linear-gradient(135deg,#3b1a0e 0%,#6b2f0f 40%,#8B4513 70%,#c47c3e 100%)!important',
    ].join(';');

    el.innerHTML = `
        <style>
            #${LOADER_ID} .aal-ring {
                width: 96px; height: 96px; border-radius: 50%;
                background: rgba(255,255,255,0.15);
                border: 3px solid rgba(255,255,255,0.4);
                display: flex; align-items: center; justify-content: center;
                margin-bottom: 18px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.25);
                overflow: hidden; padding: 6px;
            }
            #${LOADER_ID} .aal-ring img { width:100%; height:100%; object-fit:contain; border-radius:50%; }
            #${LOADER_ID} .aal-spinner {
                width: 64px; height: 64px;
                border: 5px solid rgba(255,255,255,0.15);
                border-top-color: #ffd88a; border-radius: 50%;
                animation: aal-spin 0.85s linear infinite; margin-bottom: 26px;
            }
            #${LOADER_ID} .aal-title {
                color:#fff; font-size:1.5rem; font-weight:700;
                margin:0 0 6px 0; font-family:inherit; text-align:center;
            }
            #${LOADER_ID} .aal-sub {
                color:rgba(255,255,255,0.75); font-size:0.95rem;
                margin:0 0 26px 0; font-style:italic; font-family:inherit; text-align:center;
                max-width: 360px; line-height: 1.5;
            }
            #${LOADER_ID} .aal-dots { display:flex; gap:9px; margin-bottom:30px; }
            #${LOADER_ID} .aal-dots span {
                width:10px; height:10px; border-radius:50%;
                background:#ffd88a; animation:aal-bounce 1.2s ease-in-out infinite;
            }
            #${LOADER_ID} .aal-dots span:nth-child(2){animation-delay:0.18s;}
            #${LOADER_ID} .aal-dots span:nth-child(3){animation-delay:0.36s;}
            #${LOADER_ID} .aal-dots span:nth-child(4){animation-delay:0.54s;}
            #${LOADER_ID} .aal-dots span:nth-child(5){animation-delay:0.72s;}
            #${LOADER_ID} .aal-brand {
                color:rgba(255,255,255,0.35); font-size:0.75rem;
                letter-spacing:1.2px; text-transform:uppercase; font-family:inherit;
            }
            @keyframes aal-spin  { to { transform: rotate(360deg); } }
            @keyframes aal-bounce {
                0%,80%,100% { transform:scale(0.55); opacity:0.4; }
                40%         { transform:scale(1.2);  opacity:1;   }
            }
        </style>
        <div class="aal-ring"><img src="/bhuarjan/static/img/icon.png" alt="Bhuarjan"/></div>
        <div class="aal-spinner"></div>
        <div class="aal-title">Please wait…</div>
        <div class="aal-sub">${label || 'Processing your request. This may take a few moments.'}</div>
        <div class="aal-dots"><span></span><span></span><span></span><span></span><span></span></div>
        <div class="aal-brand">Bhuarjan · Land Acquisition System</div>
    `;
    document.body.appendChild(el);
}

function _hideLoader() {
    const el = document.getElementById(LOADER_ID);
    if (!el) return;
    el.style.transition = 'opacity 0.35s ease';
    el.style.opacity = '0';
    setTimeout(() => el && el.remove(), 380);
}

// Label map for each action
const ACTION_LABELS = {
    'action_generate_award':            'Generating the Section 23 Award document…<br><small>Building PDF from survey data. Please do not close this page.</small>',
    'action_download_award':            'Preparing Award for download…<br><small>Compiling the award document.</small>',
    'action_download_excel_components': 'Generating Excel report…<br><small>Building Excel workbook from survey data.</small>',
    'apply_generate_from_download_wizard': 'Generating &amp; downloading Award…<br><small>Building the document. Download will start automatically.</small>',
    'action_generate_award_notification': 'Generating notification document…',
    'action_download_award_notification': 'Preparing notification for download…',
    'action_download_consolidated_excel': 'Generating Consolidated Excel…',
    'action_consolidated_report':        'Generating Consolidated PDF report…',
};

// Attach click listener using event delegation on document body
document.addEventListener('click', (e) => {
    // Odoo renders form buttons as <button> elements with a `name` attribute
    // Walk up the DOM to find the button element (click may be on child icon/span)
    let btn = e.target;
    while (btn && btn.tagName !== 'BUTTON') {
        btn = btn.parentElement;
    }
    if (!btn) return;

    const name = btn.getAttribute('name') || btn.dataset.name || '';
    if (!HEAVY_ACTIONS.has(name)) return;

    // Don't show if button is disabled or invisible
    if (btn.disabled || btn.closest('[style*="display: none"]') || btn.closest('[style*="display:none"]')) return;

    const label = ACTION_LABELS[name] || 'Processing your request…';
    _showLoader(label);

    // Auto-hide safety net: remove loader after 3 minutes max
    // (the page typically reloads or redirects before this)
    const timeout = setTimeout(_hideLoader, 180000);

    // Hide loader if page navigates away (file download triggers this)
    const onVisibility = () => {
        if (document.visibilityState === 'visible') {
            clearTimeout(timeout);
            setTimeout(_hideLoader, 800);
        }
    };
    document.addEventListener('visibilitychange', onVisibility, { once: true });

    // Also hide if Odoo triggers a "notification" (success/error) — means action completed
    const origNotif = window.__bhu_orig_notif;
    if (!origNotif) {
        // Patch owl env notification service after action completes via MutationObserver
        const obs = new MutationObserver(() => {
            const notif = document.querySelector('.o_notification_manager .o_notification');
            if (notif) {
                obs.disconnect();
                clearTimeout(timeout);
                setTimeout(_hideLoader, 600);
            }
        });
        obs.observe(document.body, { childList: true, subtree: true });
        // Fallback: also watch for the form's "save" indicator disappearing
        setTimeout(() => { obs.disconnect(); clearTimeout(timeout); _hideLoader(); }, 180000);
    }
}, true); // capture phase so we get it before Odoo's handler
