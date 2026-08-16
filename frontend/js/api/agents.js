import request from '../utils/request.js';

export const agentApi = {
    getAgents() {
        return request('/agents');
    },

    saveAgentConfig(agentId, payload) {
        return request(`/agents/${encodeURIComponent(agentId)}`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        });
    },

    deleteAgentConfig(agentId) {
        return request(`/agents/${encodeURIComponent(agentId)}`, {
            method: 'DELETE'
        });
    }
};
