const API_BASE = '';

// ─── Theme Toggle ───
function getTheme() {
    return localStorage.getItem('theme') || 'dark';
}

const ICON_SUN = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
const ICON_MOON = '<svg width="20" height="20" viewBox="0 0 24 24" fill="#000000"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.getElementById('themeIcon').innerHTML = theme === 'dark' ? ICON_SUN : ICON_MOON;
}

function toggleTheme() {
    const next = getTheme() === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', next);
    applyTheme(next);
}

applyTheme(getTheme());

// ─── Sidebar Toggle ───
function getSidebarState() {
    return localStorage.getItem('sidebar') || 'expanded';
}

function applySidebar(state) {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed', state === 'collapsed');
}

function toggleSidebar() {
    const next = getSidebarState() === 'expanded' ? 'collapsed' : 'expanded';
    localStorage.setItem('sidebar', next);
    applySidebar(next);
}

applySidebar(getSidebarState());

// ─── Tab Navigation ───
document.querySelectorAll('.nav-links li').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.nav-links li').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');

        if (tab.dataset.tab === 'accounts') loadAccounts();
        if (tab.dataset.tab === 'tokens') loadTokenStatus();
        if (tab.dataset.tab === 'history') loadOrderHistory();
        if (tab.dataset.tab === 'health') loadHealthCheck();
    });
});

// ─── Order Type Toggle ───
document.getElementById('orderType').addEventListener('change', function() {
    const lpGroup = document.getElementById('limitPriceGroup');
    const spRow = document.getElementById('stopPriceRow');
    const isSL = ['3','4'].includes(this.value);
    lpGroup.style.display = ['1','3'].includes(this.value) ? 'block' : 'none';
    spRow.style.display = isSL ? 'flex' : 'none';
});

// ─── Product Type Toggle (Quantity vs Lots) ───
function toggleQtyFields() {
    const productType = document.getElementById('productType').value;
    const isFO = productType === 'MARGIN';
    document.getElementById('qtyGroup').style.display = isFO ? 'none' : 'block';
    document.getElementById('lotsGroup').style.display = isFO ? 'block' : 'none';
    document.getElementById('lotSizeGroup').style.display = isFO ? 'block' : 'none';
    document.getElementById('positionTypeGroup').style.display = isFO ? 'block' : 'none';
}
document.getElementById('productType').addEventListener('change', toggleQtyFields);
toggleQtyFields();

// ─── API Helpers ───
async function api(path, method = 'GET', body = null) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${API_BASE}${path}`, opts);
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Request failed');
    }
    if (res.status === 204) return null;
    return res.json();
}

function logMessage(msg, type = 'info') {
    const log = document.getElementById('executionLog');
    const time = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    const typeClass = type === 'success' ? 'log-success' : type === 'error' ? 'log-error' : 'log-pending';
    entry.innerHTML = `<span class="log-time">${time}</span> <span class="${typeClass}">${msg}</span>`;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
}

function toast(message, type = 'info') {
    const el = document.createElement('div');
    el.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 999;
        padding: 12px 20px; border-radius: 8px; font-size: 14px; font-weight: 500;
        color: white; animation: slideIn 0.3s ease;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
    `;
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3000);
}

// ─── Account Checkboxes ───
async function loadAccountCheckboxes() {
    try {
        const accounts = await api('/api/v1/accounts');
        const group = document.getElementById('accountSelectGroup');
        const activeAccounts = accounts.filter(a => a.is_active);

        if (activeAccounts.length === 0) {
            group.innerHTML = '<div class="account-select-loading">No active accounts</div>';
            return;
        }

        group.innerHTML = activeAccounts.map(a => `
            <label class="account-checkbox">
                <input type="checkbox" value="${a.id}" checked>
                <span class="account-checkbox-label">${esc(a.name)}</span>
                <span class="account-checkbox-id">${esc(a.client_id)}</span>
            </label>
        `).join('');
    } catch {
        document.getElementById('accountSelectGroup').innerHTML =
            '<div class="account-select-loading">Failed to load accounts</div>';
    }
}

function getSelectedAccountIds() {
    const checked = document.querySelectorAll('#accountSelectGroup input[type="checkbox"]:checked');
    const ids = Array.from(checked).map(cb => cb.value);
    return ids.length > 0 ? ids : null;
}

// ─── Place Order ───
async function placeOrder(side) {
    const symbol = document.getElementById('symbol').value.trim();
    const productType = document.getElementById('productType').value;
    const isFO = productType === 'MARGIN';

    let qty;
    if (isFO) {
        const lots = parseInt(document.getElementById('lots').value);
        const lotSize = parseInt(document.getElementById('lotSize').value) || 1;
        if (!lots || lots <= 0) { toast('Enter valid lots', 'error'); return; }
        qty = lots * lotSize;
    } else {
        qty = parseInt(document.getElementById('qty').value);
        if (!qty || qty <= 0) { toast('Enter valid quantity', 'error'); return; }
    }

    const orderType = parseInt(document.getElementById('orderType').value);
    const limitPrice = parseFloat(document.getElementById('limitPrice').value) || 0;
    const stopPrice = parseFloat(document.getElementById('stopPrice').value) || 0;
    const validity = document.getElementById('validity').value;
    const accountIds = getSelectedAccountIds();

    if (!symbol) { toast('Enter a symbol', 'error'); return; }
    if (!accountIds) { toast('Select at least one account', 'error'); return; }

    const payload = { symbol, qty, order_type: orderType, side, product_type: productType, limit_price: limitPrice, stop_price: stopPrice, validity, account_ids: accountIds };

    const sideLabel = side === 1 ? 'BUY' : 'SELL';
    const posType = isFO ? ` (${document.getElementById('positionType').value === 'CARRY_FORWARD' ? 'Carry Forward' : 'Intraday'})` : '';
    logMessage(`Placing ${sideLabel} order: ${symbol} x ${qty}${posType}...`, 'pending');

    try {
        const resp = await api('/api/v1/orders/place', 'POST', payload);
        logMessage(`Batch ID: ${resp.batch_id}`, 'info');

        for (const r of resp.results) {
            const statusClass = r.status === 'SUCCESS' ? 'log-success' : 'log-error';
            logMessage(`[${r.account_name}] ${r.status}`, r.status === 'SUCCESS' ? 'success' : 'error');
            if (r.response) {
                logMessage(`  Response: ${JSON.stringify(r.response)}`, 'info');
            }
        }
        toast(`${sideLabel} order dispatched to ${resp.results.length} accounts`, 'success');
    } catch (err) {
        logMessage(`Order failed: ${err.message}`, 'error');
        toast(err.message, 'error');
    }
}

// ─── Accounts ───
async function loadAccounts() {
    try {
        const accounts = await api('/api/v1/accounts');
        const container = document.getElementById('accountsList');
        document.getElementById('activeAccountCount').textContent = `${accounts.length} Active Accounts`;

        if (accounts.length === 0) {
            container.innerHTML = '<div class="log-empty">No accounts configured. Click "+ Add Account" to start.</div>';
            return;
        }

        container.innerHTML = accounts.map(a => `
            <div class="account-card">
                <div class="account-card-header">
                    <h4>${esc(a.name)}</h4>
                    <span class="account-badge ${a.is_active ? 'badge-active' : 'badge-inactive'}">
                        ${a.is_active ? 'Active' : 'Inactive'}
                    </span>
                </div>
                <div class="account-card-detail"><span>Username</span><span>${esc(a.fyers_username)}</span></div>
                <div class="account-card-detail"><span>Client ID</span><span>${esc(a.client_id)}</span></div>
                <div class="account-card-detail"><span>Token</span><span>${a.has_token ? '✓ Present' : '✗ None'}</span></div>
                <div class="account-card-actions">
                    <button class="btn btn-sm btn-secondary" onclick="editAccount('${a.id}')">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteAccount('${a.id}')">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (err) {
        toast(err.message, 'error');
    }
}

function showAccountForm(account = null) {
    document.getElementById('accountFormModal').classList.remove('hidden');
    document.getElementById('accountFormTitle').textContent = account ? 'Edit Account' : 'Add Account';
    const sensitiveFields = ['accTotpKey', 'accPin', 'accSecretKey'];
    if (account) {
        document.getElementById('accountId').value = account.id;
        document.getElementById('accName').value = account.name;
        document.getElementById('accUsername').value = account.fyers_username;
        document.getElementById('accClientId').value = account.client_id;
        document.getElementById('accTotpKey').value = '';
        document.getElementById('accTotpKey').placeholder = 'Leave blank to keep existing';
        document.getElementById('accPin').value = '';
        document.getElementById('accPin').placeholder = 'Leave blank to keep existing';
        document.getElementById('accSecretKey').value = '';
        document.getElementById('accSecretKey').placeholder = 'Leave blank to keep existing';
        document.getElementById('accRedirectUri').value = account.redirect_uri || 'https://trade.fyers.in/api-login/redirect-uri/index.html';
        sensitiveFields.forEach(id => document.getElementById(id).removeAttribute('required'));
    } else {
        document.getElementById('accountForm').reset();
        document.getElementById('accountId').value = '';
        document.getElementById('accTotpKey').placeholder = '';
        document.getElementById('accPin').placeholder = '';
        document.getElementById('accSecretKey').placeholder = '';
        document.getElementById('accRedirectUri').value = 'https://trade.fyers.in/api-login/redirect-uri/index.html';
        sensitiveFields.forEach(id => document.getElementById(id).setAttribute('required', ''));
    }
}

function hideAccountForm() {
    document.getElementById('accountFormModal').classList.add('hidden');
}

async function submitAccount(e) {
    e.preventDefault();
    const id = document.getElementById('accountId').value;
    const data = {
        name: document.getElementById('accName').value,
        fyers_username: document.getElementById('accUsername').value,
        client_id: document.getElementById('accClientId').value,
        secret_key: document.getElementById('accSecretKey').value,
        totp_key: document.getElementById('accTotpKey').value,
        pin: document.getElementById('accPin').value,
        redirect_uri: document.getElementById('accRedirectUri').value,
    };

    try {
        if (id) {
            // For edit: only send non-empty fields
            const updateData = {};
            for (const [k, v] of Object.entries(data)) {
                if (v) updateData[k] = v;
            }
            await api(`/api/v1/accounts/${id}`, 'PUT', updateData);
            toast('Account updated', 'success');
        } else {
            await api('/api/v1/accounts', 'POST', data);
            toast('Account added', 'success');
        }
        hideAccountForm();
        loadAccounts();
        loadAccountCheckboxes();
    } catch (err) {
        toast(err.message, 'error');
    }
}

async function editAccount(id) {
    try {
        const accounts = await api('/api/v1/accounts');
        const acc = accounts.find(a => a.id === id);
        if (acc) {
            // Fetch full details
            const full = await api(`/api/v1/accounts/${id}`);
            showAccountForm(full);
        }
    } catch (err) {
        toast(err.message, 'error');
    }
}

async function deleteAccount(id) {
    if (!confirm('Delete this account?')) return;
    try {
        await api(`/api/v1/accounts/${id}`, 'DELETE');
        toast('Account deleted', 'success');
        loadAccounts();
        loadAccountCheckboxes();
    } catch (err) {
        toast(err.message, 'error');
    }
}

// ─── Tokens ───
async function loadTokenStatus() {
    try {
        const statuses = await api('/api/v1/tokens/status');
        const container = document.getElementById('tokenStatusList');
        let validCount = 0;

        container.innerHTML = statuses.map(s => {
            const isValid = s.has_token && s.is_valid;
            if (isValid) validCount++;
            const expiryStr = s.token_expiry ? new Date(s.token_expiry).toLocaleString() : 'N/A';
            return `
                <div class="token-card">
                    <div class="token-card-header">
                        <strong>${esc(s.account_name)}</strong>
                        <span>
                            <span class="token-status-dot" style="background: ${isValid ? '#10b981' : '#ef4444'}"></span>
                            ${isValid ? 'Valid' : 'Invalid / Expired'}
                        </span>
                    </div>
                    <div class="token-card-detail">Has Token: ${s.has_token ? 'Yes' : 'No'}</div>
                    <div class="token-card-detail">Expires: ${expiryStr}</div>
                </div>
            `;
        }).join('');

        document.getElementById('validTokenCount').textContent = `${validCount} Valid Tokens`;
        loadSchedulerStatus();
    } catch (err) {
        toast(err.message, 'error');
    }
}

async function generateAllTokens() {
    const btn = event.target;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Generating...';

    try {
        const resp = await api('/api/v1/tokens/generate', 'POST', {});
        let successCount = 0;
        for (const r of resp.results) {
            if (r.success) successCount++;
        }
        toast(`Tokens generated: ${successCount}/${resp.results.length} succeeded`, successCount === resp.results.length ? 'success' : 'error');
        loadTokenStatus();
    } catch (err) {
        toast(err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Generate All Tokens';
    }
}

async function refreshExpiringTokens() {
    const btn = event.target;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Refreshing...';

    try {
        const resp = await api('/api/v1/tokens/refresh', 'POST');
        if (resp.results.length === 0) {
            toast('All tokens are valid, no refresh needed', 'success');
        } else {
            let successCount = resp.results.filter(r => r.success).length;
            toast(`Refreshed: ${successCount}/${resp.results.length} succeeded`, successCount === resp.results.length ? 'success' : 'error');
        }
        loadTokenStatus();
    } catch (err) {
        toast(err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Refresh Expiring';
    }
}

async function loadSchedulerStatus() {
    try {
        const status = await api('/api/v1/tokens/scheduler');
        const el = document.getElementById('schedulerStatus');
        const accountsNeedingRefresh = status.accounts.filter(a => a.needs_refresh).length;
        el.innerHTML = `
            <div class="scheduler-info-box">
                <span>Auto-check every ${status.check_interval_minutes} min</span>
                <span>Refresh ${status.refresh_before_expiry_hours}h before expiry</span>
                <span>${accountsNeedingRefresh} account(s) need refresh</span>
            </div>
        `;
    } catch (err) {
        // silently fail
    }
}

// ─── Order History ───
async function loadOrderHistory() {
    try {
        const orders = await api('/api/v1/orders/history?limit=100');
        const tbody = document.getElementById('orderHistoryBody');

        if (orders.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:40px">No orders yet</td></tr>';
            return;
        }

        tbody.innerHTML = orders.map(o => {
            const time = new Date(o.created_at).toLocaleString();
            const sideLabel = o.side === 1 ? 'BUY' : 'SELL';
            const sideClass = o.side === 1 ? 'side-buy' : 'side-sell';
            const typeLabel = {1:'Limit', 2:'Market', 3:'SL-Limit', 4:'SL-Market'}[o.order_type] || o.order_type;
            return `
                <tr>
                    <td>${time}</td>
                    <td>${esc(o.account_name)}</td>
                    <td>${esc(o.symbol)}</td>
                    <td><span class="${sideClass}">${sideLabel}</span></td>
                    <td>${o.qty}</td>
                    <td>${typeLabel}</td>
                    <td>${o.product_type}</td>
                    <td><span class="status-badge status-${o.status}">${o.status}</span></td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        toast(err.message, 'error');
    }
}

async function loadHealthCheck() {
    try {
        const [health, tokenStatus] = await Promise.all([
            api('/health'),
            api('/api/v1/tokens/status')
        ]);
        const container = document.getElementById('healthStatus');

        const statusClass = health.status === 'healthy' ? 'health-ok' : health.status === 'degraded' ? 'health-warn' : 'health-error';

        let html = `
            <div class="health-card ${statusClass}">
                <div class="health-card-header">
                    <strong>Overall Status</strong>
                    <span class="health-badge ${statusClass}">${health.status.toUpperCase()}</span>
                </div>
                <div class="health-card-detail">Version: ${health.version}</div>
                <div class="health-card-detail">Timestamp: ${new Date(health.timestamp).toLocaleString()}</div>
            </div>
        `;

        for (const [name, check] of Object.entries(health.checks)) {
            const checkClass = check.status === 'ok' ? 'health-ok' : 'health-error';
            let details = '';
            if (name === 'database') {
                details = check.status === 'ok' ? 'Connection OK' : check.detail;
            } else if (name === 'scheduler') {
                details = `Check every ${check.check_interval_minutes} min`;
            } else if (name === 'accounts') {
                details = `${check.active} active / ${check.total} total`;
            }
            html += `
                <div class="health-card ${checkClass}">
                    <div class="health-card-header">
                        <strong>${name.charAt(0).toUpperCase() + name.slice(1)}</strong>
                        <span class="health-badge ${checkClass}">${check.status.toUpperCase()}</span>
                    </div>
                    <div class="health-card-detail">${details}</div>
                </div>
            `;
        }

        if (tokenStatus && Array.isArray(tokenStatus) && tokenStatus.length > 0) {
            const valid = tokenStatus.filter(a => a.is_valid).length;
            const total = tokenStatus.length;
            const tokenClass = valid === total ? 'health-ok' : valid > 0 ? 'health-warn' : 'health-error';
            let tokenDetails = tokenStatus.map(a => {
                const icon = a.is_valid ? '&#10003;' : '&#10007;';
                const cls = a.is_valid ? 'health-ok' : 'health-error';
                return `<span class="health-badge ${cls}" style="font-size:12px;margin:2px;">${icon} ${a.account_name}</span>`;
            }).join(' ');
            html += `
                <div class="health-card ${tokenClass}">
                    <div class="health-card-header">
                        <strong>Token Status</strong>
                        <span class="health-badge ${tokenClass}">${valid}/${total} VALID</span>
                    </div>
                    <div class="health-card-detail">${tokenDetails}</div>
                </div>
            `;
        }

        container.innerHTML = html;
    } catch (err) {
        toast(err.message, 'error');
    }
}

// ─── Layout Controls ───
function setLayout(ratio) {
    const orderCard = document.getElementById('orderFormCard');
    const logCard = document.getElementById('executionLogCard');
    const [orderFlex, logFlex] = ratio.split('-');
    orderCard.style.flex = orderFlex;
    logCard.style.flex = logFlex;
    
    document.querySelectorAll('.layout-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    localStorage.setItem('terminal-layout', ratio);
}

// Restore saved layout
function restoreLayout() {
    const saved = localStorage.getItem('terminal-layout') || '50-50';
    const orderCard = document.getElementById('orderFormCard');
    const logCard = document.getElementById('executionLogCard');
    if (orderCard && logCard) {
        const [orderFlex, logFlex] = saved.split('-');
        orderCard.style.flex = orderFlex;
        logCard.style.flex = logFlex;
    }
}

// ─── Resizable Divider ───
function initResizeDivider() {
    const divider = document.getElementById('resizeDivider');
    const orderCard = document.getElementById('orderFormCard');
    const logCard = document.getElementById('executionLogCard');
    const layout = document.getElementById('terminalLayout');
    
    if (!divider || !orderCard || !logCard || !layout) return;
    
    let isResizing = false;
    
    divider.addEventListener('mousedown', (e) => {
        isResizing = true;
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        
        const layoutRect = layout.getBoundingClientRect();
        const offsetX = e.clientX - layoutRect.left;
        const totalWidth = layoutRect.width;
        
        let orderPercent = (offsetX / totalWidth) * 100;
        orderPercent = Math.max(20, Math.min(80, orderPercent));
        
        const logPercent = 100 - orderPercent;
        
        orderCard.style.flex = Math.round(orderPercent);
        logCard.style.flex = Math.round(logPercent);
    });
    
    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        }
    });
}

// ─── Utility ───
function esc(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

// ─── Init ───
async function init() {
    restoreLayout();
    initResizeDivider();
    try {
        await api('/api/v1/accounts');
        document.getElementById('connectionStatus').className = 'status-dot green';
    } catch {
        document.getElementById('connectionStatus').className = 'status-dot red';
    }
    loadAccounts();
    loadAccountCheckboxes();
    loadTokenStatus();
}

init();
