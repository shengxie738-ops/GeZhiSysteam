import LearningTextTaskWorkspace from './LearningTextTaskWorkspace.js';

export default {
    name: 'LearningGuidedPracticePage',
    components: { LearningTextTaskWorkspace },
    props: { task: Object, hintLevel: Number, hint: Object, loading: Boolean },
    emits: ['back', 'hint', 'submit'],
    template: `<learning-text-task-workspace aria-label="Learning diagnosis / Guided practice" mode="guided" :task="task" :hint-level="hintLevel" :hint="hint" :loading="loading" @back="$emit('back')" @hint="$emit('hint')" @submit="$emit('submit', $event)"></learning-text-task-workspace>`
};
