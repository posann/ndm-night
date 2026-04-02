const dropZone = document.getElementById('drop-zone');
const status = document.getElementById('status');
const autoCaptureBtn = document.getElementById('auto-capture');
const urlInput = document.getElementById('url-input');
const sendBtn = document.getElementById('send-btn');

// ── Load state Auto-Capture ───────────────────────────────────────────────
chrome.storage.local.get(['autoCapture'], (result) => {
    autoCaptureBtn.checked = result.autoCapture !== false;
});

autoCaptureBtn.addEventListener('change', () => {
    chrome.storage.local.set({ autoCapture: autoCaptureBtn.checked });
    setStatus(`Auto-Capture: ${autoCaptureBtn.checked ? 'ON ✅' : 'OFF ❌'}`,
              autoCaptureBtn.checked ? '#4caf50' : '#888');
});

// ── Drag Events (menerima link dari halaman web) ─────────────────────────
dropZone.addEventListener('dragenter', (e) => {
    e.preventDefault();
    dropZone.classList.add('hover');
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = 'copy';
    dropZone.classList.add('hover');
});

dropZone.addEventListener('dragleave', (e) => {
    // Cegah flicker: hanya hapus hover jika benar-benar keluar dari drop zone
    if (!dropZone.contains(e.relatedTarget)) {
        dropZone.classList.remove('hover');
    }
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.remove('hover');

    // BUG FIX: Coba semua format data — Chrome pakai 'text/uri-list' saat drag link
    let url = '';

    // Priority 1: text/uri-list (standar HTML5 untuk drag link dari browser)
    const uriList = e.dataTransfer.getData('text/uri-list');
    if (uriList) {
        // uri-list bisa berisi beberapa URL dipisah newline, ambil yang pertama valid
        const urls = uriList.split('\n').filter(u => u.trim() && !u.startsWith('#'));
        if (urls.length > 0) url = urls[0].trim();
    }

    // Priority 2: text/plain
    if (!url) {
        url = (e.dataTransfer.getData('text/plain') || '').trim();
    }

    // Priority 3: URL (legacy format)
    if (!url) {
        url = (e.dataTransfer.getData('URL') || '').trim();
    }

    if (!url) {
        setStatus('❌ Tidak ada URL terdeteksi!', '#f44336');
        return;
    }

    // Auto-add protocol jika tidak ada
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        url = 'https://' + url;
    }

    if (isValidUrl(url)) {
        sendToApp(url);
    } else {
        setStatus('❌ Link tidak valid!', '#f44336');
    }
});

// ── Manual Input ──────────────────────────────────────────────────────────
sendBtn.addEventListener('click', () => {
    handleManualInput();
});

urlInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleManualInput();
});

// Auto-paste dari clipboard saat klik input (jika input masih kosong)
urlInput.addEventListener('click', async () => {
    if (urlInput.value.trim()) return; // Sudah ada isi, jangan timpa
    try {
        const text = await navigator.clipboard.readText();
        if (text && isValidUrl(text)) {
            urlInput.value = text;
            setStatus('📋 URL ditempel dari clipboard', '#007acc');
        }
    } catch (e) {
        // Clipboard permission ditolak, abaikan
    }
});

function handleManualInput() {
    let url = urlInput.value.trim();
    if (!url) {
        setStatus('⚠️ Masukkan URL terlebih dahulu!', '#ff9800');
        urlInput.focus();
        return;
    }

    // Auto-add protocol
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        url = 'https://' + url;
    }

    if (isValidUrl(url)) {
        sendToApp(url);
    } else {
        setStatus('❌ URL tidak valid!', '#f44336');
        urlInput.select();
    }
}

// ── Helper Functions ──────────────────────────────────────────────────────
function isValidUrl(url) {
    try {
        const u = new URL(url);
        return u.protocol === 'http:' || u.protocol === 'https:';
    } catch {
        return false;
    }
}

function setStatus(msg, color) {
    status.textContent = msg;
    status.style.color = color || '#4caf50';
}

function sendToApp(link) {
    setStatus('⏳ Mengirim ke NDM...', '#ff9800');
    urlInput.value = '';

    fetch(`http://127.0.0.1:5555/add?url=${encodeURIComponent(link)}`)
        .then(response => {
            if (response.ok) {
                setStatus('✅ Berhasil! Cek Aplikasi.', '#4caf50');
                setTimeout(() => window.close(), 1500);
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        })
        .catch(error => {
            setStatus('❌ Error: App tidak berjalan?', '#f44336');
            console.error('[NDM] Error:', error);
        });
}
