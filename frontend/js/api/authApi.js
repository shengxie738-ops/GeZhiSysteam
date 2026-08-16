/**
 * 认证相关的 API 接口（Vue 前端使用）
 * 后期对接后端真实接口
 */

const API_BASE_URL = '/api';

export const authApi = {
    /**
     * 退出登录接口
     */
    logout: async () => {
        // 模拟 API 调用
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve({ success: true, message: '退出成功' });
            }, 300);
        });
    },

    /**
     * 获取当前用户信息（可用于刷新令牌或校验会话）
     */
    getCurrentUser: async () => {
        // 模拟 API 调用
        return new Promise((resolve) => {
            setTimeout(() => {
                const user = localStorage.getItem('currentUser');
                if (user) {
                    resolve({ success: true, data: JSON.parse(user) });
                } else {
                    resolve({ success: false, message: '未登录' });
                }
            }, 300);
        });
    }
};
