import { ref, reactive, computed } from 'vue';
import { agents as mockAgents } from '../data/mockData.js';
import { DEFAULT_AGENT_MODEL, DEFAULT_IMAGE_MODEL, IMAGE_MODEL_OPTIONS, TEXT_MODEL_OPTIONS, mergeModelOptions } from '../config/aiModels.js';
import { agentApi } from '../api/agents.js';
import request from '../utils/request.js';

export function useAgents(showToast) {
    const agents = mockAgents;
    const textModelOptions = ref([...TEXT_MODEL_OPTIONS]);
    const imageModelOptions = ref([...IMAGE_MODEL_OPTIONS]);
    const showAgentModal = ref(false);
    const isEditingAgent = ref(false);

    const agentForm = reactive({
        id: '',
        name: '',
        role: '',
        prompt: '',
        model: DEFAULT_AGENT_MODEL,
        modelCategory: 'text',
        colorClass: 'bg-blue-500',
        icon: 'ph-robot',
        isActive: true,
        isThinking: false
    });

    const getAgentModelOptions = (agent) => {
        return agent?.modelCategory === 'image' ? imageModelOptions.value : textModelOptions.value;
    };

    const getDefaultModelForCategory = (modelCategory) => {
        return modelCategory === 'image' ? DEFAULT_IMAGE_MODEL : DEFAULT_AGENT_MODEL;
    };

    const activeAgentModelOptions = computed(() => getAgentModelOptions(agentForm));

    const normalizeBackendModel = (model) => ({
        id: model.id,
        label: model.label || model.id,
        provider: model.provider || '',
        baseUrl: model.base_url || model.baseUrl || '',
        apiModel: model.api_model || model.apiModel || '',
        hint: model.hint || ''
    });

    const loadBackendModelOptions = async () => {
        try {
            const payload = await request('/ai/models');
            const data = payload?.data || {};
            if (Array.isArray(data.text) && data.text.length) {
                textModelOptions.value = mergeModelOptions(
                    data.text.map(normalizeBackendModel),
                    TEXT_MODEL_OPTIONS
                );
            }
            if (Array.isArray(data.image) && data.image.length) {
                imageModelOptions.value = mergeModelOptions(
                    data.image.map(normalizeBackendModel),
                    IMAGE_MODEL_OPTIONS
                );
            }
        } catch (error) {
            console.info('[Agents] Backend model registry unavailable, using local model options.', error);
        }
    };

    const loadBackendAgents = async () => {
        try {
            const payload = await agentApi.getAgents();
            if (Array.isArray(payload?.data) && payload.data.length) {
                agents.value = payload.data;
            }
        } catch (error) {
            console.info('[Agents] Backend agent config unavailable, using local agents.', error);
        }
    };

    loadBackendAgents();
    loadBackendModelOptions();

    const openAgentModal = (agent = null) => {
        if (agent) {
            isEditingAgent.value = true;
            Object.assign(agentForm, {
                modelCategory: 'text',
                ...JSON.parse(JSON.stringify(agent))
            });
        } else {
            isEditingAgent.value = false;
            Object.assign(agentForm, {
                id: `agent_custom_${Date.now()}`,
                name: '',
                role: '',
                prompt: '',
                model: DEFAULT_AGENT_MODEL,
                modelCategory: 'text',
                colorClass: 'bg-blue-500',
                icon: 'ph-robot',
                isActive: true,
                isThinking: false
            });
        }
        showAgentModal.value = true;
    };

    const closeAgentModal = () => {
        showAgentModal.value = false;
    };

    const updateAgentModel = async (agent, modelId) => {
        const options = getAgentModelOptions(agent);
        if (!agent || !options.some((model) => model.id === modelId)) {
            return;
        }
        agent.model = modelId;
        try {
            await agentApi.saveAgentConfig(agent.id, agent);
        } catch (error) {
            console.info('[Agents] Failed to persist model switch, kept local state.', error);
        }
        if (showToast) {
            showToast(`Agent [${agent.name}] 已切换至 ${modelId}`, 'success');
        }
    };

    const saveAgent = async () => {
        if (!agentForm.name || !agentForm.prompt) {
            return showToast('Agent名称和核心指令不能为空', 'error');
        }
        const nextAgent = { ...agentForm };
        if (isEditingAgent.value) {
            const index = agents.value.findIndex(a => a.id === nextAgent.id);
            if (index !== -1) {
                agents.value[index] = nextAgent;
            }
            showToast(`Agent [${agentForm.name}] 配置已更新`);
        } else {
            agents.value.push(nextAgent);
            showToast(`新 Agent [${agentForm.name}] 部署成功`);
        }
        try {
            await agentApi.saveAgentConfig(nextAgent.id, nextAgent);
        } catch (error) {
            console.info('[Agents] Failed to persist agent config, kept local state.', error);
        }
        closeAgentModal();
    };

    const deleteAgent = async () => {
        if (confirm(`确定要移除节点 [${agentForm.name}] 吗？`)) {
            try {
                await agentApi.deleteAgentConfig(agentForm.id);
            } catch (error) {
                console.info('[Agents] Failed to delete backend agent config, removing locally.', error);
            }
            agents.value = agents.value.filter(a => a.id !== agentForm.id);
            showToast('Agent 节点已成功下线');
            closeAgentModal();
        }
    };

    const getAgentInfo = (id) => {
        return agents.value.find(a => a.id === id) || agents.value[0];
    };

    const getAgentInfoBySource = (source) => {
        return agents.value.find(a => a.name.toLowerCase() === (source || '').toLowerCase()) || agents.value[0];
    };

    return {
        agents,
        textModelOptions,
        imageModelOptions,
        activeAgentModelOptions,
        showAgentModal,
        isEditingAgent,
        agentForm,
        getAgentModelOptions,
        getDefaultModelForCategory,
        loadBackendAgents,
        loadBackendModelOptions,
        openAgentModal,
        closeAgentModal,
        updateAgentModel,
        saveAgent,
        deleteAgent,
        getAgentInfo,
        getAgentInfoBySource
    };
}
