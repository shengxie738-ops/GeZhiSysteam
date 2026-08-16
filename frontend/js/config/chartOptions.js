export function getNodeSize(status) {
    if (status === 'doing') return 34;
    return 28;
}

export function buildGraphOption(nodesData, linksData) {
    const repulsionBase = Math.max(250, nodesData.length * 80);

    const chartNodes = nodesData.map(node => {
        let itemStyle = {};
        if (node.value === 'done') {
            itemStyle = { color: '#10B981', borderColor: '#A7F3D0', borderWidth: 4, shadowColor: 'rgba(16, 185, 129, 0.2)', shadowBlur: 10 };
        } else if (node.value === 'doing') {
            itemStyle = { color: '#3B82F6', borderColor: '#93C5FD', borderWidth: 6, shadowColor: 'rgba(59, 130, 246, 0.6)', shadowBlur: 15 };
        } else {
            itemStyle = { color: '#E2E8F0', borderColor: '#CBD5E1', borderWidth: 2, shadowBlur: 0 };
        }

        return {
            name: node.name,
            symbolSize: getNodeSize(node.value),
            itemStyle: itemStyle,
            raw: node
        };
    });

    return {
        animationDurationUpdate: 1500,
        tooltip: { show: true, formatter: '{b}' },
        series: [{
            type: 'graph',
            layout: 'force',
            force: {
                repulsion: repulsionBase,
                edgeLength: [80, 150],
                gravity: 0.1,
                layoutAnimation: true
            },
            roam: true,
            draggable: true,
            label: { show: true, position: 'bottom', color: '#334155', fontWeight: 600, fontSize: 12, distance: 8 },
            edgeSymbol: ['none', 'arrow'],
            edgeSymbolSize: [4, 8],
            data: chartNodes,
            links: linksData,
            lineStyle: { opacity: 0.9, curveness: 0.15 },
            emphasis: { scale: true, focus: 'adjacency', lineStyle: { width: 5 } }
        }]
    };
}

export const radarOptionTemplate = {
    color: ['#1c2b38', '#3B82F6'],
    tooltip: { trigger: 'item' },
    legend: {
        data: ['您的当前学情', '全班平均表现'],
        bottom: 4,
        itemWidth: 10,
        itemHeight: 10,
        itemGap: 16,
        textStyle: { color: '#64748B', fontSize: 11 }
    },
    radar: {
        center: ['50%', '44%'],
        radius: '58%',
        indicator: [
            { name: '规划一致性', max: 100 },
            { name: '代码质量与工程', max: 100 },
            { name: '理论逻辑完备度', max: 100 },
            { name: '学术论坛活跃度', max: 100 },
            { name: '专注度均值', max: 100 },
            { name: 'Checkpoint完成率', max: 100 }
        ],
        nameGap: 18,
        splitNumber: 4,
        axisName: {
            color: '#475569',
            fontFamily: 'sans-serif',
            fontWeight: 600,
            fontSize: 11,
            padding: [2, 4]
        },
        splitArea: { areaStyle: { color: ['rgba(241, 245, 249, 0.3)', 'rgba(241, 245, 249, 0.7)'] } },
        splitLine: { lineStyle: { color: 'rgba(226, 232, 240, 0.8)' } },
        axisLine: { lineStyle: { color: 'rgba(226, 232, 240, 0.8)' } }
    },
    series: [{
        name: '能力维度对比',
        type: 'radar',
        symbol: 'circle',
        symbolSize: 7,
        data: [
            { value: [60, 55, 58, 20, 65, 40], name: '您的当前学情', areaStyle: { color: 'rgba(28, 43, 56, 0.18)' }, lineStyle: { width: 2, color: '#1c2b38' }, itemStyle: { borderWidth: 2, color: '#1c2b38' } },
            { value: [68, 62, 70, 35, 72, 55], name: '全班平均表现', areaStyle: { color: 'rgba(59, 130, 246, 0.08)' }, lineStyle: { width: 2, color: '#3B82F6' }, itemStyle: { borderWidth: 2, color: '#3B82F6' } }
        ]
    }]
};

// Lazily build lineOptionTemplate so we don't crash if echarts hasn't loaded yet
function makeGradient(r, g, b) {
    if (window.echarts && window.echarts.graphic) {
        return new window.echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: `rgba(${r}, ${g}, ${b}, 0.3)` },
            { offset: 1, color: `rgba(${r}, ${g}, ${b}, 0)` }
        ]);
    }
    return `rgba(${r}, ${g}, ${b}, 0.15)`;
}

export function getLineOptionTemplate() {
    return {
        color: ['#8B5CF6', '#3B82F6', '#10B981'],
        tooltip: { trigger: 'axis', backgroundColor: 'rgba(255, 255, 255, 0.9)', borderColor: '#e2e8f0', borderWidth: 1, textStyle: { color: '#1e293b' } },
        legend: { data: ['Planner (规划师)', 'Tutor (导师)', 'CodeNinja (代码精灵)'], bottom: 0, textStyle: { color: '#64748B' } },
        grid: { left: '3%', right: '4%', bottom: '10%', top: '5%', containLabel: true },
        xAxis: { type: 'category', boundaryGap: false, data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'], axisLine: { lineStyle: { color: '#cbd5e1' } }, axisLabel: { color: '#64748B' } },
        yAxis: { type: 'value', axisLine: { lineStyle: { color: '#cbd5e1' } }, splitLine: { lineStyle: { color: '#f1f5f9' } }, axisLabel: { color: '#64748B' } },
        series: [
            { name: 'Planner (规划师)', type: 'line', smooth: true, data: [120, 150, 180, 140, 210, 250, 310], areaStyle: { color: makeGradient(139, 92, 246) }, lineStyle: { width: 3 } },
            { name: 'Tutor (导师)', type: 'line', smooth: true, data: [220, 310, 290, 350, 420, 390, 520], areaStyle: { color: makeGradient(59, 130, 246) }, lineStyle: { width: 3 } },
            { name: 'CodeNinja (代码精灵)', type: 'line', smooth: true, data: [80, 120, 150, 190, 220, 170, 290], areaStyle: { color: makeGradient(16, 185, 129) }, lineStyle: { width: 3 } }
        ]
    };
}

function processTreeNode(node) {
    let itemStyle = {};
    let symbolSize = 16;
    
    if (node.value === 'root') {
        itemStyle = {
            color: '#6366F1',
            borderColor: '#C7D2FE',
            borderWidth: 4,
            shadowColor: 'rgba(99, 102, 241, 0.3)',
            shadowBlur: 12
        };
        symbolSize = 22;
    } else if (node.value === 'done') {
        itemStyle = {
            color: '#10B981',
            borderColor: '#A7F3D0',
            borderWidth: 3,
            shadowColor: 'rgba(16, 185, 129, 0.25)',
            shadowBlur: 10
        };
        symbolSize = 16;
    } else if (node.value === 'doing') {
        itemStyle = {
            color: '#3B82F6',
            borderColor: '#93C5FD',
            borderWidth: 5,
            shadowColor: 'rgba(59, 130, 246, 0.65)',
            shadowBlur: 16
        };
        symbolSize = 18;
    } else {
        // pending
        itemStyle = {
            color: '#FFFFFF',
            borderColor: '#CBD5E1',
            borderWidth: 2,
            shadowBlur: 0
        };
        symbolSize = 14;
    }

    const processed = {
        name: node.name,
        value: node.value,
        desc: node.desc,
        resources: node.resources,
        symbolSize: symbolSize,
        itemStyle: itemStyle
    };

    if (node.children && node.children.length > 0) {
        processed.children = node.children.map(child => processTreeNode(child));
    }

    return processed;
}

export function buildTreeOption(treeData) {
    if (!treeData) return {};
    const processedData = processTreeNode(treeData);
    
    return {
        tooltip: {
            trigger: 'item',
            triggerOn: 'mousemove',
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            borderColor: '#E2E8F0',
            borderWidth: 1,
            textStyle: { color: '#334155', fontSize: 12 },
            formatter: function (params) {
                const data = params.data;
                let statusStr = '';
                if (data.value === 'done') statusStr = '<span style="color:#10B981;font-weight:bold;margin-left:5px;">[已掌握]</span>';
                else if (data.value === 'doing') statusStr = '<span style="color:#3B82F6;font-weight:bold;margin-left:5px;">[学习中]</span>';
                else if (data.value === 'pending') statusStr = '<span style="color:#94A3B8;margin-left:5px;">[未解锁]</span>';
                
                return `<b>${params.name}</b>${statusStr}<br/><span style="display:inline-block;max-width:220px;white-space:normal;font-size:11px;color:#64748B;margin-top:4px;">${data.desc || ''}</span>`;
            }
        },
        series: [
            {
                type: 'tree',
                data: [processedData],
                top: '5%',
                left: '15%',
                bottom: '5%',
                right: '22%',
                symbol: 'circle',
                orient: 'LR',
                expandAndCollapse: true,
                initialTreeDepth: 2,
                label: {
                    position: 'left',
                    verticalAlign: 'middle',
                    align: 'right',
                    fontSize: 12,
                    color: '#334155',
                    fontWeight: 600,
                    distance: 8
                },
                leaves: {
                    label: {
                        position: 'right',
                        verticalAlign: 'middle',
                        align: 'left',
                        color: '#0F172A',
                        fontWeight: 500
                    }
                },
                lineStyle: {
                    color: 'rgba(203, 213, 225, 0.8)',
                    width: 2,
                    curveness: 0.5
                },
                emphasis: {
                    focus: 'ancestor',
                    lineStyle: {
                        width: 4,
                        color: '#6366F1'
                    }
                }
            }
        ]
    };
}

