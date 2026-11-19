const $ = (id) => document.getElementById(id);

const state = {
  token: localStorage.getItem('ai_token') || null,
  user: null,
  convId: null,
  conversations: [],
  files: [],
  busy: false,
  recognition: null,
  speaking: false,
};

const TOOL_NAMES = {
  web_search: 'web araması',
  calculator: 'hesaplama',
  weather: 'hava durumu',
};

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (state.token) headers['Authorization'] = 'Bearer ' + state.token;
  if (options.body && !(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';
  const res = await fetch(path, { ...options, headers });
  if (res.status === 401) {
    logoutLocal();
    throw new Error('Oturum süresi doldu, tekrar giriş yapın.');
  }
  let data;
  try { data = await res.json(); } catch { data = {}; }
  if (!res.ok) {
    const detail = data.detail;
    if (detail && typeof detail === 'object') {
      const err = new Error(detail.message || `Hata ${res.status}`);
      Object.assign(err, detail);
      throw err;
    }
    throw new Error(detail || `Hata ${res.status}`);
  }
  return data;
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : String(s);
  return d.innerHTML;
}

function initials(name) {
  return (name || '?').trim().slice(0, 2).toUpperCase();
}

function greeting() {
  const h = new Date().getHours();
  if (h < 6) return 'Gece yarısı';
  if (h < 11) return 'Günaydın';
  if (h < 18) return 'İyi günler';
  return 'İyi akşamlar';
}

function logoutLocal() {
  state.token = null;
  state.user = null;
  localStorage.removeItem('ai_token');
  $('app').classList.add('hidden');
  $('loginScreen').classList.remove('hidden');
}

async function init() {
  if (!state.token) return;
  try {
    state.user = await api('/api/me');
    showApp();
  } catch { logoutLocal(); }
}

function showApp() {
  $('loginScreen').classList.add('hidden');
  $('app').classList.remove('hidden');
  $('userName').textContent = state.user.username;
  $('userRole').textContent = state.user.role === 'admin' ? 'yönetici' : 'kullanıcı';
  $('userAvatar').textContent = initials(state.user.username);
  $('greeting').textContent = greeting() + ', ' + state.user.username;
  $('adminLink').classList.toggle('hidden', state.user.role !== 'admin');
  loadConversations();
  loadFiles();
  checkHealth();
}

async function checkHealth() {
  try {
    const h = await api('/api/health');
    const ok = h.ollama && h.ollama.online;
    $('status').textContent = ok ? h.model + ' hazır' : 'motor bağlı değil';
    $('statusDot').className = 'status-dot ' + (ok ? 'online' : 'offline');
  } catch (e) {
    $('status').textContent = 'sunucuya ulaşılamıyor';
    $('statusDot').className = 'status-dot offline';
  }
}

async function loadConversations() {
  state.conversations = await api('/api/conversations');
  const box = $('convList');
  $('convCount').textContent = state.conversations.length;
  box.innerHTML = '';
  if (!state.conversations.length) {
    box.innerHTML = '<div class="empty">Henüz sohbet yok. Yeni sohbet ile başlayabilirsin.</div>';
    return;
  }
  for (const c of state.conversations) {
    const el = document.createElement('div');
    el.className = 'conv-item' + (c.id === state.convId ? ' active' : '');
    el.innerHTML = `<span class="dot"></span><span class="conv-title" title="${esc(c.title)}">${esc(c.title)}</span><button class="del" title="Sohbeti sil">×</button>`;
    el.addEventListener('click', (e) => {
      if (e.target.classList.contains('del')) {
        e.stopPropagation();
        removeConversation(c.id);
      } else {
        openConversation(c.id);
      }
    });
    box.appendChild(el);
  }
}

async function openConversation(id) {
  state.convId = id;
  const c = state.conversations.find((x) => x.id === id);
  $('pageTitle').textContent = c ? c.title : 'Sohbet';
  const msgs = await api(`/api/conversations/${id}/messages`);
  $('messages').innerHTML = '';
  for (const m of msgs) addMessageToUI(m.role, m.content);
  loadConversations();
  if (window.innerWidth < 720) document.querySelector('.sidebar').classList.remove('open');
}

async function removeConversation(id) {
  if (!confirm('Bu sohbet silinsin mi?')) return;
  await api('/api/conversations/' + id, { method: 'DELETE' });
  if (state.convId === id) {
    state.convId = null;
    $('pageTitle').textContent = 'Yeni sohbet';
    $('messages').innerHTML = '';
  }
  loadConversations();
}

async function loadFiles() {
  state.files = await api('/api/files');
  const box = $('fileList');
  $('fileCount').textContent = state.files.length;
  box.innerHTML = '';
  if (!state.files.length) {
    box.innerHTML = '<div class="empty">Burada henüz dosya yok.</div>';
    return;
  }
  for (const f of state.files) {
    const el = document.createElement('div');
    el.className = 'file-item';
    el.innerHTML = `<span class="file-glyph"></span><span class="file-name" title="${esc(f.filename)}">${esc(f.filename.slice(0, 24))}</span><button class="del" title="Dosyayı kaldır">×</button>`;
    el.querySelector('.del').onclick = async () => {
      await api('/api/files/' + f.id, { method: 'DELETE' });
      loadFiles();
    };
    box.appendChild(el);
  }
}

function addMessageToUI(role, content, tool, thinking = false) {
  const wrap = document.querySelector('.welcome');
  if (wrap) wrap.remove();
  const row = document.createElement('div');
  row.className = 'msg-row ' + (role === 'user' ? 'user' : 'assistant');
  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user'
    ? initials(state.user ? state.user.username : 'Sen')
    : 'R';
  const bubble = document.createElement('div');
  bubble.className = 'bubble' + (thinking ? ' thinking' : '');
  bubble.textContent = content;
  if (tool) {
    const tag = document.createElement('div');
    tag.className = 'tool-tag';
    tag.textContent = (TOOL_NAMES[tool.tool] || tool.tool) + ' kullanıldı';
    bubble.appendChild(tag);
  }
  row.append(avatar, bubble);
  $('messages').appendChild(row);
  $('messages').scrollTop = $('messages').scrollHeight;
  return bubble;
}

async function sendMessage() {
  const text = $('prompt').value.trim();
  if (!text || state.busy) return;
  $('prompt').value = '';
  state.busy = true;
  $('sendBtn').disabled = true;
  addMessageToUI('user', text);
  if (!state.convId) $('pageTitle').textContent = text.slice(0, 42);
  const thinking = addMessageToUI('assistant', 'Düşünüyor', null, true);

  try {
    const data = await api('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        message: text,
        conversation_id: state.convId,
        use_tools: $('toolToggle').checked,
        use_files: $('fileToggle').checked,
      }),
    });
    state.convId = data.conversation_id;
    thinking.classList.remove('thinking');
    thinking.textContent = data.answer;
    if (data.tool) {
      const tag = document.createElement('div');
      tag.className = 'tool-tag';
      tag.textContent = (TOOL_NAMES[data.tool.tool] || data.tool.tool) + ' kullanıldı';
      thinking.appendChild(tag);
    }
    if ($('voiceToggle').checked && window.speechSynthesis) {
      const u = new SpeechSynthesisUtterance(data.answer.slice(0, 600));
      u.lang = 'tr-TR';
      u.rate = 1;
      window.speechSynthesis.speak(u);
    }
    loadConversations();
    checkHealth();
  } catch (e) {
    thinking.classList.remove('thinking');
    thinking.textContent = e.message;
  } finally {
    state.busy = false;
    $('sendBtn').disabled = false;
    $('prompt').focus();
  }
}

// ---------- sesli giriş ----------
function setupVoice() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { $('micBtn').disabled = true; return; }
  state.recognition = new SR();
  state.recognition.lang = 'tr-TR';
  state.recognition.interimResults = false;
  state.recognition.onresult = (e) => {
    $('prompt').value = e.results[0][0].transcript;
    $('micBtn').classList.remove('recording');
    $('prompt').focus();
  };
  state.recognition.onerror = () => $('micBtn').classList.remove('recording');
  state.recognition.onend = () => $('micBtn').classList.remove('recording');
}

function resetWelcome() {
  $('messages').innerHTML = `
    <div class="welcome">
      <div class="welcome-mark">R<span>.</span></div>
      <p id="greeting" class="eyebrow">${greeting()}</p>
      <h2>Yeni bir sayfa</h2>
      <p class="welcome-copy">Bir soru sorabilir, bir dosya bırakabilir ya da sadece düşüncelerini yazabilirsin. Cevaplar internetten gelen bilgilerle desteklenir.</p>
      <div class="suggestions">
        <button class="chip" data-prompt="Bugünün öne çıkan haberleri neler?"><span>01</span> Haberlere göz at</button>
        <button class="chip" data-prompt="125 * 8 + 17 kaç eder?"><span>02</span> Bir hesap yap</button>
        <button class="chip" data-prompt="Ankara'da hava durumu nasıl?"><span>03</span> Havaya bak</button>
      </div>
    </div>`;
  wireChips();
}

function wireChips() {
  document.querySelectorAll('.chip').forEach((chip) => {
    chip.onclick = () => {
      $('prompt').value = chip.dataset.prompt;
      $('prompt').focus();
    };
  });
}

// ---------- açık / koyu tema ----------
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem('ai_theme', theme); } catch {}
  document.querySelectorAll('.theme-toggle').forEach((btn) => {
    const label = btn.querySelector('.theme-label');
    if (label) label.textContent = theme === 'dark' ? 'Açık tema' : 'Koyu tema';
    btn.title = theme === 'dark' ? 'Açık temaya geç' : 'Koyu temaya geç';
  });
}

function initTheme() {
  let theme = null;
  try { theme = localStorage.getItem('ai_theme'); } catch {}
  if (!theme) {
    theme = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark' : 'light';
  }
  applyTheme(theme);
}

document.querySelectorAll('.theme-toggle').forEach((btn) => {
  btn.onclick = () => applyTheme(
    document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'
  );
});

// ---------- giriş / kayıt / e-posta doğrulama ----------
let authMode = 'login';
let pendingEmail = '';

function setAuthMode(mode) {
  authMode = mode;
  const reg = mode === 'register';
  const verify = mode === 'verify';
  $('authFields').classList.toggle('hidden', verify);
  $('verifyBox').classList.toggle('hidden', !verify);
  $('authTitle').textContent = verify ? 'Kodu gir' : reg ? 'Hesap oluştur' : 'Giriş yap';
  $('authDesc').textContent = verify
    ? 'E-postana gelen 6 haneli kodu yaz.'
    : reg
      ? 'Kısa bir bilgiyle başlayalım.'
      : 'Kullanıcı adın veya e-postan ile devam et.';
  $('userLabel').textContent = reg ? 'Kullanıcı adı' : 'Kullanıcı adı veya e-posta';
  $('emailField').classList.toggle('hidden', !reg);
  $('loginBtnText').textContent = reg ? 'Kayıt ol' : 'Giriş yap';
  $('registerBtn').textContent = reg
    ? 'Zaten hesabım var · Giriş yap'
    : 'Yeni hesap oluştur';
  $('loginMsg').textContent = '';
  $('loginMsg').style.color = '';
  if (!verify) {
    $('verifyMsg').className = 'msg';
    $('verifyMsg').textContent = '';
  }
}

function showVerify(email, devCode, message) {
  pendingEmail = email;
  setAuthMode('verify');
  $('verifyDesc').textContent = message || `${email} adresine bir kod gönderdik.`;
  const msg = $('verifyMsg');
  msg.className = devCode ? 'dev-code' : 'msg';
  msg.textContent = devCode
    ? `SMTP ayarlanmadı — test kodu: ${devCode}`
    : '';
  $('verifyCode').value = '';
  $('verifyCode').focus();
}

async function doLogin(identifier, password) {
  const data = await api('/api/login', {
    method: 'POST',
    body: JSON.stringify({ username: identifier, password }),
  });
  state.token = data.token;
  state.user = data.user;
  localStorage.setItem('ai_token', data.token);
  showApp();
}

$('loginBtn').onclick = async () => {
  const msg = $('loginMsg');
  msg.textContent = '';
  const username = $('loginUser').value.trim();
  const password = $('loginPass').value;
  try {
    if (authMode === 'register') {
      const r = await api('/api/register', {
        method: 'POST',
        body: JSON.stringify({
          username,
          email: $('registerEmail').value.trim(),
          password,
        }),
      });
      showVerify(
        r.email,
        r.dev_code,
        r.email_sent
          ? `${r.email} adresine kod gönderildi.`
          : 'Kod hazır. SMTP ayarlanmadığı için aşağıda gösteriliyor.'
      );
      return;
    }
    await doLogin(username, password);
  } catch (e) {
    if (e.verifyRequired && e.email) {
      showVerify(e.email, null, 'Bu hesabın e-postası doğrulanmadı. Kodu girerek devam et.');
      return;
    }
    msg.textContent = e.message;
  }
};

$('verifyBtn').onclick = async () => {
  const msg = $('verifyMsg');
  msg.className = 'msg';
  msg.textContent = '';
  try {
    const data = await api('/api/verify-email', {
      method: 'POST',
      body: JSON.stringify({ email: pendingEmail, code: $('verifyCode').value.trim() }),
    });
    state.token = data.token;
    state.user = data.user;
    localStorage.setItem('ai_token', data.token);
    showApp();
  } catch (e) { msg.textContent = e.message; }
};

$('resendBtn').onclick = async () => {
  const msg = $('verifyMsg');
  msg.className = 'msg';
  msg.textContent = 'Yeni kod hazırlanıyor...';
  try {
    const r = await api('/api/resend-code', {
      method: 'POST',
      body: JSON.stringify({ email: pendingEmail }),
    });
    msg.className = r.dev_code ? 'dev-code' : 'msg';
    msg.textContent = r.dev_code
      ? `SMTP ayarlanmadı — yeni test kodu: ${r.dev_code}`
      : 'Yeni kod gönderildi.';
  } catch (e) { msg.textContent = e.message; }
};

$('backToLogin').onclick = () => setAuthMode('login');
$('registerBtn').onclick = () => setAuthMode(authMode === 'login' ? 'register' : 'login');

$('loginPass').addEventListener('keydown', (e) => { if (e.key === 'Enter') $('loginBtn').click(); });
$('registerEmail').addEventListener('keydown', (e) => { if (e.key === 'Enter') $('loginBtn').click(); });
$('verifyCode').addEventListener('keydown', (e) => { if (e.key === 'Enter') $('verifyBtn').click(); });
$('logoutBtn').onclick = async () => {
  try { await api('/api/logout', { method: 'POST' }); } catch {}
  logoutLocal();
};
$('adminLink').onclick = () => window.open('/admin', '_blank');
$('newChatBtn').onclick = () => {
  state.convId = null;
  $('pageTitle').textContent = 'Yeni sohbet';
  resetWelcome();
};
$('sendBtn').onclick = sendMessage;
$('prompt').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});
$('micBtn').onclick = () => {
  if (!state.recognition) return;
  $('micBtn').classList.add('recording');
  state.recognition.start();
};
$('fileInput').onchange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const form = new FormData();
  form.append('file', file);
  try {
    const r = await api('/api/upload', { method: 'POST', body: form });
    alert(`${r.filename} yüklendi (${r.chars} karakter analiz edildi).`);
    loadFiles();
  } catch (err) { alert(err.message); }
  e.target.value = '';
};
$('sidebarToggle').onclick = () => document.querySelector('.sidebar').classList.toggle('open');

initTheme();
setupVoice();
wireChips();
init();
