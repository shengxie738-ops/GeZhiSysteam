import { ref, watch } from 'vue';
import { profileApi } from '../api/profileApi.js';

export function useProfile(currentUser, showToast) {
    const profile = ref({
        user_id: '',
        knowledge: 50,
        cognitive: "渐进理解型",
        pace: 50,
        error_pattern: "易错点：数组越界，指针空悬",
        goal: "掌握核心数据结构与算法",
        background: "电子信息与计算机类"
    });

    const fetchProfile = async () => {
        const username = currentUser.value?.username;
        if (!username) return;
        try {
            const data = await profileApi.getProfile(username);
            if (data) {
                profile.value = data;
            }
        } catch (e) {
            console.error("获取学生画像失败:", e);
        }
    };

    const updateProfile = async (updatedFields) => {
        const username = currentUser.value?.username;
        if (!username) return;
        try {
            const data = await profileApi.updateProfile({ user_id: username, ...updatedFields });
            if (data && data.status === 'success') {
                profile.value = data.profile;
                showToast("学情画像已同步更新！", "success");
            }
        } catch (e) {
            console.error("更新学生画像失败:", e);
        }
    };

    // 监听当前用户，登录后立刻获取画像
    watch(currentUser, (newVal) => {
        if (newVal) {
            fetchProfile();
        }
    }, { immediate: true });

    return {
        profile,
        fetchProfile,
        updateProfile
    };
}
