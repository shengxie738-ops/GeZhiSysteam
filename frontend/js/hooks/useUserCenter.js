import { ref, reactive } from 'vue';

import { userApi } from '../api/userApi.js';

export function useUserCenter(currentUser, showToast) {
    // ==================== 状态 ====================
    const showUserCenter = ref(false);
    const activeTab = ref('info');  // 'info' | 'password'
    const isLoading = ref(false);

    // 头像预览 URL（本地 blob 或后端 URL）
    const avatarPreviewUrl = ref('');

    // 基本信息表单
    const infoForm = reactive({
        real_name: '',
        student_id: '',
        class_name: ''
    });

    // 密码表单
    const pwdForm = reactive({
        old_password: '',
        new_password: '',
        confirm_password: ''
    });

    const isSaveSuccess = ref(false);
    const isPwdSuccess = ref(false);

    // ==================== 工具 ====================
    const getUsername = () => currentUser.value?.username || '';
    const getDisplayAvatarUrl = (avatarUrl) => avatarUrl ? userApi.getAvatarUrl(avatarUrl) : '';
    const syncCurrentUser = (user, avatarUrl = undefined) => {
        if (!user || !currentUser.value) return;
        const nextUser = { ...user };
        if (Object.prototype.hasOwnProperty.call(user, 'avatar_url')) {
            nextUser.avatar_url = avatarUrl ?? getDisplayAvatarUrl(user.avatar_url);
        }
        Object.assign(currentUser.value, nextUser);
    };

    // ==================== 获取用户信息 ====================
    const fetchUserInfo = async () => {
        const username = getUsername();
        if (!username) return;
        try {
            const data = await userApi.getUserInfo(username);
            infoForm.real_name = data.real_name || '';
            infoForm.student_id = data.student_id || '';
            infoForm.class_name = data.class_name || '';
            const avatarUrl = getDisplayAvatarUrl(data.avatar_url);
            avatarPreviewUrl.value = avatarUrl;
            syncCurrentUser(data, avatarUrl);
        } catch (e) {
            console.error('获取用户信息失败:', e);
        }
    };

    // ==================== 打开/关闭弹窗 ====================
    const openUserCenter = async () => {
        activeTab.value = 'info';
        pwdForm.old_password = '';
        pwdForm.new_password = '';
        pwdForm.confirm_password = '';
        await fetchUserInfo();
        showUserCenter.value = true;
    };

    const closeUserCenter = () => {
        showUserCenter.value = false;
    };

    // ==================== 保存基本信息 ====================
    const saveUserInfo = async () => {
        const username = getUsername();
        if (!username) return;
        isLoading.value = true;
        try {
            const data = await userApi.updateUserInfo({
                username,
                real_name: infoForm.real_name,
                student_id: infoForm.student_id,
                class_name: infoForm.class_name
            });
            if (data.status === 'success') {
                showToast('个人信息已保存！', 'success');
                isSaveSuccess.value = true;
                setTimeout(() => {
                    isSaveSuccess.value = false;
                }, 2500);
                const savedUser = data.user || {
                    username,
                    real_name: infoForm.real_name,
                    student_id: infoForm.student_id,
                    class_name: infoForm.class_name,
                    avatar_url: currentUser.value?.avatar_url || ''
                };
                const avatarUrl = getDisplayAvatarUrl(savedUser.avatar_url);
                avatarPreviewUrl.value = avatarUrl;
                syncCurrentUser(savedUser, avatarUrl);
            } else {
                showToast(data.detail || '保存失败', 'error');
            }
        } catch (e) {
            showToast('网络错误，请稍后重试', 'error');
        } finally {
            isLoading.value = false;
        }
    };

    // ==================== 修改密码 ====================
    const changePassword = async () => {
        if (!pwdForm.new_password || !pwdForm.confirm_password) {
            showToast('请填写完整的密码信息', 'error');
            return;
        }
        if (pwdForm.new_password !== pwdForm.confirm_password) {
            showToast('两次输入的新密码不一致', 'error');
            return;
        }
        if (pwdForm.new_password.length < 6) {
            showToast('新密码长度不能少于6位', 'error');
            return;
        }
        const username = getUsername();
        isLoading.value = true;
        try {
            const data = await userApi.changePassword({
                username,
                old_password: pwdForm.old_password,
                new_password: pwdForm.new_password
            });
            if (data.status === 'success') {
                showToast('密码修改成功！', 'success');
                isPwdSuccess.value = true;
                setTimeout(() => {
                    isPwdSuccess.value = false;
                }, 2500);
                pwdForm.old_password = '';
                pwdForm.new_password = '';
                pwdForm.confirm_password = '';
            } else {
                showToast(data.detail || '密码修改失败', 'error');
            }
        } catch (e) {
            showToast('网络错误，请稍后重试', 'error');
        } finally {
            isLoading.value = false;
        }
    };

    // ==================== 上传头像 ====================
    const handleAvatarUpload = async (event) => {
        const file = event.target.files?.[0];
        if (!file) return;

        // 本地预览（异步，不阻塞上传）
        const reader = new FileReader();
        reader.onload = (e) => {
            avatarPreviewUrl.value = e.target.result;
        };
        reader.readAsDataURL(file);

        const username = getUsername();
        const formData = new FormData();
        formData.append('username', username);
        formData.append('file', file);

        isLoading.value = true;
        try {
            const data = await userApi.uploadAvatar(formData);
            if (data.status === 'success') {
                const savedUser = data.user || { username, avatar_url: data.avatar_url };
                const newUrl = getDisplayAvatarUrl(savedUser.avatar_url || data.avatar_url);
                avatarPreviewUrl.value = newUrl;
                syncCurrentUser({ ...savedUser, avatar_url: savedUser.avatar_url || data.avatar_url }, newUrl);
                showToast('头像上传成功！', 'success');
            } else {
                showToast(data.detail || '头像上传失败', 'error');
                // 上传失败时清空本地预览（若已有旧头像则恢复）
                await fetchUserInfo();
            }
        } catch (e) {
            showToast('网络错误，请稍后重试', 'error');
            await fetchUserInfo();
        } finally {
            isLoading.value = false;
            // 重置 input 以便下次选同一文件仍能触发 change 事件
            event.target.value = '';
        }
    };

    // 触发隐藏的文件选择器
    const triggerAvatarInput = () => {
        document.getElementById('avatar-file-input')?.click();
    };

    return {
        showUserCenter,
        activeTab,
        isLoading,
        avatarPreviewUrl,
        infoForm,
        pwdForm,
        isSaveSuccess,
        isPwdSuccess,
        openUserCenter,
        closeUserCenter,
        saveUserInfo,
        changePassword,
        handleAvatarUpload,
        triggerAvatarInput,
        fetchUserInfo
    };
}
