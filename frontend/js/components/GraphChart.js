import { defineComponent, h, watch, toRef } from 'vue';
import { useEcharts } from '../hooks/useEcharts.js';

export default defineComponent({
    name: 'GraphChart',
    props: {
        option: { type: Object, required: true }
    },
    emits: ['node-click'],
    setup(props, { emit }) {
        const { containerRef, chartInstance } = useEcharts(toRef(props, 'option'));

        watch(chartInstance, (newVal) => {
            if (newVal) {
                newVal.on('click', (params) => {
                    if (params.dataType === 'node') {
                        emit('node-click', params.data.raw);
                    }
                });
            }
        });

        return () => h('div', { ref: containerRef, class: 'flex-1 w-full min-h-[500px]' });
    }
});
