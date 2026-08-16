import { reactive } from 'vue';

export function useToast() {
    const toast = reactive({ show: false, message: '', type: 'success' });

    const showToast = (msg, type = 'success') => {
        toast.message = msg;
        toast.type = type;
        toast.show = true;
        setTimeout(() => {
            toast.show = false;
        }, 3000);
    };

    return { toast, showToast };
}
