// Estado da Aplicação
let currentNotes = [];
let currentFilter = 'all';
let selectedDate = '';
let mediaRecorder = null;
let audioChunks = [];
let recordStartTime = 0;
let recordTimerInterval = null;
let currentCoords = { lat: null, lng: null };

// Elementos DOM
const recordBtn = document.getElementById('record-btn');
const recordIcon = document.getElementById('record-icon');
const recordingBanner = document.getElementById('recording-banner');
const recordingTimer = document.getElementById('recording-timer');
const timelineFeed = document.getElementById('timeline-feed');
const emptyState = document.getElementById('empty-state');
const dateSelect = document.getElementById('date-select');
const currentDateDisplay = document.getElementById('current-date-display');
const gpsStatus = document.getElementById('gps-status');
const gpsText = document.getElementById('gps-text');
const filterChips = document.getElementById('filter-chips');
const countAll = document.getElementById('count-all');

// Modais
const processingModal = document.getElementById('processing-modal');
const summaryModal = document.getElementById('summary-modal');
const settingsModal = document.getElementById('settings-modal');
const btnSummary = document.getElementById('btn-summary');
const btnSettings = document.getElementById('btn-settings');
const closeSummaryBtn = document.getElementById('close-summary-btn');
const closeSettingsBtn = document.getElementById('close-settings-btn');
const saveSettingsBtn = document.getElementById('save-settings-btn');
const copySummaryBtn = document.getElementById('copy-summary-btn');
const apiKeyInput = document.getElementById('api-key-input');
const summaryContent = document.getElementById('summary-content');
const localIpBadge = document.getElementById('local-ip-badge');

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
  initAppInfo();
  initGPS();
  loadNotes();
  setupEventListeners();
  updateDateHeader();
});

function updateDateHeader() {
  const now = new Date();
  const options = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' };
  currentDateDisplay.textContent = now.toLocaleDateString('pt-PT', options);
}

// Inicializar info do servidor e IP
async function initAppInfo() {
  try {
    const res = await fetch('/api/info');
    const data = await res.json();
    if (data.local_ip) {
      localIpBadge.textContent = `http://${data.local_ip}:8000`;
    }
    if (!data.has_api_key) {
      // Mostrar modal de definições caso ainda não tenha chave
      setTimeout(() => {
        openModal(settingsModal);
      }, 500);
    }
  } catch (err) {
    console.error('Erro ao obter info do servidor:', err);
  }
}

// Inicializar e escutar GPS
function initGPS() {
  if (!navigator.geolocation) {
    gpsStatus.className = 'gps-status searching';
    gpsText.textContent = 'GPS Indisponível';
    return;
  }

  gpsStatus.className = 'gps-status searching';
  gpsText.textContent = 'A obter GPS...';

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      currentCoords.lat = pos.coords.latitude;
      currentCoords.lng = pos.coords.longitude;
      gpsStatus.className = 'gps-status ready';
      gpsText.textContent = 'GPS Ativo';
    },
    (err) => {
      console.warn('GPS não autorizado ou inacessível:', err.message);
      gpsStatus.className = 'gps-status searching';
      gpsText.textContent = 'GPS Desligado';
    },
    { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }
  );
}

// Carregar notas da BD
async function loadNotes(targetDate = '') {
  try {
    const url = targetDate ? `/api/notes?date=${encodeURIComponent(targetDate)}` : '/api/notes';
    const res = await fetch(url);
    const data = await res.json();

    selectedDate = data.selected_date;
    currentNotes = data.notes || [];

    // Atualizar dropdown de datas
    updateDateSelector(data.available_dates, selectedDate);

    // Renderizar lista
    renderTimeline();
  } catch (err) {
    console.error('Erro ao carregar notas:', err);
  }
}

function updateDateSelector(availableDates, activeDate) {
  dateSelect.innerHTML = '';
  const todayStr = new Date().toISOString().split('T')[0];

  let dates = availableDates.includes(todayStr) ? availableDates : [todayStr, ...availableDates];

  dates.forEach((d) => {
    const opt = document.createElement('option');
    opt.value = d;
    if (d === todayStr) {
      opt.textContent = `Hoje (${formatDisplayDate(d)})`;
    } else {
      opt.textContent = formatDisplayDate(d);
    }
    if (d === activeDate) {
      opt.selected = true;
    }
    dateSelect.appendChild(opt);
  });
}

function formatDisplayDate(dateStr) {
  try {
    const [y, m, d] = dateStr.split('-');
    return `${d}/${m}/${y}`;
  } catch {
    return dateStr;
  }
}

// Renderizar Timeline
function renderTimeline() {
  timelineFeed.innerHTML = '';

  let filtered = currentNotes;
  if (currentFilter !== 'all') {
    filtered = currentNotes.filter((n) => n.theme.toLowerCase().includes(currentFilter.toLowerCase()));
  }

  countAll.textContent = currentNotes.length;

  if (filtered.length === 0) {
    emptyState.classList.remove('hidden');
    timelineFeed.classList.add('hidden');
    return;
  }

  emptyState.classList.add('hidden');
  timelineFeed.classList.remove('hidden');

  filtered.forEach((note) => {
    const card = document.createElement('div');
    card.className = 'note-card';

    // Determinar estilo do tema
    let themeClass = 'theme-pill';
    let themeIcon = 'fa-tag';
    if (note.theme.toLowerCase().includes('jardim')) {
      themeClass += ' theme-Jardinagem';
      themeIcon = 'fa-seedling';
    } else if (note.theme.toLowerCase().includes('piscina')) {
      themeClass += ' theme-Piscinas';
      themeIcon = 'fa-water-ladder';
    } else if (note.theme.toLowerCase().includes('compra') || note.theme.toLowerCase().includes('material')) {
      themeClass += ' theme-Compras';
      themeIcon = 'fa-cart-shopping';
    } else if (note.theme.toLowerCase().includes('cliente') || note.theme.toLowerCase().includes('contacto')) {
      themeClass += ' theme-Cliente';
      themeIcon = 'fa-user-tie';
    }

    // HTML das Tarefas se existirem
    let tasksHtml = '';
    if (note.tasks && note.tasks.length > 0) {
      tasksHtml = `
        <div class="tasks-list">
          <h4><i class="fa-solid fa-list-check"></i> Ações / Tarefas</h4>
          <ul>
            ${note.tasks.map((t) => `<li>${escapeHtml(t)}</li>`).join('')}
          </ul>
        </div>
      `;
    }

    // HTML do Local se existir
    let locationHtml = '';
    if (note.location_name) {
      locationHtml = `
        <div class="location-tag">
          <i class="fa-solid fa-location-dot"></i>
          <span>${escapeHtml(note.location_name)}</span>
        </div>
      `;
    }

    card.innerHTML = `
      <div class="note-node-dot"></div>
      
      <div class="note-header">
        <span class="time-badge"><i class="fa-regular fa-clock"></i> ${note.time_str}</span>
        <span class="${themeClass}"><i class="fa-solid ${themeIcon}"></i> ${escapeHtml(note.theme)}</span>
      </div>

      ${locationHtml}

      <div class="note-summary">
        ${escapeHtml(note.summary)}
      </div>

      ${tasksHtml}

      <div>
        <button class="transcription-toggle" onclick="toggleTranscription(${note.id})">
          Ver transcrição completa
        </button>
        <div id="transcription-${note.id}" class="transcription-text hidden">
          "${escapeHtml(note.transcription)}"
        </div>
      </div>

      <div class="note-footer">
        ${
          note.audio_path
            ? `<audio controls class="audio-player" src="${note.audio_path}" preload="none"></audio>`
            : '<div></div>'
        }
        <button class="btn-card-action" onclick="deleteNote(${note.id})" title="Eliminar nota">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      </div>
    `;

    timelineFeed.appendChild(card);
  });
}

window.toggleTranscription = function (id) {
  const el = document.getElementById(`transcription-${id}`);
  if (el) {
    el.classList.toggle('hidden');
  }
};

window.deleteNote = async function (id) {
  if (!confirm('Tens a certeza que pretendes eliminar este registo?')) return;
  try {
    const res = await fetch(`/api/notes/${id}`, { method: 'DELETE' });
    if (res.ok) {
      currentNotes = currentNotes.filter((n) => n.id !== id);
      renderTimeline();
    }
  } catch (err) {
    alert('Erro ao eliminar nota.');
  }
};

// Gravação de Áudio com Suporte a iPhone Safari
async function startRecording() {
  try {
    // Atualizar GPS no instante antes de gravar
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          currentCoords.lat = pos.coords.latitude;
          currentCoords.lng = pos.coords.longitude;
        },
        null,
        { enableHighAccuracy: true, timeout: 3000 }
      );
    }

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    // Encontrar o tipo MIME suportado pelo navegador (Safari usa mp4/aac, Chrome usa webm)
    let mimeType = 'audio/webm';
    if (MediaRecorder.isTypeSupported('audio/mp4')) {
      mimeType = 'audio/mp4';
    } else if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
      mimeType = 'audio/webm;codecs=opus';
    } else if (MediaRecorder.isTypeSupported('audio/aac')) {
      mimeType = 'audio/aac';
    }

    mediaRecorder = new MediaRecorder(stream, { mimeType });
    audioChunks = [];

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: mimeType });
      // Parar faixas de microfone
      stream.getTracks().forEach((track) => track.stop());
      await uploadAudio(audioBlob, mimeType);
    };

    mediaRecorder.start();
    recordStartTime = Date.now();
    recordBtn.classList.add('is-recording');
    recordIcon.className = 'fa-solid fa-stop';
    recordingBanner.classList.remove('hidden');

    recordTimerInterval = setInterval(updateRecordTimer, 500);
  } catch (err) {
    console.error('Erro ao aceder ao microfone:', err);
    alert('Não foi possível aceder ao microfone. Por favor permite o acesso nas permissões do navegador.');
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop();
  }
  clearInterval(recordTimerInterval);
  recordBtn.classList.remove('is-recording');
  recordIcon.className = 'fa-solid fa-microphone';
  recordingBanner.classList.add('hidden');
}

function updateRecordTimer() {
  const elapsed = Math.floor((Date.now() - recordStartTime) / 1000);
  const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
  const secs = String(elapsed % 60).padStart(2, '0');
  recordingTimer.textContent = `${mins}:${secs}`;
}

// Enviar Áudio para o Backend
async function uploadAudio(blob, mimeType) {
  openModal(processingModal);

  const durationSec = (Date.now() - recordStartTime) / 1000;
  const now = new Date();
  const clientTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  const clientDate = now.toISOString().split('T')[0];

  const ext = mimeType.includes('mp4') ? 'm4a' : 'webm';
  const formData = new FormData();
  formData.append('audio_file', blob, `gravação.${ext}`);
  if (currentCoords.lat !== null) formData.append('latitude', currentCoords.lat);
  if (currentCoords.lng !== null) formData.append('longitude', currentCoords.lng);
  formData.append('client_time', clientTime);
  formData.append('client_date', clientDate);
  formData.append('duration_sec', durationSec);

  try {
    const res = await fetch('/api/record', {
      method: 'POST',
      body: formData,
    });

    const data = await res.json();
    closeModal(processingModal);

    if (!res.ok) {
      alert(`Erro: ${data.detail || 'Falha ao processar gravação.'}`);
      if (data.detail && data.detail.includes('API')) {
        openModal(settingsModal);
      }
      return;
    }

    // Recarregar notas
    await loadNotes(clientDate);
  } catch (err) {
    closeModal(processingModal);
    alert('Erro de ligação ao processar o áudio.');
  }
}

// Event Listeners
function setupEventListeners() {
  recordBtn.addEventListener('click', () => {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      stopRecording();
    } else {
      startRecording();
    }
  });

  dateSelect.addEventListener('change', (e) => {
    loadNotes(e.target.value);
  });

  // Filtros por tema
  filterChips.addEventListener('click', (e) => {
    const chip = e.target.closest('.chip');
    if (!chip) return;

    document.querySelectorAll('.chip').forEach((c) => c.classList.remove('active'));
    chip.classList.add('active');
    currentFilter = chip.dataset.theme;
    renderTimeline();
  });

  // Modais
  btnSettings.addEventListener('click', () => openModal(settingsModal));
  closeSettingsBtn.addEventListener('click', () => closeModal(settingsModal));

  btnSummary.addEventListener('click', handleGenerateSummary);
  closeSummaryBtn.addEventListener('click', () => closeModal(summaryModal));

  saveSettingsBtn.addEventListener('click', async () => {
    const key = apiKeyInput.value.trim();
    if (!key) {
      alert('Insere a chave do Gemini.');
      return;
    }
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gemini_api_key: key }),
      });
      const data = await res.json();
      if (res.ok) {
        alert(data.message);
        closeModal(settingsModal);
      } else {
        alert(data.detail || 'Erro ao guardar chave.');
      }
    } catch {
      alert('Erro de ligação.');
    }
  });

  copySummaryBtn.addEventListener('click', () => {
    const text = summaryContent.innerText;
    navigator.clipboard.writeText(text).then(() => {
      copySummaryBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copiado!';
      setTimeout(() => {
        copySummaryBtn.innerHTML = '<i class="fa-solid fa-copy"></i> Copiar Resumo';
      }, 2000);
    });
  });
}

async function handleGenerateSummary() {
  if (currentNotes.length === 0) {
    alert('Ainda não tens notas gravadas para este dia.');
    return;
  }
  openModal(summaryModal);
  summaryContent.innerHTML = '<div class="loader"></div><p style="text-align:center; color:var(--text-muted)">A gerar resumo inteligente do teu dia com IA...</p>';

  try {
    const res = await fetch('/api/daily-summary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date_str: selectedDate }),
    });
    const data = await res.json();
    summaryContent.innerHTML = formatMarkdown(data.summary || 'Sem resumo.');
  } catch {
    summaryContent.innerHTML = '<p>Erro ao gerar resumo.</p>';
  }
}

function formatMarkdown(md) {
  // Conversor simples e seguro de Markdown para HTML
  let html = md
    .replace(/^# (.*$)/gim, '<h2>$1</h2>')
    .replace(/^### (.*$)/gim, '<h4>$1</h4>')
    .replace(/^## (.*$)/gim, '<h3>$1</h3>')
    .replace(/^\* (.*$)/gim, '<li>$1</li>')
    .replace(/^- (.*$)/gim, '<li>$1</li>')
    .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
    .replace(/\n\n/gim, '<br>');
  return html;
}

function openModal(modal) {
  modal.classList.remove('hidden');
}

function closeModal(modal) {
  modal.classList.add('hidden');
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
