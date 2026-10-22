// ==========================================================================
// BARQ Editorial RSS Studio - Bulk ChatGPT Import Controller
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    initBulkImporter();
});

function initBulkImporter() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const selectedFileName = document.getElementById('selected-file-name');
    const rawJsonTextarea = document.getElementById('raw-json-textarea');
    const btnParseJson = document.getElementById('btn-parse-json');
    const btnLoadSample = document.getElementById('btn-load-sample');

    const loadingSpinner = document.getElementById('loading-spinner');
    const errorBox = document.getElementById('import-error-box');
    const errorMessage = document.getElementById('import-error-message');

    const cardUpload = document.getElementById('card-upload');
    const cardPreview = document.getElementById('card-preview');
    const cardResults = document.getElementById('card-results');

    const previewTbody = document.getElementById('preview-tbody');
    const thCheckboxAll = document.getElementById('th-checkbox-all');
    const selectedCounter = document.getElementById('selected-counter');
    const btnExecuteImport = document.getElementById('btn-execute-import');
    const btnCancelPreview = document.getElementById('btn-cancel-preview');

    const btnSelectValid = document.getElementById('btn-select-valid');
    const btnSelectAll = document.getElementById('btn-select-all');
    const btnDeselectAll = document.getElementById('btn-deselect-all');
    const btnImportAnother = document.getElementById('btn-import-another');

    let currentParsedReports = [];

    // 1. Drag and Drop Handling
    if (dropZone && fileInput) {
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('dragover');
            });
        });

        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer?.files;
            if (files && files.length > 0) {
                handleFileSelected(files[0]);
            }
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files && fileInput.files.length > 0) {
                handleFileSelected(fileInput.files[0]);
            }
        });
    }

    function handleFileSelected(file) {
        if (!file) return;
        selectedFileName.style.display = 'block';
        selectedFileName.textContent = `الملف المختار: ${file.name} (${(file.size / 1024).toFixed(1)} ك.ب)`;
        
        const reader = new FileReader();
        reader.onload = (e) => {
            const content = e.target.result;
            rawJsonTextarea.value = content;
            sendForPreview({ text: content });
        };
        reader.onerror = () => {
            showError('تعذر قراءة الملف من جهازك. يرجى التأكد من صلاحيات الملف.');
        };
        reader.readAsText(file, 'utf-8');
    }

    // 2. Parse JSON Button
    if (btnParseJson) {
        btnParseJson.addEventListener('click', () => {
            const text = rawJsonTextarea.value.trim();
            if (!text) {
                showError('يرجى لصق كود JSON أو اختيار ملف أولاً.');
                return;
            }
            sendForPreview({ text });
        });
    }

    // 3. Load Sample JSON
    if (btnLoadSample) {
        btnLoadSample.addEventListener('click', async () => {
            try {
                const resp = await fetch('/api/import/template');
                const data = await resp.json();
                rawJsonTextarea.value = JSON.stringify({ reports: data.reports }, null, 2);
                sendForPreview({ text: rawJsonTextarea.value });
            } catch (err) {
                showError('تعذر تحميل النموذج التجريبي.');
            }
        });
    }

    // 4. Send Content to Server for Preview & Validation
    async function sendForPreview(payload) {
        hideError();
        loadingSpinner.style.display = 'block';
        cardPreview.style.display = 'none';
        cardResults.style.display = 'none';

        try {
            const response = await fetch('/api/import/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const res = await response.json();
            loadingSpinner.style.display = 'none';

            if (!res.success) {
                showError(res.error || 'فشلت معالجة ملف الاستيراد.');
                return;
            }

            renderPreview(res);
        } catch (err) {
            loadingSpinner.style.display = 'none';
            showError('حدث خطأ في الاتصال بالخادم أثناء تحليل الملف.');
        }
    }

    // 5. Render Preview Table & Statistics
    function renderPreview(previewData) {
        currentParsedReports = previewData.reports || [];

        document.getElementById('stat-total').textContent = previewData.total_count || 0;
        document.getElementById('stat-valid').textContent = previewData.valid_count || 0;
        document.getElementById('stat-duplicates').textContent = previewData.duplicate_count || 0;
        document.getElementById('stat-invalid').textContent = previewData.invalid_count || 0;

        previewTbody.innerHTML = '';

        currentParsedReports.forEach((item, index) => {
            const tr = document.createElement('tr');
            tr.dataset.index = index;

            const isValid = item.is_valid;
            const isDuplicate = item.is_duplicate;
            const data = item.data;
            const catMeta = item.category_meta || { name: data.category, badge_color: '#94a3b8', badge_bg: '#1e293b' };

            // Checkbox state: checked if valid and not duplicate; unchecked if duplicate; disabled if invalid
            const isChecked = isValid && !isDuplicate;
            const isDisabled = !isValid;

            // Status Badge
            let statusBadge = '';
            if (!isValid) {
                statusBadge = `<span class="badge badge-status-invalid" title="${escapeHtml(item.errors.join(' | '))}">❌ غير صالح: ${escapeHtml(item.errors[0])}</span>`;
            } else if (isDuplicate) {
                statusBadge = `<span class="badge badge-status-duplicate" title="${escapeHtml(item.duplicate_reason)}">⚠️ مكرر: ${escapeHtml(item.duplicate_reason)}</span>`;
            } else {
                statusBadge = `<span class="badge badge-status-valid">✅ جاهز (مسودة)</span>`;
            }

            // Image indicator
            const hasImage = data.image_url && data.image_url.startsWith('http');
            const imagePill = hasImage 
                ? `<span style="display: inline-block; font-size: 0.75rem; background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 0.15rem 0.5rem; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.3);" title="${escapeHtml(data.image_url)}">🖼️ صورة خارجية</span>`
                : `<span style="font-size: 0.75rem; color: #64748b;">بدون صورة</span>`;

            tr.innerHTML = `
                <td style="text-align: center;">
                    <input type="checkbox" class="report-checkbox" data-index="${index}" ${isChecked ? 'checked' : ''} ${isDisabled ? 'disabled' : ''} style="cursor: pointer; width: 16px; height: 16px;">
                </td>
                <td style="text-align: center; color: var(--text-muted); font-size: 0.85rem;">${item.index}</td>
                <td>
                    <div style="font-weight: 700; color: #ffffff; font-size: 0.95rem; margin-bottom: 0.25rem;">
                        ${escapeHtml(data.title || '(بدون عنوان)')}
                    </div>
                    <div style="font-size: 0.82rem; color: #94a3b8; max-width: 500px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        ${escapeHtml(data.summary || '')}
                    </div>
                </td>
                <td>
                    <span class="badge" style="color: ${catMeta.badge_color}; background: ${catMeta.badge_bg}; font-size: 0.82rem;">
                        ${escapeHtml(catMeta.name)}
                    </span>
                </td>
                <td>${statusBadge}</td>
                <td>
                    <div>${imagePill}</div>
                    <div style="font-size: 0.78rem; color: #94a3b8; margin-top: 0.2rem;">✍️ ${escapeHtml(data.author || 'برق')}</div>
                </td>
                <td style="text-align: center;">
                    <button type="button" class="btn btn-secondary btn-sm btn-inspect-report" data-index="${index}">
                        معاينة 👁️
                    </button>
                </td>
            `;

            previewTbody.appendChild(tr);
        });

        // Add inspect event listeners
        document.querySelectorAll('.btn-inspect-report').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const idx = parseInt(btn.dataset.index, 10);
                openInspectModal(currentParsedReports[idx]);
            });
        });

        // Add checkbox change event listeners
        document.querySelectorAll('.report-checkbox').forEach(cb => {
            cb.addEventListener('change', updateSelectionSummary);
        });

        updateSelectionSummary();
        cardPreview.style.display = 'block';
        cardPreview.scrollIntoView({ behavior: 'smooth' });
    }

    // 6. Selection Controls
    function updateSelectionSummary() {
        const checkboxes = document.querySelectorAll('.report-checkbox');
        const checked = Array.from(checkboxes).filter(cb => cb.checked && !cb.disabled);
        const totalValid = Array.from(checkboxes).filter(cb => !cb.disabled).length;

        selectedCounter.textContent = `تم تحديد ${checked.length} من إجمالي ${checkboxes.length} تقرير`;
        btnExecuteImport.disabled = checked.length === 0;
        btnExecuteImport.innerHTML = `<span>استيراد التقارير المحددة (${checked.length}) كمسودات</span> 📥`;

        if (thCheckboxAll) {
            thCheckboxAll.checked = checked.length > 0 && checked.length === totalValid;
        }
    }

    if (thCheckboxAll) {
        thCheckboxAll.addEventListener('change', () => {
            const isChecked = thCheckboxAll.checked;
            document.querySelectorAll('.report-checkbox').forEach(cb => {
                if (!cb.disabled) {
                    cb.checked = isChecked;
                }
            });
            updateSelectionSummary();
        });
    }

    if (btnSelectValid) {
        btnSelectValid.addEventListener('click', () => {
            document.querySelectorAll('.report-checkbox').forEach(cb => {
                const idx = parseInt(cb.dataset.index, 10);
                const item = currentParsedReports[idx];
                if (!cb.disabled) {
                    cb.checked = item && item.is_valid && !item.is_duplicate;
                }
            });
            updateSelectionSummary();
        });
    }

    if (btnSelectAll) {
        btnSelectAll.addEventListener('click', () => {
            document.querySelectorAll('.report-checkbox').forEach(cb => {
                if (!cb.disabled) {
                    cb.checked = true;
                }
            });
            updateSelectionSummary();
        });
    }

    if (btnDeselectAll) {
        btnDeselectAll.addEventListener('click', () => {
            document.querySelectorAll('.report-checkbox').forEach(cb => {
                cb.checked = false;
            });
            updateSelectionSummary();
        });
    }

    if (btnCancelPreview) {
        btnCancelPreview.addEventListener('click', () => {
            cardPreview.style.display = 'none';
            rawJsonTextarea.value = '';
            fileInput.value = '';
            selectedFileName.style.display = 'none';
            currentParsedReports = [];
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // 7. Execute Import of Selected Reports
    if (btnExecuteImport) {
        btnExecuteImport.addEventListener('click', async () => {
            const checkedBoxes = Array.from(document.querySelectorAll('.report-checkbox:checked'));
            if (checkedBoxes.length === 0) {
                alert('يرجى تحديد تقرير واحد على الأقل للاستيراد.');
                return;
            }

            const reportsToImport = checkedBoxes.map(cb => {
                const idx = parseInt(cb.dataset.index, 10);
                return currentParsedReports[idx].data;
            });

            btnExecuteImport.disabled = true;
            const originalHtml = btnExecuteImport.innerHTML;
            btnExecuteImport.innerHTML = `<span>جاري حفظ ${reportsToImport.length} تقرير كمسودات...</span>`;

            try {
                const response = await fetch('/api/import/execute', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ reports: reportsToImport })
                });

                const res = await response.json();
                btnExecuteImport.disabled = false;
                btnExecuteImport.innerHTML = originalHtml;

                if (!res.success) {
                    showError(res.error || 'فشلت عملية حفظ التقارير في قاعدة البيانات.');
                    return;
                }

                // Show Results Card
                cardPreview.style.display = 'none';
                cardUpload.style.display = 'none';

                const totalInFile = currentParsedReports.length;
                const importedCount = res.imported_count || 0;
                const skippedCount = totalInFile - importedCount;
                const failedCount = res.failed_count || 0;

                document.getElementById('res-imported-count').textContent = importedCount;
                document.getElementById('res-skipped-count').textContent = skippedCount;
                document.getElementById('res-failed-count').textContent = failedCount;

                cardResults.style.display = 'block';
                cardResults.scrollIntoView({ behavior: 'smooth' });
            } catch (err) {
                btnExecuteImport.disabled = false;
                btnExecuteImport.innerHTML = originalHtml;
                showError('حدث خطأ أثناء الاتصال بالخادم لحفظ التقارير.');
            }
        });
    }

    if (btnImportAnother) {
        btnImportAnother.addEventListener('click', () => {
            cardResults.style.display = 'none';
            cardUpload.style.display = 'block';
            rawJsonTextarea.value = '';
            fileInput.value = '';
            selectedFileName.style.display = 'none';
            currentParsedReports = [];
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // 8. Inspect Modal Detail Popup
    function openInspectModal(reportItem) {
        if (!reportItem) return;
        const data = reportItem.data;
        const catMeta = reportItem.category_meta || {};

        document.getElementById('inspect-modal-title').textContent = data.title || 'بدون عنوان';
        
        const metaBox = document.getElementById('inspect-modal-meta');
        metaBox.innerHTML = `
            <span class="badge" style="color: ${catMeta.badge_color || '#94a3b8'}; background: ${catMeta.badge_bg || '#1e293b'};">القسم: ${catMeta.name || data.category}</span>
            <span class="badge badge-draft">الحالة: مسودة (Draft)</span>
            <span class="badge" style="background: rgba(255,255,255,0.08); color: #cbd5e1;">الكاتب: ${escapeHtml(data.author || 'فريق تحرير برق')}</span>
            <span class="badge" style="background: rgba(255,255,255,0.08); color: #cbd5e1;">المصدر: ${escapeHtml(data.source || 'ChatGPT')}</span>
            <span class="badge" style="background: rgba(255,255,255,0.08); color: #cbd5e1;">الرابط المقترح: /articles/${escapeHtml(data.slug || '')}.html</span>
        `;

        document.getElementById('inspect-modal-summary').textContent = data.summary || 'لا يوجد موجز مخصص.';
        document.getElementById('inspect-modal-content').textContent = data.content || '';

        const imageBox = document.getElementById('inspect-modal-image-box');
        if (data.image_url && data.image_url.startsWith('http')) {
            imageBox.style.display = 'block';
            const img = document.getElementById('inspect-modal-image');
            img.src = data.image_url;
            img.onerror = () => { img.style.display = 'none'; };
            img.onload = () => { img.style.display = 'block'; };

            const imgLink = document.getElementById('inspect-modal-image-link');
            imgLink.href = data.image_url;
            imgLink.textContent = data.image_url;

            document.getElementById('inspect-modal-image-caption').textContent = data.image_caption || 'بدون شرح للصورة';
        } else {
            imageBox.style.display = 'none';
        }

        const modal = document.getElementById('modal-report-inspect');
        if (modal) modal.classList.add('active');
    }

    function showError(msg) {
        if (errorBox && errorMessage) {
            errorMessage.textContent = msg;
            errorBox.style.display = 'flex';
            errorBox.scrollIntoView({ behavior: 'smooth' });
        } else {
            alert(msg);
        }
    }

    function hideError() {
        if (errorBox) errorBox.style.display = 'none';
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}
