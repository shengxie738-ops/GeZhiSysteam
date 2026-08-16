import request from '../utils/request.js';
import { toBackendAssetUrl } from '../config/env.js';

export const userApi = {
    getUserInfo: (username) => request(`/user/info/${encodeURIComponent(username)}`),
    
    updateUserInfo: (data) => request(`/user/update_info`, {
        method: 'POST',
        body: JSON.stringify(data)
    }),
    
    changePassword: (data) => request(`/user/change_password`, {
        method: 'POST',
        body: JSON.stringify(data)
    }),
    
    uploadAvatar: (formData) => request(`/user/upload_avatar`, {
        method: 'POST',
        body: formData
    }),
    
    uploadFile: (formData) => request(`/user/upload`, {
        method: 'POST',
        body: formData
    }),
    
    getAvatarUrl: (path) => {
        const url = toBackendAssetUrl(path);
        if (!url) return '';
        return `${url}${url.includes('?') ? '&' : '?'}t=${Date.now()}`;
    }
};
