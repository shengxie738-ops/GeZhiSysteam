import { defineComponent, h, watch, toRef } from 'vue';
import { useEcharts } from '../hooks/useEcharts.js';

export default defineComponent({
    name: 'TreeChart',
    props: {
        option: { type: Object, required: true }
    },
    emits: ['node-click'],
    setup(props, { emit }) {
        const { containerRef, chartInstance } = useEcharts(toRef(props, 'option'));

        watch(chartInstance, (newVal) => {
            if (newVal) {
                // 清理旧事件，避免重复绑定
                newVal.off('click');
                newVal.on('click', (params) => {
                    // Tree 图节点点击事件，此时 params.data 是被点击节点的数据对象
                    if (params.componentType === 'series' && params.data) {
                        emit('node-click', params.data);
                    }
                });
            }
        });

        return () => h('div', { ref: containerRef, class: 'flex-1 w-full min-h-[550px]' });
    }
});
