import { apiRequest, request } from '../utils/request.js';

const json = (body) => ({
    method: 'POST',
    body: JSON.stringify(body)
});

const buildQuery = (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            query.set(key, String(value));
        }
    });
    const value = query.toString();
    return value ? `?${value}` : '';
};

export const teacherLessonPrepApi = {
    getConfig() {
        return apiRequest('/teacher/lesson-prep/config');
    },
    listResources(params = {}) {
        return apiRequest(`/teacher/lesson-prep/resources${buildQuery(params)}`);
    },
    search(payload) {
        return apiRequest('/teacher/lesson-prep/search', json(payload));
    },
    summarize(payload) {
        return apiRequest('/teacher/lesson-prep/summarize', json(payload));
    },
    generate(payload) {
        return apiRequest('/teacher/lesson-prep/generate', json(payload));
    },
    saveDraft(payload) {
        return apiRequest('/teacher/lesson-prep/drafts', json(payload));
    },
    listDrafts() {
        return apiRequest('/teacher/lesson-prep/drafts');
    },
    // 导出 docx 返回二进制流：isStream 时 request 直接返回原始 Response，
    // 不能走 apiRequest 的 {code,data} JSON 解包，故此处直连 request
    async exportDocx(payload) {
        const response = await request('/teacher/lesson-prep/export-docx', { ...json(payload), isStream: true });
        if (!response.ok) {
            let message = `导出失败（HTTP ${response.status}）`;
            try {
                const text = await response.clone().text();
                const parsed = text ? JSON.parse(text) : null;
                message = parsed?.detail || parsed?.message || message;
            } catch (_) { /* 保留默认 message */ }
            throw new Error(message);
        }
        // 解析服务端文件名（优先 filename*=UTF-8''，其次 filename="..."，兜底 lesson-plan.docx）
        const disposition = response.headers.get('Content-Disposition') || '';
        let filename = 'lesson-plan.docx';
        const star = /filename\*=(?:UTF-8'')?([^;]+)/i.exec(disposition);
        if (star) { try { filename = decodeURIComponent(star[1].trim().replace(/^"|"$/g, '')); } catch (_) {} }
        else {
            const plain = /filename="?([^";]+)"?/i.exec(disposition);
            if (plain) filename = plain[1].trim();
        }
        const blob = await response.blob();
        return { blob, filename };
    }
};

export default teacherLessonPrepApi;
