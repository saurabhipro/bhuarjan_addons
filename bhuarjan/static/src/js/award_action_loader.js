/** @odoo-module **/

/**
 * Award Action Loader
 * Shows a full-screen loading overlay when heavy award actions (generate / download)
 * are triggered from any Odoo form view button.
 */

const LOADER_ID = 'bhu_award_action_loader';

// Button method names that warrant a loading overlay.
// NOTE: 'action_download_award' is intentionally EXCLUDED because it opens
// a wizard popup — showing a loader would cover the dialog.
// The loader is only for actions that do heavy server-side work (PDF/Excel generation).
const HEAVY_ACTIONS = new Set([
    'action_generate_award',
    // 'action_download_award' — opens a wizard, NOT a heavy action (wizard covers loader)
    'action_download',          // inside the download wizard — actual PDF/Excel generation
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
    'action_download':                  'Generating &amp; downloading your document…<br><small>Building PDF / Excel. This may take a moment.</small>',
    'action_download_excel_components': 'Generating Excel report…<br><small>Building Excel workbook from survey data.</small>',
    'apply_generate_from_download_wizard': 'Generating &amp; downloading Award…<br><small>Building the document. Download will start automatically.</small>',
    'action_generate_award_notification': 'Generating notification document…',
    'action_download_award_notification': 'Preparing notification for download…',
    'action_download_consolidated_excel': 'Generating Consolidated Excel…',
    'action_consolidated_report':        'Generating Consolidated PDF report…',
};

function _isSection23Context() {
    const hash = (window.location.hash || '').toLowerCase();
    if (hash.includes('bhu.section23.award') || hash.includes('section23')) {
        return true;
    }
    const cp = document.querySelector('.o_control_panel_breadcrumbs, .o_breadcrumb, .breadcrumb');
    const txt = ((cp && cp.textContent) || '').toLowerCase();
    return txt.includes('section 23 award') || txt.includes('धारा 23');
}

function _isCreateButton(btn) {
    if (!btn) return false;
    return (
        btn.classList.contains('o_list_button_add') ||
        btn.classList.contains('o-kanban-button-new') ||
        btn.classList.contains('o_form_button_create')
    );
}

function _isSection23Hash(hashValue) {
    const hash = (hashValue || '').toLowerCase();
    return hash.includes('model=bhu.section23.award') || hash.includes('section23');
}

function _isAwardMenuTarget(node) {
    const target = node && node.closest('a, button, [role="menuitem"]');
    if (!target) return false;
    const haystack = [
        target.getAttribute('data-menu-xmlid') || '',
        target.getAttribute('data-action-xmlid') || '',
        target.getAttribute('data-action-id') || '',
        target.getAttribute('name') || '',
        target.getAttribute('href') || '',
        target.getAttribute('title') || '',
        target.textContent || '',
    ].join(' ').toLowerCase();
    return (
        haystack.includes('menu_sec23_award') ||
        haystack.includes('menu_payment_view_awards') ||
        haystack.includes('action_section23_award') ||
        haystack.includes('bhu.section23.award') ||
        haystack.includes('section 23 awards') ||
        haystack.includes('section 23 award') ||
        haystack.includes('view awards')
    );
}

function _showSection23OpenLoader() {
    _showLoader('Opening Section 23 Award…<br><small>Loading award data. Please wait.</small>');

    const startedAt = Date.now();
    const MAX_WAIT = 25000;
    const MIN_VISIBLE_MS = 550;
    let done = false;
    let pollTimer = null;
    let observer = null;

    const isViewReady = () => {
        if (!_isSection23Context() && !_isSection23Hash(window.location.hash)) return false;
        const hasList = !!document.querySelector('.o_content .o_list_view .o_list_table');
        const hasForm = !!document.querySelector('.o_content .o_form_view .o_form_sheet');
        const hasBreadcrumb = !!document.querySelector(
            '.o_control_panel_breadcrumbs, .o_breadcrumb, .breadcrumb'
        );
        return hasList || hasForm || hasBreadcrumb;
    };

    const finish = () => {
        if (done) return;
        done = true;
        if (observer) observer.disconnect();
        if (pollTimer) clearInterval(pollTimer);
        const elapsed = Date.now() - startedAt;
        const waitMore = Math.max(0, MIN_VISIBLE_MS - elapsed);
        setTimeout(_hideLoader, waitMore);
    };

    if (isViewReady()) {
        finish();
        return;
    }

    pollTimer = setInterval(() => {
        if (isViewReady() || (Date.now() - startedAt) > MAX_WAIT) {
            finish();
        }
    }, 220);

    observer = new MutationObserver(() => {
        if (isViewReady()) {
            finish();
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
}

// Show loader when user opens the Section 23 Award action from menu.
document.addEventListener('click', (e) => {
    if (!_isAwardMenuTarget(e.target)) return;
    if (_isSection23Context()) return;
    _showSection23OpenLoader();
}, true);

// Also catch hash-based navigation into Section 23 (dashboard shortcuts etc.).
let _lastHash = window.location.hash;
window.addEventListener('hashchange', () => {
    const previous = (_lastHash || '').toLowerCase();
    const current = (window.location.hash || '').toLowerCase();
    _lastHash = window.location.hash;
    if (_isSection23Hash(current) && !_isSection23Hash(previous)) {
        _showSection23OpenLoader();
    } else if (_isSection23Hash(current) && !document.getElementById(LOADER_ID)) {
        // Fallback for SPA transitions where previous/current hash values are noisy.
        _showSection23OpenLoader();
    }
});

// Attach click listener using event delegation on document body
document.addEventListener('click', (e) => {
    // Walk up the DOM to find the actual <button> element
    let btn = e.target;
    while (btn && btn.tagName !== 'BUTTON') {
        btn = btn.parentElement;
    }
    if (!btn) return;

    const name = btn.getAttribute('name') || btn.dataset.name || '';
    const isHeavy = HEAVY_ACTIONS.has(name);
    const isCreateInS23 = _isCreateButton(btn) && _isSection23Context();
    if (!isHeavy && !isCreateInS23) return;

    // Don't show if button is disabled
    if (btn.disabled) return;

    const label = isCreateInS23
        ? 'Opening Section 23 Award form…<br><small>Preparing the next screen.</small>'
        : (ACTION_LABELS[name] || 'Processing your request…');

    // Check if button is inside a dialog/wizard
    const dialog = btn.closest('.o_dialog, .modal, [role="dialog"]');

    _showLoader(label);

    // Safety-net timeouts (generous to cover slow PDF generation)
    const MAX_WAIT = 120000; // 2 minutes hard max
    const safetyTimer = setTimeout(_hideLoader, MAX_WAIT);

    function done() {
        clearTimeout(safetyTimer);
        dialogObs && dialogObs.disconnect();
        notifObs && notifObs.disconnect();
        setTimeout(_hideLoader, 500);
    }

    // 1. If button was in a wizard dialog: hide loader when dialog is removed from DOM
    let dialogObs = null;
    if (dialog) {
        dialogObs = new MutationObserver(() => {
            // Dialog closed (removed from DOM or hidden)
            if (!document.body.contains(dialog) ||
                dialog.style.display === 'none' ||
                !dialog.offsetParent) {
                done();
            }
        });
        dialogObs.observe(document.body, { childList: true, subtree: true });
    }

    // 2. Hide loader when Odoo shows a notification (success OR error)
    let notifObs = new MutationObserver(() => {
        const notif = document.querySelector('.o_notification_manager .o_notification');
        if (notif) { done(); }
    });
    notifObs.observe(document.body, { childList: true, subtree: true });

    // 3. Hide when page regains focus after a file download (browser focus returns)
    const onFocus = () => { done(); };
    window.addEventListener('focus', onFocus, { once: true });

    // 4. For non-dialog buttons: also watch for form re-render (breadcrumb change)
    if (!dialog) {
        const breadcrumb = document.querySelector('.o_breadcrumb, .breadcrumb');
        if (breadcrumb) {
            const bcObs = new MutationObserver(() => {
                bcObs.disconnect();
                done();
            });
            bcObs.observe(breadcrumb, { childList: true, subtree: true });
        }
    }
}, true); // capture phase
