import { ref, shallowRef, onMounted, onBeforeUnmount, watch, unref } from 'vue';

export function useEcharts(option) {
    const containerRef = ref(null);
    const chartInstance = shallowRef(null);
    let resizeObserver = null;

    const resizeHandler = () => {
        if (!containerRef.value || !chartInstance.value || containerRef.value.offsetWidth === 0) {
            return;
        }
        chartInstance.value.resize();
    };

    onMounted(() => {
        if (!containerRef.value) return;
        try {
            chartInstance.value = window.echarts.init(containerRef.value);
            chartInstance.value.setOption(unref(option));
        } catch (err) {
            console.error("ECharts 初始化失败：", err);
            alert("ECharts 渲染发生内部错误，请在控制台（Console）中查看完整日志。\n错误信息: " + err.message);
        }

        if (typeof ResizeObserver !== 'undefined') {
            resizeObserver = new ResizeObserver(resizeHandler);
            resizeObserver.observe(containerRef.value);
        } else {
            window.addEventListener('resize', resizeHandler);
        }
    });

    onBeforeUnmount(() => {
        if (resizeObserver && containerRef.value) {
            resizeObserver.unobserve(containerRef.value);
            resizeObserver.disconnect();
        } else {
            window.removeEventListener('resize', resizeHandler);
        }

        if (chartInstance.value) {
            chartInstance.value.dispose();
            chartInstance.value = null;
        }
    });

    watch(() => unref(option), (newOption) => {
        if (chartInstance.value && newOption) {
            try {
                chartInstance.value.setOption(newOption, { notMerge: true });
            } catch (err) {
                console.error("ECharts watch setOption 失败：", err);
            }
        }
    }, { deep: true });

    return { containerRef, chartInstance };
}
