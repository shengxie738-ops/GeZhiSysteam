export default {
    name: 'LearningCodingPracticePage',
    props: {
        task: { type: Object, default: null },
        code: { type: String, default: '' },
        hintLevel: { type: Number, default: 0 },
        hint: { type: Object, default: null },
        execution: { type: Object, default: null },
        loading: Boolean
    },
    emits: ['back', 'hint', 'run', 'reset', 'submit', 'update:code'],
    data() {
        return { resultTab: 'tests' };
    },
    computed: {
        payload() { return this.task?.content_payload || {}; },
        knowledgePointName() {
            return this.payload.knowledge_point_name || this.task?.knowledge_point_ids?.[0] || '当前知识点';
        },
        displayTitle() {
            return String(this.task?.title || `${this.knowledgePointName}编程练习`)
                .replace(/^Remediation\s*[·・-]\s*/i, '补救练习 · ')
                .replace(/^Micro task\s*[·・-]\s*/i, '专项练习 · ');
        },
        problemDescription() {
            return this.payload.description || this.task?.description || this.task?.why_this_task || '根据题目契约完成代码，并通过公开测试用例。';
        },
        contractText() {
            if (this.payload.function_contract) return String(this.payload.function_contract);
            const contract = this.payload.contract;
            if (typeof contract === 'string') return contract;
            if (contract && typeof contract === 'object') {
                const name = contract.function_name || this.payload.function_name || 'solve';
                return `${name}(...) · ${contract.language || 'python'}`;
            }
            return `${this.payload.function_name || 'solve'}(...)`;
        },
        languageLabel() {
            const language = String(this.payload.contract?.language || this.execution?.language || 'python').toLowerCase();
            return language === 'javascript' ? 'JavaScript' : 'Python 3';
        },
        publicTestCases() {
            const cases = Array.isArray(this.payload.test_cases) ? this.payload.test_cases : [];
            return cases.slice(0, 4).map((item, index) => ({
                id: index + 1,
                label: index === 0 ? '普通情况' : index === 1 ? '边界情况' : index === 2 ? '空值情况' : `测试 ${index + 1}`,
                input: Array.isArray(item.input) ? item.input.join(', ') : String(item.input ?? ''),
                expected: String(item.expected ?? '')
            }));
        },
        successCriteria() {
            const criteria = Array.isArray(this.payload.success_criteria) ? this.payload.success_criteria.map(String) : [];
            const defaults = ['正确处理普通输入与边界输入', '代码能够安全运行', '通过全部公开测试'];
            return [...new Set([...criteria, ...defaults])].slice(0, 3);
        },
        lineNumbers() {
            return Array.from({ length: Math.max(16, String(this.code || '').split('\n').length) }, (_, index) => index + 1);
        },
        testSummary() {
            return this.execution?.test_summary || { total: this.publicTestCases.length, passed: 0, failed: 0 };
        },
        executionCases() {
            return Array.isArray(this.execution?.test_cases) ? this.execution.test_cases : [];
        },
        displayCases() {
            if (this.executionCases.length) {
                return this.executionCases.slice(0, 4).map((item, index) => ({
                    id: item.testCase || index + 1,
                    label: this.publicTestCases[index]?.label || `测试 ${index + 1}`,
                    passed: Boolean(item.passed),
                    expected: String(item.expected ?? ''),
                    actual: String(item.actual ?? ''),
                    error: String(item.error || '')
                }));
            }
            return this.publicTestCases.map((item) => ({ ...item, passed: null, actual: '', error: '' }));
        },
        hasExecution() { return Boolean(this.execution?.execution_id || this.execution?.status); },
        executionPassed() { return this.execution?.status === 'PASSED'; },
        executionStatusLabel() {
            const labels = { PASSED: '全部通过', TEST_FAILED: '存在失败用例', RUNTIME_ERROR: '运行错误', SECURITY_VIOLATION: '安全检查未通过', SANDBOX_ERROR: '沙箱执行失败' };
            return labels[this.execution?.status] || '尚未运行';
        },
        progressWidth() {
            if (this.hasExecution) return this.executionPassed ? '88%' : '68%';
            return this.code.trim() ? '48%' : '24%';
        },
        hintText() {
            return this.hint?.content || this.hint?.hint || this.hint?.text || '先运行当前代码并观察失败用例。Agent 会结合题目、代码和运行结果逐级缩小问题范围。';
        },
        hintBasis() {
            return this.hint?.based_on_attempt || (this.hasExecution ? '已结合最近一次运行结果' : '等待一次真实运行结果');
        },
        diagnosticSignals() {
            if (!this.hasExecution) return [
                { tone: 'neutral', mark: '1', text: '等待运行代码以生成调试信号。' },
                { tone: 'neutral', mark: '2', text: 'Hint 将结合最近一次运行结果。' },
                { tone: 'neutral', mark: '3', text: '正式提交后才更新掌握度证据。' }
            ];
            const firstFailure = this.displayCases.find((item) => item.passed === false);
            return [
                { tone: this.testSummary.passed ? 'positive' : 'neutral', mark: '1', text: `已通过 ${this.testSummary.passed || 0} / ${this.testSummary.total || 0} 个公开测试。` },
                { tone: firstFailure ? 'alert' : 'positive', mark: firstFailure ? '!' : '2', text: firstFailure ? `${firstFailure.label}仍需检查：${firstFailure.error || `实际结果 ${firstFailure.actual || '为空'}`}。` : '当前公开测试未发现边界遗漏。' },
                { tone: 'neutral', mark: '3', text: '提交后才会形成正式掌握度证据。' }
            ];
        },
        sourceLabel() {
            if (this.task?.source_ref) return 'RAGFlow · 关联题目';
            if (this.task?.source_type === 'AI_GENERATED') return 'Agent · 目标专项练习';
            return this.task?.source_type || '学习诊断编程任务';
        }
    },
    methods: {
        updateCode(value) { this.$emit('update:code', value); },
        runCode() { if (!this.loading && this.code.trim()) this.$emit('run', { code: this.code }); },
        submitCode() { if (!this.loading && this.code.trim()) this.$emit('submit', { code: this.code }); }
    },
    template: `
      <section class="h-full overflow-y-auto bg-[#eef2f4] p-4 lg:p-6">
        <div class="max-w-[1320px] mx-auto">
          <div class="flex items-center justify-between gap-4 mb-3">
            <button class="text-xs font-bold text-slate-600 flex items-center gap-2" @click="$emit('back')"><i class="ph ph-arrow-left"></i>返回学习诊断　/　编程练习</button>
            <span class="px-3 py-1.5 rounded-full bg-white border border-[#b91c1c]/30 text-[#b91c1c] text-[10px] font-bold">诊断会话进行中</span>
          </div>

          <section class="bg-white rounded-[22px] border border-white shadow-soft overflow-hidden">
            <header class="px-5 lg:px-7 py-5 border-b border-slate-200 grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_390px] gap-5">
              <div>
                <p class="text-[10px] uppercase tracking-[0.22em] text-slate-500 font-bold">Learning diagnosis / Coding · {{ knowledgePointName }}</p>
                <h1 class="text-2xl lg:text-3xl font-bold text-[#1c2b38] mt-2" style="font-family:'Noto Serif SC',serif">{{ displayTitle }}</h1>
                <p class="text-xs text-slate-500 mt-2">{{ task?.learning_objective || problemDescription }}</p>
                <div class="flex flex-wrap gap-2 mt-4"><span class="px-2.5 py-1 rounded-full bg-red-50 text-[#a32923] text-[10px] font-bold">当前首要任务</span><span class="px-2.5 py-1 rounded-full bg-[#edf3f5] text-[#456170] text-[10px] font-bold">预计 {{ task?.estimated_minutes || 20 }} 分钟</span><span class="px-2.5 py-1 rounded-full bg-[#edf3f5] text-[#456170] text-[10px] font-bold">{{ languageLabel }}</span><span class="px-2.5 py-1 rounded-full bg-[#edf3f5] text-[#456170] text-[10px] font-bold">难度 {{ task?.difficulty || 1 }} / 5</span></div>
              </div>
              <div class="self-center">
                <div class="flex justify-between text-[10px] text-slate-400"><span class="text-[#a32923] font-bold">理解题意</span><span class="text-[#a32923] font-bold">编写代码</span><span :class="hasExecution ? 'text-[#a32923] font-bold' : ''">运行验证</span><span>Agent 诊断</span></div>
                <div class="h-1.5 rounded-full bg-slate-200 mt-3 overflow-hidden"><div class="h-full bg-[#b91c1c] rounded-full transition-all duration-300" :style="{ width: progressWidth }"></div></div>
              </div>
            </header>

            <div class="grid grid-cols-1 xl:grid-cols-[280px_minmax(0,1fr)_300px] min-h-[670px]">
              <aside class="bg-[#fbfcfc] p-5 xl:border-r border-slate-200">
                <h2 class="text-xl font-bold text-[#1c2b38]" style="font-family:'Noto Serif SC',serif">题目</h2>
                <span class="inline-flex mt-3 px-2.5 py-1 rounded-full bg-[#edf3f5] text-[#456170] text-[9px] font-bold"><i class="ph ph-code mr-1"></i>{{ sourceLabel }}</span>
                <h3 class="text-sm font-bold text-[#1c2b38] mt-4">{{ payload.problem_title || displayTitle }}</h3>
                <p class="text-[11px] text-slate-600 leading-6 mt-2">{{ problemDescription }}</p>
                <pre class="mt-3 px-3 py-3 border-l-[3px] border-[#b91c1c] rounded-r-xl bg-red-50/70 text-[10px] text-slate-600 whitespace-pre-wrap font-mono leading-5">{{ contractText }}</pre>

                <h3 class="text-[11px] font-bold text-slate-800 mt-5">公开样例</h3>
                <article v-for="item in publicTestCases.slice(0,2)" :key="item.id" class="rounded-xl border border-slate-200 bg-white p-3 mt-2">
                  <div class="flex items-center justify-between text-[9px] text-slate-400"><span>示例 0{{ item.id }}</span><span>{{ item.label }}</span></div>
                  <div class="grid grid-cols-[34px_1fr] gap-y-1 mt-2 text-[10px] font-mono"><strong class="text-slate-500">输入</strong><span class="truncate">{{ item.input || '无' }}</span><strong class="text-slate-500">输出</strong><span class="truncate">{{ item.expected || '无' }}</span></div>
                </article>

                <h3 class="text-[11px] font-bold text-slate-800 mt-5">完成要求</h3>
                <div v-for="criterion in successCriteria" :key="criterion" class="flex items-start gap-2 py-3 border-b border-slate-200 last:border-0"><span class="w-4 h-4 rounded-[5px] bg-[#edf3f5] text-[#527482] grid place-items-center text-[9px] font-bold">✓</span><p class="text-[10px] text-slate-600 leading-5 flex-1">{{ criterion }}</p></div>
              </aside>

              <main class="min-w-0 bg-[#f4f7f8] p-4">
                <section class="rounded-2xl overflow-hidden bg-[#121d28] shadow-[0_10px_24px_rgba(18,29,40,.16)]">
                  <div class="h-11 px-4 flex items-center justify-between bg-[#1b2b39] border-b border-white/10 text-[10px]"><span class="font-mono text-slate-100">solution.{{ languageLabel === 'JavaScript' ? 'js' : 'py' }}　<span class="text-amber-300">●</span> 已修改</span><span class="px-2.5 py-1 rounded-lg border border-white/10 text-slate-300">{{ languageLabel }}</span></div>
                  <div class="grid grid-cols-[42px_minmax(0,1fr)] min-h-[420px] max-h-[480px] overflow-hidden">
                    <div class="py-4 pr-3 text-right bg-[#101a24] text-[11px] leading-[22px] text-slate-600 font-mono select-none"><div v-for="number in lineNumbers" :key="number">{{ number }}</div></div>
                    <textarea :value="code" @input="updateCode($event.target.value)" spellcheck="false" aria-label="学习诊断代码编辑器" class="w-full min-h-[420px] max-h-[480px] resize-none overflow-auto bg-[#121d28] text-slate-100 p-4 outline-none font-mono text-xs leading-[22px] placeholder:text-slate-600" placeholder="请在这里完成代码……"></textarea>
                  </div>
                  <footer class="min-h-[52px] px-3 py-2 bg-white flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2"><span class="text-[9px] text-slate-400">{{ hasExecution ? '代码修改后需重新运行，当前显示最近一次结果' : '草稿仅保存在当前页面' }}</span><div class="flex gap-2 self-end sm:self-auto"><button class="min-h-[36px] px-3 rounded-xl border border-slate-300 bg-white text-[10px] font-bold text-slate-700" @click="$emit('reset')">重置代码</button><button :disabled="loading || !code.trim()" class="min-h-[36px] px-4 rounded-xl bg-[#1c2b38] text-white text-[10px] font-bold disabled:opacity-45" @click="runCode"><i class="ph ph-play mr-1"></i>运行代码</button><button :disabled="loading || !code.trim()" class="min-h-[36px] px-4 rounded-xl bg-[#b91c1c] text-white text-[10px] font-bold disabled:opacity-45" @click="submitCode">提交并生成诊断</button></div></footer>
                </section>

                <section class="rounded-2xl overflow-hidden bg-white border border-slate-200 mt-3 min-h-[174px]">
                  <div class="h-10 px-4 bg-[#fbfcfc] border-b border-slate-200 flex items-center justify-between gap-3"><div class="flex gap-5 text-[10px]"><button :class="resultTab === 'console' ? 'text-[#b91c1c] font-bold' : 'text-slate-500'" @click="resultTab='console'">控制台</button><button :class="resultTab === 'tests' ? 'text-[#b91c1c] font-bold' : 'text-slate-500'" @click="resultTab='tests'">测试结果</button><button :class="resultTab === 'history' ? 'text-[#b91c1c] font-bold' : 'text-slate-500'" @click="resultTab='history'">运行记录</button></div><span class="text-[9px]" :class="executionPassed ? 'text-emerald-700' : hasExecution ? 'text-red-600' : 'text-slate-400'">{{ executionStatusLabel }}<template v-if="hasExecution"> · {{ testSummary.passed || 0 }} / {{ testSummary.total || 0 }} 通过</template></span></div>
                  <div v-if="resultTab === 'tests'" class="grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-4 gap-2 p-3">
                    <article v-for="item in displayCases" :key="item.id" class="rounded-xl border p-3 min-w-0" :class="item.passed === true ? 'border-emerald-200 bg-emerald-50/50' : item.passed === false ? 'border-red-200 bg-red-50/50' : 'border-slate-200 bg-[#f7f9fa]'"><p class="text-[10px] font-bold" :class="item.passed === true ? 'text-emerald-700' : item.passed === false ? 'text-red-700' : 'text-slate-600'">{{ item.passed === true ? '✓' : item.passed === false ? '×' : '—' }} {{ item.label }}</p><p class="text-[9px] text-slate-500 mt-2 truncate">预期 {{ item.expected || '无' }}</p><p v-if="item.passed !== null" class="text-[9px] text-slate-500 mt-1 truncate">实际 {{ item.error || item.actual || '无输出' }}</p></article>
                  </div>
                  <pre v-else-if="resultTab === 'console'" class="p-4 text-[10px] leading-6 font-mono whitespace-pre-wrap text-slate-600">{{ execution?.stderr || execution?.stdout || '运行代码后，这里会展示标准输出或错误信息。' }}</pre>
                  <div v-else class="p-4"><div v-if="hasExecution" class="flex items-center justify-between rounded-xl bg-[#f7f9fa] border border-slate-200 p-3"><div><p class="text-[10px] font-bold text-slate-700">最近一次运行</p><p class="text-[9px] text-slate-400 mt-1">Execution {{ execution.execution_id }}</p></div><span class="text-[10px] font-bold" :class="executionPassed ? 'text-emerald-700' : 'text-red-700'">{{ executionStatusLabel }}</span></div><p v-else class="text-[10px] text-slate-400">当前还没有运行记录。</p></div>
                </section>
              </main>

              <aside class="bg-[#f4f7f8] p-5 xl:border-l border-slate-200">
                <section class="rounded-2xl bg-[#1c2b38] text-white p-5 shadow-lg">
                  <p class="text-[10px] uppercase tracking-[0.2em] text-white/50 font-bold">Agent guide</p>
                  <div class="flex items-center gap-3 mt-3"><span class="w-10 h-10 rounded-xl bg-white/10 grid place-items-center text-xs font-bold">P.X</span><div><h3 class="text-sm font-bold">Prof. X · 调试导师</h3><p class="text-[10px] text-white/55 mt-1">观察运行证据，只提示下一步</p></div></div>
                  <p class="text-[10px] text-white/65 leading-6 mt-4">先运行代码并查看失败用例。Agent 会结合题目、代码和测试结果逐级缩小问题范围。</p>
                  <div class="rounded-xl bg-white/[.07] p-4 mt-3"><div class="flex justify-between text-[10px] text-white/55"><span>当前提示</span><strong class="text-white">Level {{ hintLevel || 1 }} / 5</strong></div><p class="text-[10px] leading-6 mt-3">{{ hintText }}</p><p class="text-[9px] text-white/45 mt-2">{{ hintBasis }}</p><button class="w-full min-h-[38px] rounded-xl border border-white/20 text-[10px] font-bold mt-3" @click="$emit('hint')">获取下一层提示</button></div>
                </section>

                <section class="rounded-2xl bg-white border border-slate-200 p-4 mt-4"><h3 class="text-sm font-bold text-[#1c2b38]">实时诊断信号</h3><div v-for="signal in diagnosticSignals" :key="signal.text" class="flex items-start gap-2 mt-3"><span class="w-4 h-4 rounded-[5px] grid place-items-center text-[8px] flex-none" :class="signal.tone === 'alert' ? 'bg-red-50 text-red-700' : signal.tone === 'positive' ? 'bg-emerald-50 text-emerald-700' : 'bg-[#edf3f5] text-[#526f7e]'">{{ signal.mark }}</span><p class="text-[9px] text-slate-600 leading-5 flex-1">{{ signal.text }}</p></div></section>
                <section class="rounded-2xl bg-amber-50 border border-amber-200 p-4 mt-4"><p class="text-[10px] font-bold text-amber-800">独立思考保护</p><p class="text-[9px] text-amber-700 leading-5 mt-2">Agent 不会直接补全代码。高等级提示与多次失败会降低本次证据权重，但不会阻止继续练习。</p></section>
              </aside>
            </div>
            <footer class="min-h-[40px] px-4 border-t border-slate-200 bg-white flex items-center justify-center text-[9px] text-slate-400">运行结果只用于调试；点击“提交并生成诊断”后才更新学习证据与动态路径。</footer>
          </section>
        </div>
      </section>`
};
