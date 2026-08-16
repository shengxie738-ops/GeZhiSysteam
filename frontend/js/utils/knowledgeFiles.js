export const SUPPORTED_KNOWLEDGE_FILE_EXTENSIONS = [
    'pdf',
];

export const ACCEPTED_KNOWLEDGE_FILE_EXTENSIONS = SUPPORTED_KNOWLEDGE_FILE_EXTENSIONS
    .map(ext => `.${ext}`)
    .join(',');

export function getKnowledgeFileExtension(file) {
    const name = file?.name || '';
    const parts = name.split('.');
    if (parts.length < 2) return '';
    return parts.pop().toLowerCase();
}

export function isSupportedKnowledgeFile(file) {
    const extension = getKnowledgeFileExtension(file);
    return SUPPORTED_KNOWLEDGE_FILE_EXTENSIONS.includes(extension);
}

export function getKnowledgeFileStatusLabel(status) {
    const labels = {
        parsed: '已同步',
        failed: '解析失败',
        queued: '待解析',
        cancelled: '已取消',
        parsing: '解析中',
    };
    return labels[status] || labels.parsing;
}
