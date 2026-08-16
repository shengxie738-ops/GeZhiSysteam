import { defineComponent, h, toRef } from 'vue';
import { useEcharts } from '../hooks/useEcharts.js';

export default defineComponent({
    name: 'RadarChart',
    props: {
        option: { type: Object, required: true }
    },
    setup(props) {
        const { containerRef } = useEcharts(toRef(props, 'option'));
        return () => h('div', { ref: containerRef, class: 'w-full h-full' });
    }
});
