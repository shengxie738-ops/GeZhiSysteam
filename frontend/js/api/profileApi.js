import request from '../utils/request.js';

export const profileApi = {
    getProfile: (username) => request(`/profile/${encodeURIComponent(username)}`),
    
    updateProfile: (data) => request(`/profile/update`, {
        method: 'POST',
        body: JSON.stringify(data)
    }),
    
    recordTest: (data) => request(`/profile/record_test`, {
        method: 'POST',
        body: JSON.stringify(data)
    }),
    
    getDiagnosisHistory: (userId) => request(`/diagnosis/history?user_id=${encodeURIComponent(userId)}`)
};
