export default {
    name: 'LearningTextTaskWorkspace',
    props: {
        task: { type: Object, default: null },
        mode: { type: String, default: 'review' },
        hintLevel: { type: Number, default: 0 },
        hint: { type: Object, default: null },
        loading: Boolean
    },
    emits: ['back', 'hint', 'submit'],
    data() {
        return {
            answer: '',
            answerMode: 'structured',
            draftSaved: false
        };
    },
    computed: {
        payload() { return this.task?.content_payload || {}; },
        isGuided() { return this.mode === 'guided'; },
        knowledgePointName() {
            return this.payload.knowledge_point_name || this.task?.knowledge_point_ids?.[0] || '当前知识点';
        },
        wordCount() { return this.answer.trim().replace(/\s/g, '').length; },
        materialSourceLabel() {
            if (this.task?.source_ref) return 'RAGFlow · 关联课程资料';
            if (this.task?.source_type === 'AI_GENERATED') return 'Agent · 目标知识材料';
            return this.task?.source_type || '学习诊断材料';
        },
        materialTitle() {
            return this.isGuided ? `${this.knowledgePointName}引导练习` : `${this.knowledgePointName}知识回顾`;
        },
        displayTitle() {
            return String(this.task?.title || this.materialTitle)
                .replace(/^Remediation\s*[·・-]\s*/i, '补救练习 · ')
                .replace(/^Micro task\s*[·・-]\s*/i, '专项练习 · ');
        },
        materialContent() {
            if (this.isGuided) {
                return this.payload.prompt || this.payload.description || this.task?.why_this_task || '请按照引导步骤分析题目，并写下完整推理过程。';
            }
            return this.payload.content || this.payload.description || this.task?.why_this_task || '请阅读当前知识点材料，并用自己的话复述关键概念。';
        },
        guidedSteps() {
            return Array.isArray(this.payload.guided_steps) ? this.payload.guided_steps : [];
        },
        structurePrompts() {
            return this.isGuided
                ? [
                    { title: '先说明题意', text: `解释这道练习希望你解决的${this.knowledgePointName}问题。` },
                    { title: '再写出推理步骤', text: '按顺序记录判断、依据和中间结论。' },
                    { title: '最后给出检查方法', text: '说明如何验证最终答案或排除错误情况。' }
                ]
                : [
                    { title: '先说明核心概念', text: `用自己的话解释${this.knowledgePointName}。` },
                    { title: '再描述处理步骤', text: '结合一个普通场景和一个边界场景说明。' },
                    { title: '最后给出验证方法', text: '说明如何检查理解或操作结果是否正确。' }
                ];
        },
        understandingQuestions() {
            if (this.isGuided && this.guidedSteps.length) {
                return this.guidedSteps.slice(0, 3).map((step, index) => ({ number: `0${index + 1}`, label: ['题意', '过程', '验证'][index] || '思考', text: step }));
            }
            return this.isGuided
                ? [
                    { number: '01', label: '题意', text: '题目真正要求解决的核心问题是什么？' },
                    { number: '02', label: '过程', text: '你的判断依据和推理顺序是什么？' },
                    { number: '03', label: '验证', text: '怎样检查答案在边界情况下仍然成立？' }
                ]
                : [
                    { number: '01', label: '概念', text: `${this.knowledgePointName}最关键的定义是什么？` },
                    { number: '02', label: '过程', text: '它在实际操作中需要注意哪些步骤？' },
                    { number: '03', label: '迁移', text: '如何用一个边界场景验证你的理解？' }
                ];
        },
        successCriteria() {
            const values = this.payload.success_criteria;
            const defaults = this.isGuided
                ? ['准确说明题意', '写出完整推理过程', '给出结果检查方法']
                : ['解释核心概念', '描述一个边界场景', '给出验证方法'];
            const source = Array.isArray(values) ? values.map(String) : [];
            return [...new Set([...source, ...defaults])].slice(0, 3);
        },
        criterionChecks() {
            const text = this.answer.trim();
            return this.successCriteria.map((criterion, index) => {
                if (!text) return false;
                const tokens = String(criterion).split(/[，。；、\s]/).filter((token) => token.length >= 2);
                const keywordHit = tokens.some((token) => text.includes(token));
                return keywordHit || this.wordCount >= [40, 80, 120][index];
            });
        },
        criteriaProgress() { return this.criterionChecks.filter(Boolean).length; },
        hintText() {
            return this.hint?.content || this.hint?.hint || this.hint?.text || (this.isGuided
                ? '先用一句话写出题目要求，再列出你已经确定的条件。'
                : `先尝试区分${this.knowledgePointName}的普通情况与边界情况。`);
        },
        taskTypeLabel() { return this.isGuided ? 'Guided practice' : 'Knowledge review'; },
        answerPlaceholder() {
            return this.answerMode === 'free'
                ? '在这里写下你的完整思路或答案……'
                : this.structurePrompts.map((item) => `${item.title}：\n${item.text}`).join('\n\n');
        }
    },
    methods: {
        saveDraft() { this.draftSaved = Boolean(this.answer.trim()); },
        submitAnswer() {
            if (!this.answer.trim() || this.loading) return;
            this.$emit('submit', { answer: this.answer });
        }
    },
    template: `
      <section class="h-full overflow-y-auto bg-[#eef2f4] p-4 lg:p-7">
        <div class="max-w-[1280px] mx-auto">
          <div class="flex items-center justify-between gap-4 mb-4">
            <button class="text-xs font-bold text-slate-600 flex items-center gap-2" @click="$emit('back')"><i class="ph ph-arrow-left"></i>返回学习诊断　/　{{ isGuided ? '引导练习' : '知识回顾' }}</button>
            <span class="px-3 py-1.5 rounded-full bg-white border border-[#b91c1c]/30 text-[#b91c1c] text-[10px] font-bold">诊断会话进行中</span>
          </div>

          <section class="bg-white rounded-[22px] border border-white shadow-soft overflow-hidden">
            <header class="px-5 lg:px-7 py-5 border-b border-slate-200 grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_330px] gap-5">
              <div>
                <p class="text-[10px] uppercase tracking-[0.22em] text-slate-500 font-bold">{{ taskTypeLabel }} · {{ knowledgePointName }}</p>
                <h1 class="text-2xl lg:text-3xl font-bold text-[#1c2b38] mt-2" style="font-family:'Noto Serif SC',serif">{{ displayTitle }}</h1>
                <p class="text-xs text-slate-500 mt-2">{{ task?.learning_objective || task?.why_this_task || '完成作答后，Agent 将生成新的诊断证据。' }}</p>
                <div class="flex flex-wrap gap-2 mt-4"><span class="px-2.5 py-1 rounded-full bg-red-50 text-[#a32923] text-[10px] font-bold">当前首要任务</span><span class="px-2.5 py-1 rounded-full bg-[#edf3f5] text-[#456170] text-[10px] font-bold">预计 {{ task?.estimated_minutes || 10 }} 分钟</span><span class="px-2.5 py-1 rounded-full bg-[#edf3f5] text-[#456170] text-[10px] font-bold">难度 {{ task?.difficulty || 1 }} / 5</span></div>
              </div>
              <div class="self-center">
                <div class="flex justify-between text-[10px] text-slate-400"><span class="text-[#a32923] font-bold">阅读材料</span><span class="text-[#a32923] font-bold">组织作答</span><span>Agent 诊断</span><span>更新路径</span></div>
                <div class="h-1.5 rounded-full bg-slate-200 mt-3 overflow-hidden"><div class="h-full w-1/2 bg-[#b91c1c] rounded-full"></div></div>
              </div>
            </header>

            <div class="grid grid-cols-1 xl:grid-cols-[minmax(0,1.45fr)_340px]">
              <main class="min-w-0 bg-[#fbfcfc] p-5 lg:p-6 xl:border-r border-slate-200">
                <div class="flex items-center justify-between mb-3"><h2 class="text-xl font-bold text-[#1c2b38]" style="font-family:'Noto Serif SC',serif">学习材料</h2><span class="text-[10px] text-slate-400">已关联当前目标知识点</span></div>
                <article class="rounded-2xl border border-slate-200 bg-white p-5">
                  <div class="flex items-center justify-between gap-3"><span class="text-[10px] text-[#456170] font-bold"><i class="ph ph-books mr-1"></i>{{ materialSourceLabel }}</span><span class="px-2 py-1 rounded-full bg-[#edf3f5] text-[10px] text-[#456170]">{{ knowledgePointName }}</span></div>
                  <h3 class="text-sm font-bold text-[#1c2b38] mt-4">{{ materialTitle }}</h3>
                  <p class="text-xs text-slate-600 leading-7 mt-2">{{ materialContent }}</p>
                  <div v-if="guidedSteps.length" class="mt-3 border-l-[3px] border-[#b91c1c] bg-red-50/60 rounded-r-xl px-4 py-3"><p v-for="(step,index) in guidedSteps" :key="index" class="text-[11px] text-slate-600 leading-6">{{ index + 1 }}. {{ step }}</p></div>
                  <div v-else class="mt-3 border-l-[3px] border-[#b91c1c] bg-red-50/60 rounded-r-xl px-4 py-3 text-[11px] text-slate-600">关键关注：概念、边界场景、处理过程与验证方法。</div>
                </article>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-2.5 my-4">
                  <article v-for="question in understandingQuestions" :key="question.number" class="rounded-xl border border-slate-200 bg-[#f7fafb] p-3 min-h-[84px]"><p class="text-[10px] text-[#b91c1c] font-bold">{{ question.number }} {{ question.label }}</p><p class="text-[11px] text-slate-700 leading-5 mt-2">{{ question.text }}</p></article>
                </div>

                <div class="flex items-center justify-between mb-3"><h2 class="text-xl font-bold text-[#1c2b38]" style="font-family:'Noto Serif SC',serif">我的回答</h2><span class="text-[10px] text-slate-400">建议 120–300 字</span></div>
                <section class="rounded-2xl border border-slate-200 bg-white overflow-hidden">
                  <div class="h-11 flex items-center gap-1 bg-[#f3f7f8] border-b border-slate-200 px-2"><button class="h-8 px-3 rounded-lg text-[10px]" :class="answerMode === 'structured' ? 'bg-white text-slate-900 font-bold shadow-sm' : 'text-slate-500'" @click="answerMode = 'structured'">结构化复述</button><button class="h-8 px-3 rounded-lg text-[10px]" :class="answerMode === 'free' ? 'bg-white text-slate-900 font-bold shadow-sm' : 'text-slate-500'" @click="answerMode = 'free'">自由作答</button></div>
                  <textarea v-model="answer" :placeholder="answerPlaceholder" class="w-full min-h-[230px] resize-y p-5 text-sm text-slate-700 leading-7 outline-none placeholder:text-slate-400"></textarea>
                  <div class="min-h-[42px] flex items-center justify-between gap-3 px-4 border-t border-slate-200 text-[10px] text-slate-400"><span><i class="inline-block w-1.5 h-1.5 rounded-full bg-[#5d8793] mr-1"></i>{{ draftSaved ? '草稿已保存在当前页面' : '输入内容仅保存在当前页面' }}</span><span>{{ wordCount }} / 300 字　·　概念覆盖 {{ criteriaProgress }} / {{ successCriteria.length }}</span></div>
                </section>

                <div class="sticky bottom-0 -mx-5 lg:-mx-6 mt-5 px-5 lg:px-6 py-4 bg-white/95 backdrop-blur border-t border-slate-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 z-10"><p class="text-[10px] text-slate-500">提交后形成新的学习证据，并重新计算相关知识点掌握度。</p><div class="flex gap-2 self-end sm:self-auto"><button class="min-h-[40px] px-4 rounded-xl border border-slate-300 bg-white text-xs font-bold text-slate-700" @click="saveDraft">保存并稍后继续</button><button :disabled="loading || !answer.trim()" class="min-h-[40px] px-5 rounded-xl bg-[#b91c1c] text-white text-xs font-bold disabled:opacity-45 shadow-[0_8px_18px_rgba(185,28,28,.18)]" @click="submitAnswer">提交并生成诊断</button></div></div>
              </main>

              <aside class="bg-[#f5f8f9] p-5">
                <section class="rounded-2xl bg-[#1c2b38] text-white p-5 shadow-lg">
                  <p class="text-[10px] uppercase tracking-[0.2em] text-white/50 font-bold">Agent guide</p>
                  <div class="flex items-center gap-3 mt-3"><span class="w-10 h-10 rounded-xl bg-white/10 grid place-items-center text-xs font-bold">P.X</span><div><h3 class="text-sm font-bold">Prof. X · 启发式导师</h3><p class="text-[10px] text-white/55 mt-1">只提供下一步，不直接给出完整答案</p></div></div>
                  <p class="text-[11px] text-white/70 leading-6 mt-4">先尝试回答三个理解检查。卡住时再逐级获取提示，提示使用情况会进入诊断证据。</p>
                  <div class="rounded-xl bg-white/[.07] p-4 mt-3"><div class="flex justify-between text-[10px] text-white/55"><span>当前提示</span><strong class="text-white">Level {{ hintLevel || 1 }} / 5</strong></div><p class="text-[11px] leading-6 mt-3">{{ hintText }}</p><button class="w-full min-h-[38px] rounded-xl border border-white/20 text-[10px] font-bold mt-3" @click="$emit('hint')">获取下一层提示</button></div>
                </section>

                <section class="rounded-2xl bg-white border border-slate-200 p-5 mt-4"><h3 class="text-sm font-bold text-[#1c2b38]">完成标准</h3><div v-for="(criterion,index) in successCriteria" :key="criterion" class="flex items-start gap-2 mt-3"><span class="w-4 h-4 rounded-[5px] border grid place-items-center text-[9px]" :class="criterionChecks[index] ? 'bg-[#b91c1c] border-[#b91c1c] text-white' : 'border-slate-300 bg-[#f7fafb]'">{{ criterionChecks[index] ? '✓' : '' }}</span><p class="text-[10px] text-slate-600 leading-5 flex-1">{{ criterion }}</p></div></section>
                <section class="rounded-2xl bg-amber-50 border border-amber-200 p-4 mt-4"><p class="text-[10px] font-bold text-amber-800">独立思考保护</p><p class="text-[10px] text-amber-700 leading-5 mt-2">系统不会直接展示标准答案。高等级提示会降低本次证据权重，但不会阻止你完成学习。</p></section>
              </aside>
            </div>
          </section>
        </div>
      </section>`
};
