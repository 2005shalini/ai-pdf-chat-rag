/* ==========================================
   AI PDF CHAT RAG - Frontend PDF Upload Handler
   ========================================== */

document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const browseBtn = document.getElementById('browse-btn');
    const pdfInput = document.getElementById('pdf-input');
    const previewContainer = document.querySelector('.upload-ready-preview');
    const previewName = document.querySelector('.preview-name');
    const previewMeta = document.querySelector('.preview-meta');
    const readyStatusTag = document.querySelector('.ready-status-tag');
    const sampleChips = document.querySelectorAll('.sample-chip');

    const API_URL = 'http://127.0.0.1:5000/upload';

    // Click trigger for file browse button
    if (browseBtn && pdfInput) {
        browseBtn.addEventListener('click', (e) => {
            e.preventDefault();
            pdfInput.click();
        });

        pdfInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                handleFileUpload(e.target.files[0]);
            }
        });
    }

    // Drag and Drop Zone Event Listeners
    if (dropZone) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.add('drag-active');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.remove('drag-active');
            }, false);
        });

        dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files && files[0]) {
                handleFileUpload(files[0]);
            }
        }, false);
    }

    // Sample Document Chips Click Handler
    if (sampleChips) {
        sampleChips.forEach(chip => {
            chip.addEventListener('click', (e) => {
                e.preventDefault();
                const textContent = chip.textContent.trim();
                const mockFile = new File(["dummy pdf content"], textContent, { type: "application/pdf" });
                handleFileUpload(mockFile);
            });
        });
    }

    // Core File Upload Handler connecting to Flask POST /upload
    async function handleFileUpload(file) {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            showErrorState('Invalid file format. Please select a PDF document.');
            return;
        }

        showUploadingState(file.name);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.success) {
                showSuccessState(data.filename, file.size, data.message);
            } else {
                showErrorState(data.message || 'Upload failed');
            }
        } catch (error) {
            console.error('PDF Upload Fetch Error:', error);
            showErrorState('Could not connect to Flask backend (http://127.0.0.1:5000). Ensure app.py is running.');
        }
    }

    // UI Feedback Helpers
    function showUploadingState(filename) {
        if (previewContainer) {
            previewContainer.style.display = 'flex';
            if (previewName) previewName.textContent = filename;
            if (previewMeta) previewMeta.textContent = 'Uploading to Flask backend...';
            if (readyStatusTag) {
                readyStatusTag.innerHTML = `
                    <span class="pulse-dot" style="width:8px;height:8px;background-color:var(--primary-light);"></span>
                    Uploading...
                `;
                readyStatusTag.style.color = 'var(--primary-light)';
                readyStatusTag.style.background = 'rgba(99, 102, 241, 0.15)';
                readyStatusTag.style.borderColor = 'rgba(99, 102, 241, 0.3)';
            }
        }
    }

    function showSuccessState(filename, fileSize, message) {
        if (previewContainer) {
            previewContainer.style.display = 'flex';
            if (previewName) previewName.textContent = filename;
            const sizeKB = (fileSize / 1024).toFixed(1);
            if (previewMeta) previewMeta.textContent = `${sizeKB} KB • Saved in backend/uploads/`;
            if (readyStatusTag) {
                readyStatusTag.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                        <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                    Saved to Backend
                `;
                readyStatusTag.style.color = 'var(--accent-emerald)';
                readyStatusTag.style.background = 'rgba(16, 185, 129, 0.15)';
                readyStatusTag.style.borderColor = 'rgba(16, 185, 129, 0.3)';
            }
        }
    }

    function showErrorState(message) {
        if (previewContainer) {
            previewContainer.style.display = 'flex';
            if (previewName) previewName.textContent = 'Upload Error';
            if (previewMeta) previewMeta.textContent = message;
            if (readyStatusTag) {
                readyStatusTag.innerHTML = `⚠️ Upload Failed`;
                readyStatusTag.style.color = '#ef4444';
                readyStatusTag.style.background = 'rgba(239, 68, 68, 0.15)';
                readyStatusTag.style.borderColor = 'rgba(239, 68, 68, 0.3)';
            }
        }
    }
});
