import { apiRequest } from '../utils/request.js';

const json = (method, body) => ({ method, body: JSON.stringify(body) });

const buildQuery = (params = {}) => {
    const entries = Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== '');
    if (!entries.length) return '';
    const query = new URLSearchParams();
    for (const [key, value] of entries) {
        query.set(key, String(value));
    }
    return `?${query.toString()}`;
};

const prefix = '/teacher/learning-diagnosis';
const normalizeReviewStatus = (status) => {
    const value = String(status || 'REVIEWED').toUpperCase();
    if (value === 'FOLLOW_UP') return 'OBSERVING';
    return value;
};

export const teacherLearningDiagnosisApi = {
    listReviews(params = {}) {
        return apiRequest(`${prefix}/reviews${buildQuery(params)}`);
    },
    getSummary(params = {}) {
        return apiRequest(`${prefix}/summary${buildQuery(params)}`);
    },
    getReviewDetail(snapshotId, params = {}) {
        return apiRequest(`${prefix}/reviews/${encodeURIComponent(snapshotId)}${buildQuery(params)}`);
    },
    markReviewed(snapshotId, payload = {}) {
        const { status, comment = '', risk_level = '', ...rest } = payload;
        return apiRequest(`${prefix}/reviews/${encodeURIComponent(snapshotId)}`, json('POST', {
            ...rest,
            status: normalizeReviewStatus(status),
            comment,
            risk_level
        }));
    },
    addNote(snapshotId, payload = {}) {
        return apiRequest(`${prefix}/reviews/${encodeURIComponent(snapshotId)}/notes`, json('POST', payload));
    },
    toggleWatch(studentId, payload = {}) {
        const watched = Boolean(payload.watched ?? payload.pinned);
        const reason = payload.reason || '';
        if (!studentId) {
            return Promise.reject(new Error('studentId is required'));
        }
        if (!watched) {
            return apiRequest(`${prefix}/watch-flags/${encodeURIComponent(studentId)}`, { method: 'DELETE' });
        }
        return apiRequest(`${prefix}/watch-flags/${encodeURIComponent(studentId)}`, json('PUT', {
            pinned: true,
            reason
        }));
    },
    markFollowUp(snapshotId, payload = {}) {
        return teacherLearningDiagnosisApi.markReviewed(snapshotId, {
            ...payload,
            status: 'OBSERVING'
        });
    }
};

export default teacherLearningDiagnosisApi;
