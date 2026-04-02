chrome.downloads.onCreated.addListener((downloadItem) => {
    chrome.storage.local.get(['autoCapture'], (result) => {
        const isEnabled = result.autoCapture !== false;

        // Validasi URL dan status aktif
        if (isEnabled && downloadItem.url && /^https?:\/\//.test(downloadItem.url)) {
            
            // LANGKAH 1: Langsung Cancel dan Hapus dari UI Chrome
            chrome.downloads.cancel(downloadItem.id, () => {
                chrome.downloads.erase({ id: downloadItem.id });
            });

            // LANGKAH 2: Kirim ke NDM
            const targetUrl = `http://127.0.0.1:5555/add?url=${encodeURIComponent(downloadItem.url)}`;
            
            fetch(targetUrl)
                .then(res => {
                    if (!res.ok) console.error('NDM Offline');
                })
                .catch(err => console.error('Gagal kirim:', err));
        }
    });
});