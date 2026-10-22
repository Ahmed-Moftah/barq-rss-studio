// ==========================================================================
// BARQ Editorial RSS Studio - Interactive Client Controller
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    initModals();
    initCopyButtons();
    initChatGPTImporter();
    initLivePreview();
    initPublishAction();
});

// Modals Controller
function initModals() {
    const triggers = document.querySelectorAll('[data-modal-target]');
    triggers.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = btn.getAttribute('data-modal-target');
            const modal = document.getElementById(targetId);
            if (modal) modal.classList.add('active');
        });
    });

    const closeBtns = document.querySelectorAll('[data-modal-close]');
    closeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const modal = btn.closest('.modal-overlay');
            if (modal) modal.classList.remove('active');
        });
    });

    // Close on backdrop click
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });
}

// Copy to Clipboard
function initCopyButtons() {
    document.querySelectorAll('.btn-copy, [data-copy]').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const textToCopy = btn.getAttribute('data-copy') || btn.previousElementSibling?.textContent;
            if (!textToCopy) return;

            try {
                await navigator.clipboard.writeText(textToCopy.trim());
                const originalHtml = btn.innerHTML;
                btn.innerHTML = '<span>تم النسخ ✓</span>';
                btn.style.color = '#34d399';
                setTimeout(() => {
                    btn.innerHTML = originalHtml;
                    btn.style.color = '';
                }, 2000);
            } catch (err) {
                alert('فشل نسخ النص تلقائياً، يرجى نسخه يدوياً.');
            }
        });
    });
}

// ChatGPT Smart Import
function initChatGPTImporter() {
    const importBtn = document.getElementById('btn-parse-chatgpt');
    const importTextarea = document.getElementById('chatgpt-raw-input');
    
    if (!importBtn || !importTextarea) return;

    importBtn.addEventListener('click', async () => {
        const text = importTextarea.value.trim();
        if (!text) {
            alert('يرجى لصق نص التقرير الصادر من ChatGPT أولاً');
            return;
        }

        importBtn.disabled = true;
        const originalText = importBtn.innerHTML;
        importBtn.innerHTML = '<span>جاري التحليل والمعالجة...</span>';

        try {
            const resp = await fetch('/api/parse-chatgpt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });

            const res = await resp.json();
            if (res.success && res.data) {
                const data = res.data;
                
                // Populate Form Fields
                const titleField = document.getElementById('field-title');
                const catField = document.getElementById('field-category');
                const summaryField = document.getElementById('field-summary');
                const contentField = document.getElementById('field-content');
                const tagsField = document.getElementById('field-tags');
                const authorField = document.getElementById('field-author');
                const sourceField = document.getElementById('field-source');

                if (titleField && data.title) titleField.value = data.title;
                if (catField && data.category) catField.value = data.category;
                if (summaryField && data.summary) summaryField.value = data.summary;
                if (contentField && data.content) contentField.value = data.content;
                if (tagsField && data.tags) tagsField.value = data.tags;
                if (authorField && data.author) authorField.value = data.author;
                if (sourceField && data.source) sourceField.value = data.source;

                // Close Modal
                const modal = importBtn.closest('.modal-overlay');
                if (modal) modal.classList.remove('active');

                // Trigger live preview update if active
                if (typeof updateLivePreview === 'function') {
                    updateLivePreview();
                }

                alert('تم استيراد وتحليل التقرير بنجاح وتعبئة بيانات المحرر!');
            }
        } catch (err) {
            alert('حدث خطأ أثناء تحليل النص، يرجى مراجعة الصياغة يدوياً.');
        } finally {
            importBtn.disabled = false;
            importBtn.innerHTML = originalText;
        }
    });
}

// Live Markdown Preview Toggle
function initLivePreview() {
    const contentField = document.getElementById('field-content');
    const previewContainer = document.getElementById('content-preview-container');
    const toggleBtn = document.getElementById('btn-toggle-preview');

    if (!contentField || !previewContainer || !toggleBtn) return;

    window.updateLivePreview = () => {
        const raw = contentField.value;
        // Simple client markdown renderer for live feedback
        let html = raw
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
            .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/gim, '<em>$1</em>')
            .replace(/\[(.*?)\]\((.*?)\)/gim, '<a href="$2" target="_blank">$1</a>')
            .replace(/\n\n/gim, '</p><p>')
            .replace(/^\* (.*$)/gim, '<li>$1</li>');

        previewContainer.innerHTML = `<p>${html}</p>`;
    };

    contentField.addEventListener('input', window.updateLivePreview);

    toggleBtn.addEventListener('click', () => {
        const isHidden = previewContainer.style.display === 'none';
        if (isHidden) {
            window.updateLivePreview();
            previewContainer.style.display = 'block';
            toggleBtn.innerHTML = '<span>إخفاء المعاينة</span> 👁️';
        } else {
            previewContainer.style.display = 'none';
            toggleBtn.innerHTML = '<span>معاينة حية</span> 👁️';
        }
    });
}

// Automated GitHub Publish Handler
function initPublishAction() {
    const publishBtns = document.querySelectorAll('.btn-trigger-publish');
    publishBtns.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const commitMessage = prompt('أدخل رسالة التحديث أو اضغط موافق للنشر التلقائي:', 'تحديث خلاصات RSS والتقارير التحريرية');
            if (commitMessage === null) return; // user cancelled

            btn.disabled = true;
            const originalText = btn.innerHTML;
            btn.innerHTML = '<span>جاري التوليد والنشر... ⏳</span>';

            try {
                const resp = await fetch('/api/publish', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ commit_message: commitMessage })
                });
                const res = await resp.json();

                if (res.success) {
                    alert(`✓ اكتملت عملية التوليد والتصدير بنجاح!\n\n${res.message || 'تم تحديث ملفات خلاصات RSS وموقع GitHub Pages.'}`);
                    window.location.reload();
                } else {
                    alert(`تنبيه: ${res.message || 'حدث خطأ أثناء النشر.'}`);
                }
            } catch (err) {
                alert('فشل الاتصال بالخادم أثناء النشر.');
            } finally {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        });
    });
}
