(function () {
    const storageKey = 'wearemania-upload-file-status';

    function formatBytes(bytes) {
        if (!bytes) return '0 KB';
        const units = ['B', 'KB', 'MB', 'GB'];
        const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
        return `${(bytes / Math.pow(1024, index)).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
    }

    function setProgress(percent, title, status) {
        const panel = document.getElementById('uploadProgress');
        const bar = document.getElementById('progressBar');
        const percentText = document.getElementById('progressPercent');
        const titleText = document.getElementById('progressTitle');
        const statusText = document.getElementById('progressStatus');
        const steps = Array.from(document.querySelectorAll('.step'));

        if (panel) panel.classList.add('active');
        if (bar) bar.style.width = `${percent}%`;
        if (percentText) percentText.textContent = `${percent}%`;
        if (titleText) titleText.textContent = title;
        if (statusText) statusText.textContent = status;

        const activeIndex = Math.min(Math.floor(percent / 26), steps.length - 1);
        steps.forEach(function (step, index) {
            step.classList.toggle('done', index < activeIndex);
            step.classList.toggle('active', index === activeIndex);
        });
    }

    function setSelectedFile(file) {
        const preview = document.getElementById('filePreview');
        const fileName = document.getElementById('selectedFileName');
        const fileSize = document.getElementById('selectedFileSize');
        const submitButton = document.getElementById('submitUploadBtn');

        if (!file) return;

        if (!file.name.toLowerCase().endsWith('.csv')) {
            alert('File harus berformat CSV. Pilih file dengan ekstensi .csv.');
            clearFile();
            return;
        }

        if (preview) preview.hidden = false;
        if (fileName) fileName.textContent = file.name;
        if (fileSize) fileSize.textContent = formatBytes(file.size);
        if (submitButton) submitButton.disabled = false;

        localStorage.setItem(storageKey, JSON.stringify({
            name: file.name,
            size: file.size,
            updatedAt: new Date().toISOString()
        }));
    }

    function clearFile() {
        const input = document.querySelector('#uploadForm input[type="file"]');
        const preview = document.getElementById('filePreview');
        const fileName = document.getElementById('selectedFileName');
        const fileSize = document.getElementById('selectedFileSize');
        const submitButton = document.getElementById('submitUploadBtn');
        const progress = document.getElementById('uploadProgress');

        if (input) input.value = '';
        if (preview) preview.hidden = true;
        if (fileName) fileName.textContent = 'Belum ada file dipilih';
        if (fileSize) fileSize.textContent = '-';
        if (submitButton) submitButton.disabled = true;
        if (progress) progress.classList.remove('active');

        localStorage.removeItem(storageKey);
    }

    function restoreFileInfo() {
        const raw = localStorage.getItem(storageKey);
        if (!raw) return;

        try {
            const saved = JSON.parse(raw);
            const preview = document.getElementById('filePreview');
            const fileName = document.getElementById('selectedFileName');
            const fileSize = document.getElementById('selectedFileSize');

            if (preview) preview.hidden = false;
            if (fileName) fileName.textContent = `${saved.name} (tersimpan di browser)`;
            if (fileSize) fileSize.textContent = `${formatBytes(saved.size)} · pilih ulang file jika ingin upload lagi`;
        } catch (error) {
            localStorage.removeItem(storageKey);
        }
    }

    function setupUploadForm() {
        const form = document.getElementById('uploadForm');
        const input = form ? form.querySelector('input[type="file"]') : null;
        const dropZone = document.getElementById('dropZone');
        const clearButton = document.getElementById('clearFileBtn');
        const submitButton = document.getElementById('submitUploadBtn');

        restoreFileInfo();

        if (!form || !input) return;

        input.addEventListener('change', function () {
            const file = input.files && input.files[0];
            if (file) setSelectedFile(file);
        });

        if (clearButton) {
            clearButton.addEventListener('click', clearFile);
        }

        if (dropZone) {
            ['dragenter', 'dragover'].forEach(function (eventName) {
                dropZone.addEventListener(eventName, function (event) {
                    event.preventDefault();
                    dropZone.classList.add('drag-over');
                });
            });

            ['dragleave', 'drop'].forEach(function (eventName) {
                dropZone.addEventListener(eventName, function (event) {
                    event.preventDefault();
                    dropZone.classList.remove('drag-over');
                });
            });

            dropZone.addEventListener('drop', function (event) {
                const file = event.dataTransfer.files && event.dataTransfer.files[0];
                if (!file) return;

                const transfer = new DataTransfer();
                transfer.items.add(file);
                input.files = transfer.files;
                setSelectedFile(file);
            });
        }

        form.addEventListener('submit', function (event) {
            const file = input.files && input.files[0];

            if (!file) {
                event.preventDefault();
                alert('Pilih file CSV dulu sebelum upload.');
                return;
            }

            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = 'Mengupload dan mengimpor data...';
            }

            const stages = [
                { percent: 18, title: 'Mengupload file...', status: 'File CSV sedang dikirim ke server Django.' },
                { percent: 42, title: 'Validasi kolom...', status: 'Sistem memeriksa kolom Date, Page path, dan Views.' },
                { percent: 68, title: 'Cleaning & mapping...', status: 'Data dibersihkan dan Page path dipetakan ke kategori berita.' },
                { percent: 90, title: 'Import database...', status: 'Data valid sedang disimpan ke database.' }
            ];

            let index = 0;
            setProgress(8, 'Menyiapkan upload...', 'Sistem sedang menyiapkan file. Jangan tutup halaman ini sampai proses selesai.');

            window.setInterval(function () {
                const stage = stages[Math.min(index, stages.length - 1)];
                setProgress(stage.percent, stage.title, stage.status);
                index += 1;
            }, 520);
        });
    }

    document.addEventListener('DOMContentLoaded', setupUploadForm);
})();
