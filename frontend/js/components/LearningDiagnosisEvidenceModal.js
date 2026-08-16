export default {
    name: 'LearningDiagnosisEvidenceModal',
    props: { open: Boolean, snapshot: Object, evidence: { type: Array, default: () => [] } },
    emits: ['close'],
    template: `
      <div v-if="open" class="fixed inset-0 z-[90] bg-slate-950/40 backdrop-blur-sm flex items-center justify-center p-4" @click.self="$emit('close')">
        <section class="w-full max-w-2xl max-h-[82vh] overflow-y-auto bg-[#fcfbfa] border border-white rounded-2xl shadow-2xl p-6">
          <header class="flex items-start justify-between gap-4 border-b border-slate-200 pb-4">
            <div><p class="text-[10px] uppercase tracking-[0.2em] text-slate-400 font-bold">Evidence provenance</p><h3 class="text-xl font-bold text-slate-900 mt-1">诊断证据与来源</h3></div>
            <button class="w-9 h-9 rounded-xl border border-slate-200 bg-white" @click="$emit('close')"><i class="ph ph-x"></i></button>
          </header>
          <div class="mt-5 space-y-3">
            <article v-for="(item, index) in evidence" :key="item.evidence_id || item.id || index" class="rounded-xl border border-slate-200 bg-white/80 p-4">
              <div class="flex justify-between gap-3"><span class="text-xs font-bold text-slate-900">{{ item.source_type || '学习活动' }} · 证据 {{ index + 1 }}</span><span class="text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-full px-2 py-1">可靠度 {{ Math.round(Number(item.provenance?.reliability || 0) * 100) }}%</span></div>
              <p class="text-xs text-slate-700 mt-2">{{ item.summary || item.result?.summary || '已记录与当前目标相关的学习活动。' }}</p>
              <p class="font-mono text-[11px] text-slate-500 mt-2 break-all">{{ item.source_ref || item.evidence_id || item.id }}</p>
              <p class="text-[11px] text-slate-500 mt-2">知识点：{{ (item.knowledge_point_ids || []).join('、') || '当前目标' }}</p>
            </article>
            <p v-if="!evidence.length" class="rounded-xl border border-dashed border-slate-300 p-6 text-center text-xs text-slate-500">当前快照暂无可展示的目标相关证据，完成任务后会在此处出现。</p>
          </div>
        </section>
      </div>`
};
