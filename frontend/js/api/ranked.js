import request from '../utils/request.js';

export const rankedApi = {
    getDashboard(userId) {
        return request(`/ranked/student/${encodeURIComponent(userId)}/dashboard`);
    },

    getHistory(userId) {
        return request(`/ranked/student/${encodeURIComponent(userId)}/history`);
    },

    getMistakes(userId) {
        return request(`/ranked/student/${encodeURIComponent(userId)}/mistakes`);
    },

    getSeasons(userId) {
        return request(`/ranked/student/${encodeURIComponent(userId)}/seasons`);
    },

    startMatch(payload) {
        return request('/ranked/matches/start', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    submitMatch(matchId, payload) {
        return request(`/ranked/matches/${encodeURIComponent(matchId)}/submit`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    askCoach(payload) {
        return request('/ranked/coach/ask', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    analyzeMistake(mistakeId, payload) {
        return request(`/ranked/mistakes/${encodeURIComponent(mistakeId)}/ai-analysis`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    deleteMistake(mistakeId, userId) {
        const query = new URLSearchParams({ userId }).toString();
        return request(`/ranked/mistakes/${encodeURIComponent(mistakeId)}?${query}`, {
            method: 'DELETE'
        });
    }
};
