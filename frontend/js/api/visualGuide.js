import request from '../utils/request.js';

const VISUAL_GUIDE_TIMEOUT_MS = 90000;

export async function requestVisualGuideImage({ prompt, guideType, sessionId, imageModel, textModel, architectureAgent }) {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), VISUAL_GUIDE_TIMEOUT_MS);

    try {
        const payload = await request('/visual-guide/generate', {
            method: 'POST',
            signal: controller.signal,
            body: JSON.stringify({
                prompt,
                guide_type: guideType,
                session_id: sessionId,
                image_model: imageModel,
                text_model: textModel,
                agent_id: architectureAgent?.id,
                agent_prompt: architectureAgent?.prompt,
                style: 'gezhi-ink-glass',
                context: {
                    mode: 'guided_learning',
                    agent: guideType === 'steps' ? 'Prof. X' : 'Mira',
                    agent_id: architectureAgent?.id,
                    agent_model: textModel,
                    agent_prompt: architectureAgent?.prompt
                }
            })
        });

        if (payload.status && payload.status !== 'success') {
            throw new Error(payload.message || 'Visual guide API returned non-success status');
        }

        return normalizeVisualGuidePayload(payload);
    } finally {
        window.clearTimeout(timer);
    }
}

export function normalizeVisualGuidePayload(payload) {
    if (!payload || typeof payload !== 'object') return null;

    const imageUrl = payload.image_url || payload.imageUrl || '';
    const rawBase64 = payload.image_base64 || payload.imageBase64 || '';
    const imageBase64 = rawBase64 && !String(rawBase64).startsWith('data:')
        ? `data:image/png;base64,${rawBase64}`
        : rawBase64;
    const rawBackgroundBase64 = payload.background_base64 || payload.backgroundBase64 || '';
    const backgroundBase64 = rawBackgroundBase64 && !String(rawBackgroundBase64).startsWith('data:')
        ? `data:image/png;base64,${rawBackgroundBase64}`
        : rawBackgroundBase64;
    const backgroundUrl = payload.background_url || payload.backgroundUrl || '';
    const svg = payload.svg || '';
    const nodes = Array.isArray(payload.nodes) ? payload.nodes : [];
    const mermaid = payload.mermaid || '';
    const treeText = payload.tree_text || payload.treeText || '';
    const diagramType = payload.diagram_type || payload.diagramType || '';

    if (!svg && !backgroundUrl && !backgroundBase64 && !imageUrl && !imageBase64 && !mermaid && !treeText && nodes.length === 0) {
        return null;
    }
    const isArchitecture = payload.provider === 'prof_x_text_architecture' || Boolean(mermaid || treeText);

    return {
        source: isArchitecture ? 'backend-architecture' : (svg || backgroundUrl || backgroundBase64 || imageUrl || imageBase64 ? 'backend' : 'backend-structure'),
        provider: payload.provider || '',
        diagramType,
        mermaid,
        treeText,
        svg,
        backgroundUrl,
        backgroundBase64,
        imageUrl,
        imageBase64,
        alt: payload.image_alt || payload.imageAlt || 'Mira 生成的学习引导图',
        caption: payload.caption || 'AI 引导图已生成',
        nodes,
        edges: Array.isArray(payload.edges) ? payload.edges : [],
        metadata: payload.metadata || {}
    };
}

export function createLocalVisualGuide(prompt, guideType) {
    const cleanPrompt = (prompt || '解释一下什么是 Transformer 架构').trim();
    const keyword = extractKeyword(cleanPrompt);
    const guideBuilders = {
        concept: () => ({
            title: `概念图：${keyword}`,
            caption: `围绕「${cleanPrompt}」拆出核心概念与关系。`,
            center: keyword,
            nodes: ['先建立定义', '拆解组成部分', '看清信息流', '迁移到例子'],
            edges: ['是什么', '由什么组成', '如何运转', '怎么应用']
        }),
        steps: () => ({
            title: `步骤图：${keyword}`,
            caption: '把问题转换为 4 个可执行学习步骤。',
            center: keyword,
            nodes: ['明确问题', '定位前置知识', '推导关键机制', '做题巩固'],
            edges: ['Step 1', 'Step 2', 'Step 3', 'Step 4']
        })
    };

    return {
        ...(guideBuilders[guideType] || guideBuilders.concept)(),
        type: guideType,
        source: 'local',
        generatedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
}

export function resolveVisualGuideState({ localGuide, backendGuide }) {
    if (backendGuide) {
        const hasArchitecture = backendGuide.provider === 'prof_x_text_architecture' || Boolean(backendGuide.mermaid || backendGuide.treeText);
        const hasSvg = Boolean(backendGuide.svg);
        const hasBackground = Boolean(backendGuide.backgroundUrl || backendGuide.backgroundBase64);
        const promptText = localGuide.caption.match(/「(.+?)」/)?.[1] || localGuide.center || localGuide.title;

        return {
            status: 'ready',
            image: backendGuide,
            guide: {
                ...localGuide,
                caption: backendGuide.caption || localGuide.caption,
                nodes: backendGuide.nodes?.length ? backendGuide.nodes : localGuide.nodes,
                edges: backendGuide.edges?.length ? backendGuide.edges : localGuide.edges,
                source: backendGuide.provider || backendGuide.source || 'backend'
            },
            historySource: backendGuide.provider || 'backend',
            logMessage: hasArchitecture
                ? `Prof. X 已为「${promptText}」生成知识结构图。`
                : hasSvg && hasBackground
                ? `已为「${promptText}」生成精准引导图，并叠加千问背景。`
                : hasSvg
                    ? `已为「${promptText}」生成精准 SVG 引导图。`
                    : `已根据「${promptText}」生成千问 AI 引导图。`
        };
    }

    if (localGuide?.type === 'steps') {
        const architectureGuide = createLocalArchitectureGuidePayload(localGuide);
        return {
            status: 'fallback',
            image: architectureGuide,
            guide: {
                ...localGuide,
                caption: architectureGuide.caption,
                nodes: architectureGuide.nodes,
                edges: architectureGuide.edges,
                source: architectureGuide.provider
            },
            historySource: 'local_architecture',
            logMessage: `Prof. X 知识结构图接口暂不可用，已为「${localGuide.center}」生成本地知识结构图。`
        };
    }

    return {
        status: 'fallback',
        image: null,
        guide: localGuide,
        historySource: 'local',
        logMessage: `后端生图接口暂不可用，已为「${localGuide.caption.match(/「(.+?)」/)?.[1] || localGuide.center}」生成本地草图模式引导图。`
    };
}

function createLocalArchitectureGuidePayload(localGuide) {
    const center = localGuide?.center || '核心问题';
    const safeNode = sanitizeMermaidLabel(center);
    const mermaid = [
        'flowchart TD',
        `  A[核心概念：${safeNode}] --> B[基本定义]`,
        `  A --> C[关键特性]`,
        `  A --> D[应用场景]`,
        `  B --> E[重要知识点]`,
        `  C --> E`,
        `  D --> E`
    ].join('\n');

    return {
        source: 'local-architecture',
        provider: 'local_text_architecture',
        diagramType: 'mermaid',
        mermaid,
        treeText: '',
        svg: '',
        backgroundUrl: '',
        backgroundBase64: '',
        imageUrl: '',
        imageBase64: '',
        alt: `${center} Prof. X 知识结构图`,
        caption: 'Prof. X 已生成知识结构图（本地模式）。',
        nodes: ['核心概念', '基本定义', '关键特性', '应用场景', '重要知识点'],
        edges: ['定义', '特性', '应用', '展开'],
        metadata: { render_mode: 'local_text_architecture' }
    };
}

export function getVisualGuideSourceLabel(image) {
    if (!image) return '本地草图';
    if (image.provider === 'prof_x_text_architecture' || image.mermaid || image.treeText) return 'Prof.X知识结构图';
    if (image.svg && (image.backgroundUrl || image.backgroundBase64)) return '精准引导图+千问背景';
    if (image.svg) return '精准引导图';
    if (image.provider === 'structured_svg+qwen') return '精准引导图+千问背景';
    if (image.provider === 'structured_svg' || image.provider === 'fallback_svg') return '精准引导图';
    if (image.provider === 'qwen') return '千问AI图';
    if (image) return '后端AI图';
    return '本地草图';
}

export function buildVisualGuideSvg(guide, guideType) {
    const title = escapeXml(guide?.title || 'Mira 学习引导图');
    const center = escapeXml(guide?.center || '核心问题');
    const caption = escapeXml(guide?.caption || '');
    const nodes = (guide?.nodes || []).slice(0, 4);
    const edges = (guide?.edges || []).slice(0, 4);
    const accent = guideType === 'steps' ? '#1d4ed8' : '#b91c1c';
    const positions = [
        { x: 115, y: 118 },
        { x: 358, y: 78 },
        { x: 535, y: 204 },
        { x: 286, y: 295 }
    ];

    const nodeMarkup = positions.map((pos, index) => {
        const text = escapeXml(nodes[index] || `节点 ${index + 1}`);
        const edge = escapeXml(edges[index] || '');
        return `
            <line x1="330" y1="188" x2="${pos.x + 70}" y2="${pos.y + 24}" stroke="${accent}" stroke-opacity="0.22" stroke-width="2" />
            <rect x="${pos.x}" y="${pos.y}" width="140" height="48" rx="14" fill="rgba(255,255,255,0.88)" stroke="${accent}" stroke-opacity="0.18" />
            <text x="${pos.x + 70}" y="${pos.y + 22}" text-anchor="middle" fill="#1c2b38" font-size="13" font-weight="700">${text}</text>
            <text x="${pos.x + 70}" y="${pos.y + 39}" text-anchor="middle" fill="${accent}" font-size="10">${edge}</text>
        `;
    }).join('');

    return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="660" height="390" viewBox="0 0 660 390">
    <defs>
        <linearGradient id="paper" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stop-color="#f8fbfc"/>
            <stop offset="52%" stop-color="#eef4f7"/>
            <stop offset="100%" stop-color="#f7edf0"/>
        </linearGradient>
        <radialGradient id="halo" cx="50%" cy="48%" r="48%">
            <stop offset="0%" stop-color="${accent}" stop-opacity="0.24"/>
            <stop offset="100%" stop-color="${accent}" stop-opacity="0"/>
        </radialGradient>
        <filter id="softNoise">
            <feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves="2" stitchTiles="stitch"/>
            <feColorMatrix type="saturate" values="0"/>
            <feComponentTransfer><feFuncA type="table" tableValues="0 0.08"/></feComponentTransfer>
        </filter>
    </defs>
    <rect width="660" height="390" rx="24" fill="url(#paper)"/>
    <rect width="660" height="390" rx="24" filter="url(#softNoise)" opacity="0.45"/>
    <circle cx="330" cy="188" r="145" fill="url(#halo)"/>
    <circle cx="330" cy="188" r="64" fill="rgba(255,255,255,0.72)" stroke="${accent}" stroke-opacity="0.32" stroke-width="2"/>
    <text x="330" y="181" text-anchor="middle" fill="${accent}" font-size="18" font-weight="800">${center}</text>
    <text x="330" y="205" text-anchor="middle" fill="#64748b" font-size="11">Mira visual guide</text>
    ${nodeMarkup}
    <text x="34" y="42" fill="#1c2b38" font-size="20" font-weight="800">${title}</text>
    <text x="34" y="66" fill="#64748b" font-size="12">${caption}</text>
    <text x="34" y="358" fill="#94a3b8" font-size="10">Generated locally for guided learning · backend image API ready</text>
</svg>`;
}

function extractKeyword(prompt) {
    const normalized = prompt
        .replace(/[，。？！、,.!?：:；;（）()\[\]【】"“”']/g, ' ')
        .replace(/解释一下|什么是|帮我|请|制定|学习计划|如何|怎么|用步骤图说明|用类比解释|说明/g, ' ')
        .trim();
    const parts = normalized.split(/\s+/).filter(Boolean);
    const latinKeyword = parts.find(part => /[A-Za-z0-9]/.test(part));
    return (latinKeyword || parts[0] || prompt.slice(0, 12) || '核心概念').slice(0, 18);
}

function sanitizeMermaidLabel(value) {
    return String(value || '核心问题')
        .replace(/[\[\]{}()<>|"]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()
        .slice(0, 24) || '核心问题';
}

function escapeXml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&apos;');
}
