export const TEXT_MODEL_OPTIONS = [
    {
        id: 'qwen3.7-plus',
        label: 'qwen3.7-plus',
        provider: '阿里云百炼',
        baseUrl: 'https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/compatible-mode/v1',
        hint: '综合讲解'
    },
    {
        id: 'qwen3.7-max',
        label: 'qwen3.7-max',
        provider: '阿里云百炼',
        baseUrl: 'https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/compatible-mode/v1',
        hint: '复杂规划'
    },
    {
        id: 'qwen3.8-max',
        label: 'qwen3.8-max',
        provider: '阿里云百炼',
        baseUrl: 'https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/compatible-mode/v1',
        hint: '旗舰推理',
        enableThinking: true
    },
    {
        id: 'qwen3.7-flash',
        label: 'qwen3.7-flash',
        provider: '阿里云百炼',
        baseUrl: 'https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/compatible-mode/v1',
        hint: '轻量快速',
        enableThinking: true
    },
    {
        id: 'qwen3.6-plus',
        label: 'qwen3.6-plus',
        provider: '阿里云百炼',
        baseUrl: 'https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/compatible-mode/v1',
        hint: '稳定检索'
    },
    {
        id: 'qwen3.6-max-preview',
        label: 'qwen3.6-max-preview',
        provider: '阿里云百炼',
        baseUrl: 'https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/compatible-mode/v1',
        hint: '高阶推理'
    },
    {
        id: 'qwen3.5-plus',
        label: 'qwen3.5-plus',
        provider: '阿里云百炼',
        baseUrl: 'https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/compatible-mode/v1',
        hint: '日常问答'
    },
    {
        id: 'deepseek-v4-pro',
        label: 'deepseek-v4-pro',
        provider: '阿里云百炼',
        baseUrl: 'https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/compatible-mode/v1',
        hint: '深度分析'
    },
    {
        id: 'deepseek-v4-flash',
        label: 'deepseek-v4-flash',
        provider: '阿里云百炼',
        baseUrl: 'https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/compatible-mode/v1',
        hint: '极速响应',
        enableThinking: true
    },
    {
        id: 'glm-5.2',
        label: 'glm-5.2',
        provider: '阿里云百炼',
        baseUrl: 'https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/compatible-mode/v1',
        hint: '通用协作'
    },
    {
        id: 'glm-5.1',
        label: 'glm-5.1',
        provider: '阿里云百炼',
        baseUrl: 'https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/compatible-mode/v1',
        hint: '逻辑推理',
        enableThinking: true
    },
    {
        id: 'glm-4.5-air',
        label: 'glm-4.5-air',
        provider: '智谱 AI',
        baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
        hint: '轻量响应'
    },
    {
        id: 'glm-4.6v',
        label: 'glm-4.6v',
        provider: '智谱 AI',
        baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
        hint: '视觉理解'
    },
    {
        id: 'kimi-k2.7-code',
        label: 'kimi-k2.7-code',
        provider: '阿里云百炼',
        baseUrl: 'https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/compatible-mode/v1',
        hint: '代码生成'
    },
    {
        id: 'kimi-k2.6',
        label: 'kimi-k2.6',
        provider: '阿里云百炼',
        baseUrl: 'https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/compatible-mode/v1',
        hint: '长文理解',
        enableThinking: true
    }
];

export const IMAGE_MODEL_OPTIONS = [
    {
        id: 'qwen-image-2.0',
        label: 'qwen-image-2.0',
        provider: '阿里云百炼',
        baseUrl: 'https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/api/v1'
    },
    {
        id: 'qwen-image-2.0-pro',
        label: 'qwen-image-2.0-pro',
        provider: '阿里云百炼',
        baseUrl: 'https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/api/v1'
    },
    {
        id: 'qwen-image-max',
        label: 'qwen-image-max',
        provider: '阿里云百炼',
        baseUrl: 'https://ws-ormgvfkztc6f2p76.cn-beijing.maas.aliyuncs.com/api/v1'
    },
    {
        id: 'z-image-turbo',
        label: 'z-image-turbo',
        provider: '阿里云 DashScope',
        baseUrl: 'https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation'
    }
];

export const DEFAULT_AGENT_MODEL = 'qwen3.7-plus';
export const DEFAULT_IMAGE_MODEL = 'qwen-image-2.0-pro';

export function mergeModelOptions(primaryOptions = [], fallbackOptions = []) {
    const merged = new Map();
    for (const model of fallbackOptions) {
        if (model?.id) {
            merged.set(model.id, model);
        }
    }
    for (const model of primaryOptions) {
        if (model?.id) {
            merged.set(model.id, model);
        }
    }
    return Array.from(merged.values());
}

export function getTextModelLabel(modelId) {
    return TEXT_MODEL_OPTIONS.find((model) => model.id === modelId)?.label || modelId || DEFAULT_AGENT_MODEL;
}

export function getImageModelLabel(modelId) {
    return IMAGE_MODEL_OPTIONS.find((model) => model.id === modelId)?.label || modelId || DEFAULT_IMAGE_MODEL;
}
