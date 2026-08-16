import { ref, reactive, inject, computed } from 'vue';

export default {
    name: 'TeacherCourseManager',
    props: {
        courses: {
            type: Array,   // 接收已解引用的响应式数组
            required: true
        }
    },
    emits: ['show-toast'],
    setup(props, { emit }) {
        // ── 视图状态 ──────────────────────────────────────────
        const editMode       = ref(false);
        const selectedCourse = ref(null);   // 当前进入管理的课程对象（引用）

        // ── 课程编辑 ──────────────────────────────────────────
        const editingCourse = ref(null);    // 正在编辑信息的课程
        const editForm      = reactive({ name: '', code: '', desc: '' });

        const startEditCourse = (course, e) => {
            e && e.stopPropagation();
            editingCourse.value = course;
            editForm.name = course.name;
            editForm.code = course.code;
            editForm.desc = course.desc;
        };

        const saveEditCourse = () => {
            if (!editForm.name.trim()) {
                emit('show-toast', '课程名不能为空', 'error');
                return;
            }
            editingCourse.value.name = editForm.name.trim();
            editingCourse.value.code = editForm.code.trim();
            editingCourse.value.desc = editForm.desc.trim();
            editingCourse.value = null;
            emit('show-toast', '课程信息已保存 ✓', 'success');
        };

        const cancelEditCourse = () => { editingCourse.value = null; };

        // ── 新建课程 ──────────────────────────────────────────
        const showNewCourseModal = ref(false);
        const newCourseForm = reactive({
            name: '', code: '', desc: '', icon: 'ph-book-open',
            color: 'from-blue-500 to-indigo-600'
        });
        const iconOptions = [
            'ph-book-open', 'ph-code', 'ph-brain', 'ph-cpu',
            'ph-database', 'ph-tree-structure', 'ph-flask', 'ph-chart-bar'
        ];
        const colorOptions = [
            { label: '蓝靛', value: 'from-blue-500 to-indigo-600' },
            { label: '翠绿', value: 'from-emerald-500 to-teal-600' },
            { label: '紫罗', value: 'from-purple-500 to-indigo-600' },
            { label: '琥珀', value: 'from-amber-500 to-orange-600' },
            { label: '玫红', value: 'from-pink-500 to-rose-600' },
            { label: '石板', value: 'from-slate-500 to-slate-700' },
        ];

        const openNewCourseModal = () => {
            Object.assign(newCourseForm, { name: '', code: '', desc: '', icon: 'ph-book-open', color: 'from-blue-500 to-indigo-600' });
            showNewCourseModal.value = true;
        };

        const saveNewCourse = () => {
            if (!newCourseForm.name.trim() || !newCourseForm.code.trim()) {
                emit('show-toast', '课程名和课程编号不能为空', 'error');
                return;
            }
            const newCourse = {
                id: 'course_' + Date.now(),
                name:  newCourseForm.name.trim(),
                code:  newCourseForm.code.trim().toUpperCase(),
                icon:  newCourseForm.icon,
                desc:  newCourseForm.desc.trim() || '暂无课程简介。',
                color: newCourseForm.color,
                files: []
            };
            props.courses.push(newCourse);
            showNewCourseModal.value = false;
            emit('show-toast', `课程《${newCourse.name}》已创建 ✓`, 'success');
        };

        // ── 进入课程 / 返回 ───────────────────────────────────
        const enterCourse = (course) => {
            selectedCourse.value = course;
            renamingFileIdx.value = -1;
            deleteConfirmIdx.value = -1;
        };
        const backToList = () => { selectedCourse.value = null; };

        // ── 课件：重命名 ──────────────────────────────────────
        const renamingFileIdx = ref(-1);
        const renameValue     = ref('');

        const startRename = (idx, file) => {
            renamingFileIdx.value = idx;
            deleteConfirmIdx.value = -1;
            renameValue.value = file.name;
        };
        const confirmRename = (file) => {
            const v = renameValue.value.trim();
            if (!v) { emit('show-toast', '文件名不能为空', 'error'); return; }
            file.name = v;
            renamingFileIdx.value = -1;
            emit('show-toast', '文件名已更新 ✓', 'success');
        };
        const cancelRename = () => { renamingFileIdx.value = -1; };

        // ── 课件：删除 ────────────────────────────────────────
        const deleteConfirmIdx = ref(-1);

        const askDelete = (idx) => {
            deleteConfirmIdx.value = idx;
            renamingFileIdx.value = -1;
        };
        const confirmDelete = (idx) => {
            const removed = selectedCourse.value.files.splice(idx, 1);
            deleteConfirmIdx.value = -1;
            emit('show-toast', `已删除 「${removed[0]?.name}」`, 'success');
        };
        const cancelDelete = () => { deleteConfirmIdx.value = -1; };

        // ── 课件：上传（Mock，读取文件元数据追加列表）────────
        const fileInputRef = ref(null);
        const triggerUpload = () => { fileInputRef.value?.click(); };

        const handleUpload = (e) => {
            const fileList = e.target.files;
            if (!fileList || !fileList.length || !selectedCourse.value) return;
            let addedCount = 0;
            Array.from(fileList).forEach(f => {
                const ext = f.name.split('.').pop().toLowerCase();
                const type = ext === 'pdf' ? 'pdf' : 'ppt';
                const sizeKB = (f.size / 1024).toFixed(0);
                const sizeStr = f.size > 1024 * 1024
                    ? `${(f.size / 1024 / 1024).toFixed(1)} MB`
                    : `${sizeKB} KB`;
                selectedCourse.value.files.push({
                    name: f.name,
                    type,
                    path: `courses/${selectedCourse.value.id}/${f.name}`,
                    size: sizeStr
                });
                addedCount++;
            });
            e.target.value = '';
            emit('show-toast', `已添加 ${addedCount} 个课件记录 ✓（演示模式，仅记录元数据）`, 'success');
        };

        // ── 预览课件（调用父层 previewFile，通过事件代理）────
        // 因组件内部无法直接访问 coursesState，改为 emit 自定义事件让父层处理
        const previewFileItem = (file) => {
            // 通过 window 事件触发父层的预览逻辑（已有 switch-view 模式）
            window.dispatchEvent(new CustomEvent('teacher-preview-file', { detail: file }));
        };

        const getCourseBanner = (courseName) => `./course-banners/${courseName}.png`;

        const hideBrokenBanner = (event) => {
            event.target.classList.add('hidden');
        };

        const showCourseBanner = (event) => {
            event.target.classList.remove('hidden');
        };

        return {
            editMode,
            selectedCourse,
            editingCourse, editForm,
            startEditCourse, saveEditCourse, cancelEditCourse,
            showNewCourseModal, newCourseForm, iconOptions, colorOptions,
            openNewCourseModal, saveNewCourse,
            enterCourse, backToList,
            renamingFileIdx, renameValue,
            startRename, confirmRename, cancelRename,
            deleteConfirmIdx,
            askDelete, confirmDelete, cancelDelete,
            fileInputRef, triggerUpload, handleUpload,
            previewFileItem,
            getCourseBanner, hideBrokenBanner, showCourseBanner,
        };
    },
    template: `
<section class="absolute inset-0 overflow-y-auto p-8 lg:p-12">
    <div class="max-w-5xl mx-auto flex flex-col gap-6">

        <!-- ── 页头 ─────────────────────────────────────────── -->
        <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
            <div class="flex items-center gap-3">
                <button v-if="selectedCourse" @click="backToList"
                    class="text-slate-400 hover:text-[#1c2b38] transition-colors flex items-center gap-1 text-sm">
                    <i class="ph ph-arrow-left"></i> 返回课程列表
                </button>
                <div>
                    <h2 class="text-2xl font-bold text-slate-800" style="font-family:'Noto Serif SC',serif;">
                        {{ selectedCourse ? selectedCourse.name : '课程库管理' }}
                    </h2>
                    <p class="text-sm text-slate-500 mt-1">
                        {{ selectedCourse ? selectedCourse.desc : '管理公共课程库资源，支持课件上传、删除与课程信息维护' }}
                    </p>
                </div>
            </div>

            <div class="flex items-center gap-3 shrink-0">
                <!-- 编辑模式开关：按钮式 pill，关闭=静默锁，开启=琥珀警示 -->
                <button @click="editMode = !editMode"
                    class="relative flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold
                           border-2 transition-all duration-300 select-none overflow-hidden"
                    :class="editMode
                        ? 'bg-amber-500 border-amber-400 text-white shadow-lg shadow-amber-500/30'
                        : 'bg-white/60 border-slate-200 text-slate-500 hover:border-slate-300 hover:text-slate-700'">
                    <!-- 激活时的背景光晕 -->
                    <span v-if="editMode"
                        class="absolute inset-0 bg-gradient-to-r from-amber-400/30 to-orange-400/10 pointer-events-none"></span>
                    <!-- 图标：关闭=锁，开启=铅笔 -->
                    <i :class="editMode ? 'ph-pencil-simple ph' : 'ph-lock-simple ph'"
                        class="text-base relative z-10 transition-all duration-200"></i>
                    <span class="relative z-10 transition-all duration-200">
                        {{ editMode ? '退出编辑' : '编辑模式' }}
                    </span>
                    <!-- 开启时右侧状态点 -->
                    <span v-if="editMode"
                        class="relative z-10 w-1.5 h-1.5 rounded-full bg-white/80 animate-pulse ml-0.5"></span>
                </button>

                <!-- 上传课件（仅在进入课程且编辑模式时显示） -->
                <button v-if="selectedCourse && editMode" @click="triggerUpload"
                    class="px-4 py-2 bg-emerald-500 text-white rounded-xl text-sm font-bold
                           hover:bg-emerald-600 transition-all active:scale-95 flex items-center gap-1.5 shadow-sm">
                    <i class="ph ph-upload-simple"></i> 上传课件
                </button>
                <input ref="fileInputRef" type="file" multiple accept=".pdf,.ppt,.pptx"
                    class="hidden" @change="handleUpload">

                <!-- 新建课程（仅在课程列表且编辑模式时显示） -->
                <button v-if="!selectedCourse && editMode" @click="openNewCourseModal"
                    class="px-4 py-2 bg-[#1c2b38] text-white rounded-xl text-sm font-bold
                           hover:bg-[#253645] transition-all active:scale-95 flex items-center gap-1.5 shadow-sm">
                    <i class="ph ph-plus"></i> 新建课程
                </button>
            </div>
        </div>

        <!-- ── 编辑模式提示条 ──────────────────────────────── -->
        <transition name="fade">
            <div v-if="editMode"
                class="flex items-center gap-3 px-4 py-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-700 text-sm">
                <i class="ph ph-pencil-simple text-amber-500 text-lg"></i>
                <span><strong>编辑模式已开启</strong>：您现在可以修改课程信息、增删课件。关闭开关退出编辑。</span>
            </div>
        </transition>

        <!-- ════════════════════════════════════════════════════
             课程列表（未选中课程时显示）
        ════════════════════════════════════════════════════ -->
        <div v-if="!selectedCourse" class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div v-for="course in courses" :key="course.id"
                class="group relative glass-panel-liquid overflow-hidden transition-all duration-500"
                :class="editMode ? 'ring-2 ring-amber-300/40' : 'hover:-translate-y-1 cursor-pointer'"
                @click="!editMode && enterCourse(course)">

                <!-- 课程卡片头部色条 -->
                <div class="h-32 relative overflow-hidden bg-slate-100 flex items-center justify-center"
                    :class="'bg-gradient-to-br ' + course.color">
                    <i :class="['ph text-5xl text-white/30 transition-transform duration-500 group-hover:scale-110', course.icon]"></i>
                    <img :key="course.name"
                        :src="getCourseBanner(course.name)"
                        :alt="course.name"
                        class="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-700 ease-out"
                        @load="showCourseBanner"
                        @error="hideBrokenBanner">
                    <div class="absolute inset-0 bg-gradient-to-t from-black/20 via-transparent to-transparent"></div>
                </div>

                <!-- 卡片内容 -->
                <div class="p-5">
                    <!-- 非编辑状态 -->
                    <template v-if="editingCourse !== course">
                        <div class="flex items-start justify-between mb-2 gap-2">
                            <h3 class="font-bold text-slate-800 text-lg leading-tight">{{ course.name }}</h3>
                            <span class="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full font-mono shrink-0 mt-1">
                                {{ course.code }}
                            </span>
                        </div>
                        <p class="text-sm text-slate-500 leading-relaxed mb-4 line-clamp-2">{{ course.desc }}</p>
                        <div class="flex items-center justify-between">
                            <span class="text-xs text-slate-400">
                                <i class="ph ph-files"></i> {{ course.files.length }} 个课件
                            </span>
                            <div class="flex items-center gap-2">
                                <!-- 编辑模式操作按钮 -->
                                <template v-if="editMode">
                                    <button @click.stop="startEditCourse(course, $event)"
                                        class="px-3 py-1.5 text-xs font-bold bg-amber-100 text-amber-700
                                               rounded-lg hover:bg-amber-200 transition-colors flex items-center gap-1">
                                        <i class="ph ph-pencil-simple"></i> 编辑信息
                                    </button>
                                    <button @click.stop="enterCourse(course)"
                                        class="px-3 py-1.5 text-xs font-bold bg-[#1c2b38] text-white
                                               rounded-lg hover:bg-[#253645] transition-colors flex items-center gap-1">
                                        <i class="ph ph-folder-open"></i> 管理课件
                                    </button>
                                </template>
                                <!-- 正常浏览模式 -->
                                <template v-else>
                                    <span class="text-xs text-[#b91c1c] font-bold group-hover:translate-x-1
                                                 transition-transform inline-flex items-center gap-1">
                                        进入管理 <i class="ph ph-arrow-right"></i>
                                    </span>
                                </template>
                            </div>
                        </div>
                    </template>

                    <!-- 编辑课程信息内联表单 -->
                    <template v-if="editingCourse === course">
                        <div class="flex flex-col gap-3">
                            <div>
                                <label class="text-xs font-semibold text-slate-500 mb-1 block">课程名称</label>
                                <input v-model="editForm.name" type="text"
                                    class="w-full text-sm bg-white/80 border border-amber-300 text-slate-800
                                           rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-amber-400/40 transition-all"
                                    placeholder="课程名称">
                            </div>
                            <div class="grid grid-cols-2 gap-2">
                                <div>
                                    <label class="text-xs font-semibold text-slate-500 mb-1 block">课程编号</label>
                                    <input v-model="editForm.code" type="text"
                                        class="w-full text-sm bg-white/80 border border-amber-300 text-slate-800
                                               rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-amber-400/40 transition-all"
                                        placeholder="CS201">
                                </div>
                            </div>
                            <div>
                                <label class="text-xs font-semibold text-slate-500 mb-1 block">课程描述</label>
                                <textarea v-model="editForm.desc" rows="2"
                                    class="w-full text-sm bg-white/80 border border-amber-300 text-slate-800
                                           rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-amber-400/40
                                           transition-all resize-none"
                                    placeholder="课程简介..."></textarea>
                            </div>
                            <div class="flex gap-2 pt-1">
                                <button @click="saveEditCourse"
                                    class="flex-1 py-2 bg-[#1c2b38] text-white text-xs font-bold rounded-lg
                                           hover:bg-[#253645] transition-colors flex items-center justify-center gap-1">
                                    <i class="ph ph-floppy-disk"></i> 保存
                                </button>
                                <button @click="cancelEditCourse"
                                    class="flex-1 py-2 bg-slate-100 text-slate-600 text-xs font-bold rounded-lg
                                           hover:bg-slate-200 transition-colors">
                                    取消
                                </button>
                            </div>
                        </div>
                    </template>
                </div>
            </div>

            <!-- 空状态 / 新建课程占位卡 -->
            <div v-if="editMode" @click="openNewCourseModal"
                class="border-2 border-dashed border-slate-300/60 rounded-2xl flex flex-col items-center
                       justify-center text-slate-400 min-h-[200px] cursor-pointer
                       hover:border-[#1c2b38]/30 hover:text-[#1c2b38] hover:bg-[#1c2b38]/5 transition-all">
                <i class="ph ph-plus-circle text-4xl mb-2"></i>
                <p class="text-sm font-medium">新建课程</p>
            </div>
        </div>

        <!-- ════════════════════════════════════════════════════
             课件文件管理（已选中课程时显示）
        ════════════════════════════════════════════════════ -->
        <div v-if="selectedCourse" class="bg-white rounded-2xl border border-slate-200/80 shadow-soft overflow-hidden">
            <!-- 课件数量统计 -->
            <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
                <span class="text-sm text-slate-500">
                    <i class="ph ph-files text-slate-400"></i>
                    共 <strong class="text-slate-700">{{ selectedCourse.files.length }}</strong> 个课件
                </span>
                <span v-if="editMode" class="text-xs text-amber-600 font-semibold flex items-center gap-1">
                    <i class="ph ph-pencil-simple"></i> 编辑模式
                </span>
            </div>

            <!-- 课件列表 -->
            <div v-if="selectedCourse.files.length > 0" class="divide-y divide-slate-100">
                <div v-for="(file, idx) in selectedCourse.files" :key="idx"
                    class="flex items-center gap-4 px-6 py-4 hover:bg-slate-50 transition-colors group"
                    :class="deleteConfirmIdx === idx ? 'bg-red-50/60' : ''">

                    <!-- 文件图标 -->
                    <div :class="['w-10 h-10 rounded-xl flex items-center justify-center shrink-0',
                        file.type === 'pdf' ? 'bg-red-50' : 'bg-amber-50']">
                        <i :class="['ph text-xl', file.type === 'pdf' ? 'ph-file-pdf text-red-500' : 'ph-presentation text-amber-500']"></i>
                    </div>

                    <!-- 文件信息 / 重命名输入框 -->
                    <div class="flex-1 min-w-0">
                        <!-- 重命名模式 -->
                        <template v-if="renamingFileIdx === idx">
                            <input v-model="renameValue" type="text" autofocus
                                @keydown.enter="confirmRename(file)"
                                @keydown.esc="cancelRename"
                                class="w-full text-sm bg-white border border-amber-300 text-slate-800
                                       rounded-lg px-3 py-1.5 outline-none focus:ring-2 focus:ring-amber-400/40 transition-all">
                        </template>
                        <!-- 正常显示 -->
                        <template v-else>
                            <p class="font-medium text-slate-700 text-sm truncate">{{ file.name }}</p>
                            <p class="text-xs text-slate-400 mt-0.5">
                                <span :class="['inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold mr-1',
                                    file.type === 'pdf' ? 'bg-red-100 text-red-600' : 'bg-amber-100 text-amber-600']">
                                    {{ file.type === 'pdf' ? 'PDF' : 'PPT' }}
                                </span>
                                {{ file.size }}
                            </p>
                        </template>
                    </div>

                    <!-- 操作按钮区 -->
                    <div class="flex items-center gap-2 shrink-0">

                        <!-- 重命名确认 / 取消 -->
                        <template v-if="renamingFileIdx === idx">
                            <button @click="confirmRename(file)"
                                class="px-3 py-1.5 bg-[#1c2b38] text-white rounded-lg text-xs font-bold
                                       hover:bg-[#253645] transition-colors flex items-center gap-1">
                                <i class="ph ph-check"></i> 确认
                            </button>
                            <button @click="cancelRename"
                                class="px-3 py-1.5 bg-slate-100 text-slate-600 rounded-lg text-xs font-bold
                                       hover:bg-slate-200 transition-colors">
                                取消
                            </button>
                        </template>

                        <!-- 删除确认 / 取消 -->
                        <template v-else-if="deleteConfirmIdx === idx">
                            <span class="text-xs text-red-600 font-medium mr-1">确认删除？</span>
                            <button @click="confirmDelete(idx)"
                                class="px-3 py-1.5 bg-[#b91c1c] text-white rounded-lg text-xs font-bold
                                       hover:bg-[#991b1b] transition-colors flex items-center gap-1">
                                <i class="ph ph-trash"></i> 删除
                            </button>
                            <button @click="cancelDelete"
                                class="px-3 py-1.5 bg-slate-100 text-slate-600 rounded-lg text-xs font-bold
                                       hover:bg-slate-200 transition-colors">
                                取消
                            </button>
                        </template>

                        <!-- 正常操作按钮 -->
                        <template v-else>
                            <!-- 预览（始终可见） -->
                            <button @click="previewFileItem(file)"
                                class="px-3 py-1.5 bg-[#b91c1c] text-white rounded-lg text-xs font-bold
                                       hover:bg-[#991b1b] transition-colors flex items-center gap-1
                                       opacity-0 group-hover:opacity-100">
                                <i class="ph ph-eye"></i> 预览
                            </button>
                            <!-- 编辑模式额外操作 -->
                            <template v-if="editMode">
                                <button @click="startRename(idx, file)"
                                    class="px-3 py-1.5 bg-amber-100 text-amber-700 rounded-lg text-xs font-bold
                                           hover:bg-amber-200 transition-colors flex items-center gap-1
                                           opacity-0 group-hover:opacity-100">
                                    <i class="ph ph-pencil-simple"></i> 重命名
                                </button>
                                <button @click="askDelete(idx)"
                                    class="px-3 py-1.5 bg-red-100 text-red-600 rounded-lg text-xs font-bold
                                           hover:bg-red-200 transition-colors flex items-center gap-1
                                           opacity-0 group-hover:opacity-100">
                                    <i class="ph ph-trash"></i> 删除
                                </button>
                            </template>
                        </template>
                    </div>
                </div>
            </div>

            <!-- 课件为空占位 -->
            <div v-else class="flex flex-col items-center justify-center py-16 text-slate-400">
                <i class="ph ph-folder-open text-5xl mb-3 opacity-40"></i>
                <p class="text-sm font-medium mb-1">该课程暂无课件</p>
                <p v-if="editMode" class="text-xs">开启编辑模式后点击右上角「上传课件」按钮添加</p>
                <button v-if="editMode" @click="triggerUpload"
                    class="mt-4 px-4 py-2 bg-emerald-500 text-white rounded-xl text-sm font-bold
                           hover:bg-emerald-600 transition-colors flex items-center gap-1.5">
                    <i class="ph ph-upload-simple"></i> 立即上传
                </button>
            </div>
        </div>

        <!-- ════════════════════════════════════════════════════
             新建课程弹窗
        ════════════════════════════════════════════════════ -->
        <transition name="fade">
            <div v-if="showNewCourseModal"
                class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm"
                @click.self="showNewCourseModal = false">
                <div class="bg-white/95 backdrop-blur-xl rounded-3xl shadow-float w-full max-w-md
                            overflow-hidden border border-white flex flex-col max-h-[90vh]">
                    <!-- 弹窗头部 -->
                    <div class="px-6 py-4 border-b border-white/20 flex justify-between items-center bg-white/40">
                        <h3 class="text-lg font-bold text-slate-800 flex items-center gap-2"
                            style="font-family:'Noto Serif SC',serif;">
                            <i class="ph ph-plus-circle text-[#1c2b38]"></i> 新建课程
                        </h3>
                        <button @click="showNewCourseModal = false"
                            class="text-slate-400 hover:text-slate-700 transition-colors">
                            <i class="ph ph-x text-xl"></i>
                        </button>
                    </div>

                    <!-- 弹窗主体 -->
                    <div class="p-6 overflow-y-auto flex-1 flex flex-col gap-4">
                        <div>
                            <label class="block text-xs font-semibold text-slate-600 mb-1.5">课程名称 *</label>
                            <input v-model="newCourseForm.name" type="text" placeholder="例如：操作系统"
                                class="w-full bg-white/60 border border-white text-slate-800 text-sm rounded-xl
                                       focus:ring-2 focus:ring-[#1c2b38]/20 focus:border-[#1c2b38] px-3 py-2.5 outline-none transition-all">
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-slate-600 mb-1.5">课程编号 *</label>
                            <input v-model="newCourseForm.code" type="text" placeholder="例如：CS301"
                                class="w-full bg-white/60 border border-white text-slate-800 text-sm rounded-xl
                                       focus:ring-2 focus:ring-[#1c2b38]/20 focus:border-[#1c2b38] px-3 py-2.5 outline-none transition-all">
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-slate-600 mb-1.5">课程描述</label>
                            <textarea v-model="newCourseForm.desc" rows="3"
                                placeholder="简要描述课程内容..."
                                class="w-full bg-white/60 border border-white text-slate-800 text-sm rounded-xl
                                       focus:ring-2 focus:ring-[#1c2b38]/20 focus:border-[#1c2b38] px-3 py-2.5 outline-none
                                       transition-all resize-none"></textarea>
                        </div>

                        <!-- 图标选择 -->
                        <div>
                            <label class="block text-xs font-semibold text-slate-600 mb-1.5">课程图标</label>
                            <div class="flex gap-2 flex-wrap">
                                <button v-for="icon in iconOptions" :key="icon"
                                    @click="newCourseForm.icon = icon"
                                    class="w-10 h-10 rounded-xl flex items-center justify-center text-lg border-2 transition-all"
                                    :class="newCourseForm.icon === icon
                                        ? 'border-[#1c2b38] bg-[#1c2b38] text-white shadow-md scale-110'
                                        : 'border-slate-200 bg-white text-slate-600 hover:border-slate-400'">
                                    <i :class="'ph ' + icon"></i>
                                </button>
                            </div>
                        </div>

                        <!-- 颜色主题选择 -->
                        <div>
                            <label class="block text-xs font-semibold text-slate-600 mb-1.5">卡片主题色</label>
                            <div class="flex gap-2">
                                <button v-for="opt in colorOptions" :key="opt.value"
                                    @click="newCourseForm.color = opt.value"
                                    class="flex-1 h-8 rounded-lg border-2 bg-gradient-to-r transition-all"
                                    :class="[opt.value, newCourseForm.color === opt.value
                                        ? 'border-slate-800 scale-105 shadow-md'
                                        : 'border-transparent hover:scale-105']"
                                    :title="opt.label">
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- 弹窗底部 -->
                    <div class="px-6 py-4 border-t border-white/20 bg-white/40 flex justify-end gap-3">
                        <button @click="showNewCourseModal = false"
                            class="px-5 py-2.5 rounded-xl text-sm font-medium text-slate-600
                                   bg-white/60 border border-white hover:bg-white transition-colors">
                            取消
                        </button>
                        <button @click="saveNewCourse"
                            class="px-5 py-2.5 rounded-xl text-sm font-medium text-white
                                   bg-[#1c2b38] hover:bg-[#253645] transition-colors flex items-center gap-2">
                            <i class="ph ph-floppy-disk"></i> 创建课程
                        </button>
                    </div>
                </div>
            </div>
        </transition>

    </div>
</section>
    `
};
