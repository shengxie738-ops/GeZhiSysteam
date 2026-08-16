export default {
    name: 'LearningDiagnosisTaskPage',
    props: { task: Object, code: String, hintLevel: Number, loading: Boolean },
    emits: ['back', 'update:code', 'hint', 'submit'],
    template: `
      <section class="h-full overflow-y-auto bg-slate-50 p-5 lg:p-8">
        <div class="max-w-6xl mx-auto">
          <button class="text-xs font-bold text-slate-600 mb-5 flex items-center gap-2" @click="$emit('back')"><i class="ph ph-arrow-left"></i>返回学习诊断</button>
          <div class="grid grid-cols-1 xl:grid-cols-[360px_1fr] gap-5">
            <aside class="space-y-4">
              <article class="bg-white border border-slate-200 rounded-2xl p-5 shadow-soft">
                <p class="text-[10px] uppercase tracking-[0.2em] text-slate-400 font-bold">Task briefing</p>
                <h2 class="text-2xl font-bold text-slate-900 mt-2">{{ task?.title }}</h2>
                <p class="text-xs text-slate-500 mt-3 leading-relaxed">聚焦链表边界条件：普通输入、空链表、单节点和异常输入。请先独立完成，再按需申请提示。</p>
                <div class="mt-4 flex flex-wrap gap-2"><span class="px-2.5 py-1 rounded-full bg-slate-100 text-[10px] font-bold">{{ task?.task_type }}</span><span class="px-2.5 py-1 rounded-full bg-slate-100 text-[10px] font-bold">预计 {{ task?.estimated_minutes }} 分钟</span></div>
              </article>
              <article class="bg-[#1c2b38] text-white rounded-2xl p-5">
                <p class="text-[10px] uppercase tracking-[0.2em] text-white/50 font-bold">Hint policy</p>
                <h3 class="font-bold mt-2">当前 Level {{ hintLevel }}</h3>
                <p class="text-xs text-white/65 mt-2 leading-relaxed">提示只降低本条证据的独立性权重，不惩罚学生。INDEPENDENT_RETEST 独立复测最多允许 Level 1。</p>
                <button :disabled="loading || (task?.task_type === 'INDEPENDENT_RETEST' && hintLevel >= 1)" class="mt-4 w-full min-h-[42px] rounded-xl bg-white text-slate-900 text-xs font-bold disabled:opacity-50" @click="$emit('hint')">申请下一层提示</button>
              </article>
            </aside>
            <main class="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-soft min-h-[620px] flex flex-col">
              <header class="h-14 px-5 border-b border-slate-200 flex items-center justify-between"><span class="text-xs font-bold text-slate-900">Python 沙箱</span><span class="text-[10px] font-mono text-slate-400">isolated execution</span></header>
              <textarea :value="code" @input="$emit('update:code', $event.target.value)" spellcheck="false" class="flex-1 min-h-[430px] resize-none bg-[#111827] text-slate-100 font-mono text-sm p-5 outline-none"></textarea>
              <footer class="p-4 border-t border-slate-200 flex justify-end"><button :disabled="loading" class="min-h-[44px] px-6 rounded-xl bg-[#b91c1c] hover:bg-[#991b1b] text-white text-xs font-bold disabled:opacity-60" @click="$emit('submit')">运行并提交证据</button></footer>
            </main>
          </div>
        </div>
      </section>`
};
