import { apiRequest } from '../utils/request.js';

const json = (method, body) => ({ method, body: JSON.stringify(body) });

export const learningDiagnosisApi = {
    getLatestSession(studentId) {
        return apiRequest(`/learning-diagnosis/latest?student_id=${encodeURIComponent(studentId)}`);
    },
    createSession(payload = {}) {
        return apiRequest('/learning-diagnosis/sessions', json('POST', {
            weekly_minutes: 180,
            include_git_evidence: false,
            ...payload
        }));
    },
    updateGoal(sessionId, payload = {}) {
        return apiRequest(`/learning-diagnosis/sessions/${encodeURIComponent(sessionId)}/goals`, json('POST', payload));
    },
    toggleGitEvidence(sessionId, studentId, enabled) {
        return apiRequest(`/learning-diagnosis/sessions/${encodeURIComponent(sessionId)}/refresh?student_id=${encodeURIComponent(studentId)}`, json('POST', {
            trigger: { trigger_type: 'GIT_EVIDENCE_TOGGLE', include_git_evidence: Boolean(enabled) }
        }));
    },
    getSession(sessionId, studentId) {
        return apiRequest(`/learning-diagnosis/sessions/${sessionId}?student_id=${encodeURIComponent(studentId)}`);
    },
    refreshSession(sessionId, studentId, trigger = {}) {
        return apiRequest(`/learning-diagnosis/sessions/${sessionId}/refresh?student_id=${encodeURIComponent(studentId)}`, json('POST', { trigger }));
    },
    getPath(sessionId, studentId) {
        return apiRequest(`/learning-diagnosis/sessions/${sessionId}/path?student_id=${encodeURIComponent(studentId)}`);
    },
    requestHint(taskId, sessionId, studentId, requestedLevel, assessmentMode = false, attempt = {}) {
        return apiRequest(`/learning-diagnosis/tasks/${taskId}/hints?session_id=${encodeURIComponent(sessionId)}&student_id=${encodeURIComponent(studentId)}`, json('POST', {
            requested_level: requestedLevel,
            assessment_mode: assessmentMode,
            attempt
        }));
    },
    runTask(taskId, payload) {
        return apiRequest(`/learning-diagnosis/tasks/${taskId}/run`, json('POST', payload));
    },
    submitTask(taskId, payload) {
        return apiRequest(`/learning-diagnosis/tasks/${taskId}/submit`, json('POST', payload));
    },
    getSnapshot(snapshotId, studentId) {
        return apiRequest(`/learning-diagnosis/snapshots/${snapshotId}?student_id=${encodeURIComponent(studentId)}`);
    }
};

export default learningDiagnosisApi;
