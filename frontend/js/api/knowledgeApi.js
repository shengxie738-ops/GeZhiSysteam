import request from '../utils/request.js';

export const knowledgeApi = {
    list: (userId) => request(`/user/knowledge?user_id=${encodeURIComponent(userId)}`),

    getCourseKnowledgeBases: () => request('/knowledge/courses'),

    createRepository: ({ userId, name }) => request('/user/knowledge/repositories', {
        method: 'POST',
        body: JSON.stringify({
            user_id: userId,
            name
        })
    }),

    uploadDocument: ({ userId, repositoryId, file }) => {
        const formData = new FormData();
        formData.append('user_id', userId);
        formData.append('repository_id', repositoryId);
        formData.append('file', file);
        return request('/user/knowledge/documents', {
            method: 'POST',
            body: formData
        });
    },

    deleteDocument: ({ userId, documentId }) => request(`/user/knowledge/documents/${encodeURIComponent(documentId)}?user_id=${encodeURIComponent(userId)}`, {
        method: 'DELETE'
    }),

    deleteRepository: ({ userId, repositoryId }) => request(`/user/knowledge/repositories/${encodeURIComponent(repositoryId)}?user_id=${encodeURIComponent(userId)}`, {
        method: 'DELETE'
    })
};

export default knowledgeApi;
