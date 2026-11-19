const token = localStorage.getItem('ai_token');
if (!token) location.href = '/';

async function api(path, options = {}) {
  const headers = { Authorization: 'Bearer ' + token, ...(options.headers || {}) };
  if (options.body) headers['Content-Type'] = 'application/json';
  const res = await fetch(path, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 || res.status === 403) location.href = '/';
    throw new Error(data.detail || 'Hata ' + res.status);
  }
  return data;
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : String(s);
  return d.innerHTML;
}

function time(ts) {
  return new Date(ts * 1000).toLocaleString('tr-TR');
}

async function loadAll() {
  try {
    const [stats, users] = await Promise.all([api('/api/admin/stats'), api('/api/admin/users')]);

    const labels = {
      users: 'Kullanıcı', conversations: 'Sohbet', messages: 'Mesaj', files: 'Dosya',
      requests: 'AI isteği', tool_calls: 'Araç çağrısı', active_users_24h: 'Aktif kullanıcı (24s)'
    };
    document.getElementById('cards').innerHTML = Object.keys(labels).map(k =>
      `<div class="card"><div class="n">${stats[k] ?? 0}</div><div class="l">${labels[k]}</div></div>`
    ).join('');

    document.getElementById('usersBody').innerHTML = users.map(u => `
      <tr>
        <td>${u.id}</td>
        <td>${esc(u.username)}</td>
        <td>${esc(u.email || '—')} ${u.email ? (u.email_verified ? '<span class="badge ok">onaylı</span>' : '<span class="badge">bekliyor</span>') : ''}</td>
        <td><span class="badge ${u.role === 'admin' ? 'admin' : ''}">${esc(u.role)}</span></td>
        <td>${u.is_active ? '✅' : '❌'}</td>
        <td>${time(u.created_at)}</td>
        <td>
          <select onchange="setRole(${u.id}, this.value)">
            <option value="user" ${u.role === 'user' ? 'selected' : ''}>user</option>
            <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>admin</option>
          </select>
          <button onclick="toggleActive(${u.id}, ${u.is_active ? 0 : 1})" class="link-btn">${u.is_active ? 'Pasifleştir' : 'Aktifleştir'}</button>
        </td>
      </tr>`).join('');

    document.getElementById('logsBody').innerHTML = (stats.recent || []).map(l => `
      <tr><td>${esc(l.username || 'sistem')}</td><td>${esc(l.action)}</td><td>${esc(l.detail)}</td><td>${time(l.created_at)}</td></tr>
    `).join('');
  } catch (e) { alert(e.message); }
}

async function setRole(id, role) {
  await api(`/api/admin/users/${id}/role`, { method: 'POST', body: JSON.stringify({ role }) });
  loadAll();
}

async function toggleActive(id, active) {
  await api(`/api/admin/users/${id}/active?active=${!!active}`, { method: 'POST' });
  loadAll();
}

// ---------- açık / koyu tema ----------
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem('ai_theme', theme); } catch {}
  document.querySelectorAll('.theme-toggle').forEach((btn) => {
    btn.title = theme === 'dark' ? 'Açık temaya geç' : 'Koyu temaya geç';
  });
}

let savedTheme = null;
try { savedTheme = localStorage.getItem('ai_theme'); } catch {}
applyTheme(
  savedTheme || (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
);
document.querySelectorAll('.theme-toggle').forEach((btn) => {
  btn.onclick = () => applyTheme(
    document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'
  );
});

loadAll();
setInterval(loadAll, 30000);
