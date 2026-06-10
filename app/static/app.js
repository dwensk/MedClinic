'use strict';

const TOKEN_KEY = 'medklinik_token';
let token = localStorage.getItem(TOKEN_KEY);
let currentUser = null;

// ── Cached lookup maps (id → label) populated when tabs load ──────────────
let doctorMap  = {};
let patientMap = {};
let deptMap    = {};

// ── Appointments state ─────────────────────────────────────────────────────
let doctorData    = {};    // id → specialization string
let _appointments  = [];   // full list, refreshed on each load
let _apptFilter    = 'all';
let _editingApptId  = null;
let _deletingApptId = null;

// ── API wrapper ───────────────────────────────────────────────────────────

async function api(path, { method = 'GET', body = null, form = false } = {}) {
  const headers = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  let fetchBody;
  if (body && form) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
    fetchBody = new URLSearchParams(body).toString();
  } else if (body) {
    headers['Content-Type'] = 'application/json';
    fetchBody = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(path, { method, headers, body: fetchBody });
  } catch {
    return null;
  }

  if (res.status === 401) {
    logout();
    return null;
  }
  return res;
}

// ── Auth ──────────────────────────────────────────────────────────────────

async function login(email, password) {
  const res = await api('/auth/login', {
    method: 'POST',
    body: { username: email, password },
    form: true,
  });

  if (!res) { showMsg('login-error', 'Нет ответа от сервера'); return; }

  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    showMsg('login-error', d.detail || 'Неверный email или пароль');
    return;
  }

  const d = await res.json();
  token = d.access_token;
  localStorage.setItem(TOKEN_KEY, token);
  await initDashboard();
}

async function fetchMe() {
  const res = await api('/auth/me');
  if (!res || !res.ok) return null;
  return res.json();
}

function logout() {
  token = null;
  currentUser = null;
  localStorage.removeItem(TOKEN_KEY);
  doctorMap  = {};
  patientMap = {};
  deptMap    = {};
  doctorData = {};
  showLogin();
}

// ── Initialisation ────────────────────────────────────────────────────────

async function initDashboard() {
  currentUser = await fetchMe();
  if (!currentUser) { showLogin(); return; }

  const roleLabel = currentUser.role === 'admin' ? 'Администратор' : 'Врач';
  document.getElementById('user-display').textContent =
    `${currentUser.full_name} · ${roleLabel}`;

  // Show admin-only elements for admins, hide for doctors.
  document.querySelectorAll('.admin-only').forEach(el => {
    el.classList.toggle('hidden', currentUser.role !== 'admin');
  });

  showDashboard();
  showTab('patients');
}

// ── View helpers ──────────────────────────────────────────────────────────

function showLogin() {
  document.getElementById('login-screen').classList.remove('hidden');
  document.getElementById('dashboard').classList.add('hidden');
}

function showDashboard() {
  document.getElementById('login-screen').classList.add('hidden');
  document.getElementById('dashboard').classList.remove('hidden');
}

function showMsg(id, text, isSuccess = false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = isSuccess ? 'success-msg' : 'error-msg';
  el.classList.remove('hidden');
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.add('hidden'), isSuccess ? 3000 : 6000);
}

function setTableRows(tableId, rows) {
  const tbody = document.querySelector(`#${tableId} tbody`);
  if (!rows.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="99">Нет данных</td></tr>';
  } else {
    tbody.innerHTML = rows.join('');
  }
}

function esc(v) {
  return String(v ?? '—')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formToObj(form) {
  const obj = {};
  new FormData(form).forEach((val, key) => {
    if (val !== '') obj[key] = val;
  });
  return obj;
}

// ── Tabs ──────────────────────────────────────────────────────────────────

function showTab(name) {
  document.querySelectorAll('.tab-btn').forEach(btn =>
    btn.classList.toggle('active', btn.dataset.tab === name));
  document.querySelectorAll('.tab-panel').forEach(panel =>
    panel.classList.toggle('hidden', panel.id !== `tab-${name}`));

  switch (name) {
    case 'patients':     loadPatients();     break;
    case 'doctors':      loadDoctors();      break;
    case 'departments':  loadDepartments();  break;
    case 'appointments': loadAppointments(); break;
  }
}

// ── Patients ──────────────────────────────────────────────────────────────

async function loadPatients() {
  const res = await api('/patients/');
  if (!res) return;
  if (!res.ok) { showMsg('patients-error', 'Не удалось загрузить пациентов'); return; }

  const list = await res.json();

  // Update lookup map for appointments selects.
  patientMap = {};
  list.forEach(p => { patientMap[p.id] = `${p.full_name} (${p.iin})`; });

  setTableRows('patients-table', list.map(p => `
    <tr>
      <td>${p.id}</td>
      <td>${esc(p.full_name)}</td>
      <td>${esc(p.iin)}</td>
      <td>${esc(p.phone)}</td>
      <td>${p.birth_date ?? '—'}</td>
      <td>${p.gender ?? '—'}</td>
    </tr>`));
}

async function createPatient(data) {
  const res = await api('/patients/', { method: 'POST', body: data });
  if (!res) return false;
  if (res.status === 403) {
    const d = await res.json().catch(() => ({}));
    showMsg('patients-error', d.detail || 'Недостаточно прав');
    return false;
  }
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    showMsg('patients-error', d.detail || 'Ошибка при создании пациента');
    return false;
  }
  showMsg('patients-success', 'Пациент успешно добавлен', true);
  await loadPatients();
  return true;
}

// ── Departments ───────────────────────────────────────────────────────────

async function loadDepartments() {
  const res = await api('/departments/');
  if (!res) return;
  if (!res.ok) { showMsg('departments-error', 'Не удалось загрузить отделения'); return; }

  const list = await res.json();
  const isAdmin = currentUser?.role === 'admin';

  deptMap = {};
  list.forEach(d => { deptMap[d.id] = d.name; });

  // Refresh doctor-form department select.
  const sel = document.getElementById('doctor-dept-select');
  sel.innerHTML = '<option value="">— выберите —</option>' +
    list.map(d => `<option value="${d.id}">${esc(d.name)}</option>`).join('');

  setTableRows('departments-table', list.map(d => `
    <tr>
      <td>${d.id}</td>
      <td>${esc(d.name)}</td>
      <td>${d.description ? esc(d.description) : '—'}</td>
      ${isAdmin ? `<td><button class="btn-sm btn-danger" onclick="deleteDepartment(${d.id})">Удалить</button></td>` : ''}
    </tr>`));
}

async function createDepartment(data) {
  const res = await api('/departments/', { method: 'POST', body: data });
  if (!res) return false;
  if (res.status === 403) {
    const d = await res.json().catch(() => ({}));
    showMsg('departments-error', d.detail || 'Недостаточно прав');
    return false;
  }
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    showMsg('departments-error', d.detail || 'Ошибка при создании отделения');
    return false;
  }
  showMsg('departments-success', 'Отделение успешно добавлено', true);
  await loadDepartments();
  return true;
}

async function deleteDepartment(id) {
  if (!confirm('Удалить отделение?')) return;
  const res = await api(`/departments/${id}`, { method: 'DELETE' });
  if (!res) return;
  if (res.status === 403) { showMsg('departments-error', 'Недостаточно прав'); return; }
  if (res.status === 409) {
    const d = await res.json().catch(() => ({}));
    showMsg('departments-error', d.detail || 'Невозможно удалить');
    return;
  }
  if (!res.ok) { showMsg('departments-error', 'Ошибка при удалении'); return; }
  showMsg('departments-success', 'Отделение удалено', true);
  await loadDepartments();
}

// ── Doctors ───────────────────────────────────────────────────────────────

async function loadDoctors() {
  // Make sure deptMap is populated for display labels.
  if (!Object.keys(deptMap).length) {
    const dr = await api('/departments/');
    if (dr && dr.ok) {
      const dl = await dr.json();
      dl.forEach(d => { deptMap[d.id] = d.name; });
      const sel = document.getElementById('doctor-dept-select');
      sel.innerHTML = '<option value="">— выберите —</option>' +
        dl.map(d => `<option value="${d.id}">${esc(d.name)}</option>`).join('');
    }
  }

  const res = await api('/doctors/');
  if (!res) return;
  if (!res.ok) { showMsg('doctors-error', 'Не удалось загрузить врачей'); return; }

  const list = await res.json();
  const isAdmin = currentUser?.role === 'admin';

  doctorMap  = {};
  doctorData = {};
  list.forEach(d => {
    doctorMap[d.id]  = `#${d.id} — ${d.specialization}`;
    doctorData[d.id] = d.specialization;
  });

  setTableRows('doctors-table', list.map(d => `
    <tr>
      <td>${d.id}</td>
      <td style="color:var(--muted);font-size:.8125rem">польз.&nbsp;${d.user_id}</td>
      <td>${esc(d.specialization)}</td>
      <td>${deptMap[d.department_id] ? esc(deptMap[d.department_id]) : d.department_id}</td>
      <td>${esc(d.phone)}</td>
      <td>${d.cabinet ? esc(d.cabinet) : '—'}</td>
      ${isAdmin ? `<td><button class="btn-sm btn-danger" onclick="deleteDoctor(${d.id})">Удалить</button></td>` : ''}
    </tr>`));
}

async function createDoctor(data) {
  data.department_id = parseInt(data.department_id, 10);
  const res = await api('/doctors/', { method: 'POST', body: data });
  if (!res) return false;
  if (res.status === 403) {
    const d = await res.json().catch(() => ({}));
    showMsg('doctors-error', d.detail || 'Недостаточно прав');
    return false;
  }
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    showMsg('doctors-error', d.detail || 'Ошибка при создании врача');
    return false;
  }
  showMsg('doctors-success', 'Врач успешно добавлен', true);
  await loadDoctors();
  return true;
}

async function deleteDoctor(id) {
  if (!confirm('Удалить врача?')) return;
  const res = await api(`/doctors/${id}`, { method: 'DELETE' });
  if (!res) return;
  if (res.status === 403) { showMsg('doctors-error', 'Недостаточно прав'); return; }
  if (res.status === 409) {
    const d = await res.json().catch(() => ({}));
    showMsg('doctors-error', d.detail || 'Невозможно удалить');
    return;
  }
  if (!res.ok) { showMsg('doctors-error', 'Ошибка при удалении'); return; }
  showMsg('doctors-success', 'Врач удалён', true);
  await loadDoctors();
}

// ── Appointments ──────────────────────────────────────────────────────────

const STATUS_LABELS = {
  scheduled: 'Запланирована',
  completed:  'Завершена',
  cancelled:  'Отменена',
  no_show:    'Не явился',
};

async function loadAppointments() {
  await refreshDoctorSelect();
  await refreshPatientSelect();

  const res = await api('/appointments/');
  if (!res) return;
  if (!res.ok) { showMsg('appointments-error', 'Не удалось загрузить записи'); return; }

  _appointments = await res.json();
  renderAppointments();
}

function renderAppointments() {
  const filtered = _apptFilter === 'all'
    ? _appointments
    : _appointments.filter(a => a.status === _apptFilter);

  const canAct = currentUser?.role === 'admin' || currentUser?.role === 'doctor';
  const tbody  = document.querySelector('#appointments-table tbody');

  if (!filtered.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="7">Записей не найдено</td></tr>';
    return;
  }

  tbody.innerHTML = filtered.map(a => {
    const dt = new Date(a.scheduled_at).toLocaleString('ru-RU', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
    return `<tr>
      <td>${esc(patientMap[a.patient_id] ?? `#${a.patient_id}`)}</td>
      <td>Врач&nbsp;#${a.doctor_id}</td>
      <td>${esc(doctorData[a.doctor_id] ?? '—')}</td>
      <td>${dt}</td>
      <td><span class="status-badge status-${a.status}">${STATUS_LABELS[a.status] ?? a.status}</span></td>
      <td>${a.reason ? esc(a.reason) : '—'}</td>
      <td class="actions-cell">${canAct ? `
        <button class="btn-icon" title="Редактировать" onclick="openEditModal(${a.id})">✏</button>
        <button class="btn-icon btn-icon-danger" title="Удалить" onclick="openDeleteModal(${a.id})">🗑</button>` : ''}</td>
    </tr>`;
  }).join('');
}

async function refreshDoctorSelect() {
  if (Object.keys(doctorMap).length) {
    // Cache is warm — just rebuild the select from the map.
    rebuildDoctorSelect();
    return;
  }
  const res = await api('/doctors/');
  if (!res || !res.ok) return;
  const list = await res.json();
  doctorMap  = {};
  doctorData = {};
  list.forEach(d => {
    doctorMap[d.id]  = `#${d.id} — ${d.specialization}`;
    doctorData[d.id] = d.specialization;
  });
  rebuildDoctorSelect();
}

function rebuildDoctorSelect() {
  const sel = document.getElementById('appt-doctor-select');
  sel.innerHTML = '<option value="">— выберите врача —</option>' +
    Object.entries(doctorMap).map(([id, label]) =>
      `<option value="${id}">${esc(label)}</option>`).join('');
}

async function refreshPatientSelect() {
  if (Object.keys(patientMap).length) {
    rebuildPatientSelect();
    return;
  }
  const res = await api('/patients/');
  if (!res || !res.ok) return;
  const list = await res.json();
  patientMap = {};
  list.forEach(p => { patientMap[p.id] = `${p.full_name} (${p.iin})`; });
  rebuildPatientSelect();
}

function rebuildPatientSelect() {
  const sel = document.getElementById('appt-patient-select');
  sel.innerHTML = '<option value="">— выберите пациента —</option>' +
    Object.entries(patientMap).map(([id, label]) =>
      `<option value="${id}">${esc(label)}</option>`).join('');
}

async function createAppointment(data) {
  data.doctor_id  = parseInt(data.doctor_id,  10);
  data.patient_id = parseInt(data.patient_id, 10);
  // datetime-local gives "YYYY-MM-DDTHH:MM" — append seconds so server parses it.
  if (data.scheduled_at && data.scheduled_at.length === 16) {
    data.scheduled_at += ':00';
  }

  const res = await api('/appointments/', { method: 'POST', body: data });
  if (!res) return false;
  if (res.status === 403) {
    const d = await res.json().catch(() => ({}));
    showMsg('appointments-error', d.detail || 'Недостаточно прав');
    return false;
  }
  if (res.status === 409) {
    const d = await res.json().catch(() => ({}));
    showMsg('appointments-error', d.detail || 'Конфликт времени');
    return false;
  }
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    showMsg('appointments-error', d.detail || 'Ошибка при создании записи');
    return false;
  }
  showMsg('appointments-success', 'Запись успешно создана', true);
  await loadAppointments();
  return true;
}

// ── Appointment modals ────────────────────────────────────────────────────

function toDatetimeLocal(iso) {
  const d   = new Date(iso);
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function openEditModal(id) {
  const a = _appointments.find(a => a.id === id);
  if (!a) return;
  _editingApptId = id;
  document.getElementById('edit-scheduled-at').value = toDatetimeLocal(a.scheduled_at);
  document.getElementById('edit-status').value        = a.status;
  document.getElementById('edit-reason').value        = a.reason ?? '';
  document.getElementById('appt-edit-modal').classList.remove('hidden');
}

function closeEditModal() {
  _editingApptId = null;
  document.getElementById('appt-edit-modal').classList.add('hidden');
}

async function saveEditAppointment() {
  if (_editingApptId === null) return;
  const scheduledAt = document.getElementById('edit-scheduled-at').value;
  const status      = document.getElementById('edit-status').value;
  const reason      = document.getElementById('edit-reason').value;

  const body = { status, reason: reason || null };
  if (scheduledAt) {
    body.scheduled_at = scheduledAt.length === 16 ? scheduledAt + ':00' : scheduledAt;
  }

  const res = await api(`/appointments/${_editingApptId}`, { method: 'PATCH', body });
  if (!res) return;
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    showMsg('appointments-error', d.detail || 'Ошибка при сохранении');
    return;
  }
  closeEditModal();
  await loadAppointments();
}

function openDeleteModal(id) {
  _deletingApptId = id;
  document.getElementById('appt-delete-modal').classList.remove('hidden');
}

function closeDeleteModal() {
  _deletingApptId = null;
  document.getElementById('appt-delete-modal').classList.add('hidden');
}

async function confirmDeleteAppointment() {
  if (_deletingApptId === null) return;
  const id = _deletingApptId;
  closeDeleteModal();
  const res = await api(`/appointments/${id}`, { method: 'DELETE' });
  if (!res) return;
  if (!res.ok) { showMsg('appointments-error', 'Ошибка при удалении записи'); return; }
  showToast('Запись удалена');
  await loadAppointments();
}

function showToast(msg) {
  const el = document.createElement('div');
  el.className = 'toast-msg';
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

// ── Event wiring ──────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {

  document.getElementById('login-form').addEventListener('submit', async e => {
    e.preventDefault();
    await login(
      document.getElementById('login-email').value,
      document.getElementById('login-password').value
    );
  });

  document.getElementById('logout-btn').addEventListener('click', logout);

  document.querySelectorAll('.tab-btn').forEach(btn =>
    btn.addEventListener('click', () => showTab(btn.dataset.tab)));

  document.getElementById('patient-form').addEventListener('submit', async e => {
    e.preventDefault();
    const ok = await createPatient(formToObj(e.target));
    if (ok) e.target.reset();
  });

  document.getElementById('doctor-form').addEventListener('submit', async e => {
    e.preventDefault();
    const ok = await createDoctor(formToObj(e.target));
    if (ok) e.target.reset();
  });

  document.getElementById('dept-form').addEventListener('submit', async e => {
    e.preventDefault();
    const ok = await createDepartment(formToObj(e.target));
    if (ok) e.target.reset();
  });

  document.getElementById('appt-form').addEventListener('submit', async e => {
    e.preventDefault();
    const ok = await createAppointment(formToObj(e.target));
    if (ok) e.target.reset();
  });

  // Appointment filter tabs — client-side filtering.
  document.querySelectorAll('.filter-tab').forEach(tab =>
    tab.addEventListener('click', () => {
      _apptFilter = tab.dataset.filter;
      document.querySelectorAll('.filter-tab').forEach(t =>
        t.classList.toggle('active', t === tab));
      renderAppointments();
    }));

  // Close modals when clicking the dimmed overlay.
  document.getElementById('appt-edit-modal').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeEditModal();
  });
  document.getElementById('appt-delete-modal').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeDeleteModal();
  });

  // Auto-login from stored token.
  if (token) {
    await initDashboard();
  } else {
    showLogin();
  }
});
