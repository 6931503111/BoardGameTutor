/* PDF scans are rendered and recognized locally; only libraries/language models are downloaded. */
(function () {
    'use strict';
    const PDF_BASE = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@6.5.438/build';
    const OCR_BASE = 'https://cdn.jsdelivr.net/npm/tesseract.js@7.0.0/dist';
    let libraries;

    function loadLibraries() {
        if (!libraries) {
            const script = new Promise((resolve, reject) => {
                if (window.Tesseract) return resolve(window.Tesseract);
                const element = document.createElement('script');
                element.src = OCR_BASE + '/tesseract.min.js';
                element.onload = () => resolve(window.Tesseract);
                element.onerror = () => { element.remove(); reject(new Error('โหลดเครื่องมือ OCR ไม่สำเร็จ ตรวจการเชื่อมต่ออินเทอร์เน็ตแล้วลองใหม่')); };
                document.head.appendChild(element);
            });
            libraries = Promise.all([import(PDF_BASE + '/pdf.min.mjs'), script]).catch(error => {
                libraries = null;
                throw error;
            });
        }
        return libraries;
    }

    window.readPdfWithOcr = async function (file, { onProgress = () => {}, signal, forceOcr = false } = {}) {
        const checkCancelled = () => {
            if (signal?.aborted) throw new DOMException('ยกเลิกการอ่าน PDF แล้ว', 'AbortError');
        };
        checkCancelled();
        if (file.size > 20 * 1024 * 1024) throw new Error('ไฟล์ PDF ต้องมีขนาดไม่เกิน 20 MB');
        onProgress('กำลังโหลดเครื่องมืออ่าน PDF และ OCR ครั้งแรกอาจใช้เวลาสักครู่...');
        const [pdfjs, tesseract] = await loadLibraries();
        checkCancelled();
        pdfjs.GlobalWorkerOptions.workerSrc = PDF_BASE + '/pdf.worker.min.mjs';
        let worker, renderTask, loadingTask, pageNumber = 0, totalPages = 0;
        const cancel = () => { renderTask?.cancel(); if (worker) void worker.terminate().catch(() => {}); };
        signal?.addEventListener('abort', cancel, { once: true });
        try {
            loadingTask = pdfjs.getDocument({ data: new Uint8Array(await file.arrayBuffer()), isEvalSupported: false });
            const pdf = await loadingTask.promise;
            checkCancelled();
            totalPages = pdf.numPages;
            if (totalPages > 40) throw new Error('OCR รองรับครั้งละไม่เกิน 40 หน้า กรุณาแบ่ง PDF แล้วอ่านทีละส่วน');
            const parts = [];
            let textLength = 0;
            for (pageNumber = 1; pageNumber <= totalPages; pageNumber++) {
                checkCancelled();
                onProgress(`กำลังอ่านหน้า ${pageNumber}/${totalPages}`);
                const page = await pdf.getPage(pageNumber);
                try {
                    const textContent = await page.getTextContent();
                    let text = textContent.items.map(item => item.str + (item.hasEOL ? '\n' : ' ')).join('').trim();
                    if (forceOcr || text.replace(/\s/g, '').length < 40) {
                        if (!worker) {
                            onProgress('กำลังโหลดข้อมูลภาษาไทยและอังกฤษสำหรับ OCR...');
                            worker = await tesseract.createWorker(['tha', 'eng'], 1, {
                                workerPath: OCR_BASE + '/worker.min.js',
                                corePath: 'https://cdn.jsdelivr.net/npm/tesseract.js-core@7.0.0',
                                logger: event => {
                                    if (event.status === 'recognizing text') onProgress(`OCR หน้า ${pageNumber}/${totalPages} — ${Math.round((event.progress || 0) * 100)}%`);
                                },
                            });
                        }
                        checkCancelled();
                        const base = page.getViewport({ scale: 1 });
                        if (!(base.width > 0 && base.height > 0)) throw new Error(`ขนาดหน้า ${pageNumber} ไม่ถูกต้อง`);
                        const viewport = page.getViewport({ scale: Math.min(3, 2600 / Math.max(base.width, base.height)) });
                        const canvas = document.createElement('canvas');
                        canvas.width = Math.ceil(viewport.width);
                        canvas.height = Math.ceil(viewport.height);
                        try {
                            renderTask = page.render({ canvasContext: canvas.getContext('2d'), viewport });
                            await renderTask.promise;
                            checkCancelled();
                            const result = await worker.recognize(canvas);
                            text = result.data.text.trim();
                        } finally {
                            renderTask = null;
                            canvas.width = canvas.height = 0;
                        }
                    }
                    checkCancelled();
                    if (text) {
                        const part = `[หน้า ${pageNumber}]\n${text}`;
                        parts.push(part);
                        textLength += part.length + 2;
                        if (textLength > 100000) throw new Error('ข้อความเกิน 100,000 ตัวอักษร กรุณาแบ่ง PDF แล้วอ่านทีละส่วน');
                    }
                } finally {
                    page.cleanup();
                }
            }
            const text = parts.join('\n\n');
            if (text.replace(/\[หน้า \d+\]/g, '').trim().length < 50) throw new Error('OCR ยังอ่านข้อความได้ไม่เพียงพอ ลองใช้ไฟล์ภาพที่ชัดขึ้น หรือวางข้อความคู่มือด้วยตนเอง');
            return text;
        } catch (error) {
            checkCancelled();
            if (error.name === 'PasswordException') throw new Error('PDF นี้มีรหัสผ่าน กรุณาปลดล็อกไฟล์ก่อนอัปโหลด');
            throw error;
        } finally {
            signal?.removeEventListener('abort', cancel);
            if (worker) await worker.terminate().catch(() => {});
            if (loadingTask) await loadingTask.destroy().catch(() => {});
        }
    };
}());
