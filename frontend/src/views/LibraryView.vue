<script setup lang="ts">
import { BookOpen, CheckSquare, ChevronDown, ChevronRight, Layers, MoveRight, Play, Trash2, X } from 'lucide-vue-next'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { del, get, post } from '../api'
import { confirmDialog } from '../platform/dialogs'
import { platformRuntime } from '../platform/runtime'
import OptionSheet from '../components/OptionSheet.vue'
import QuestionBankSwitcher from '../components/QuestionBankSwitcher.vue'
import { loadQuestionBankProfiles, questionBankProfilesState } from '../services/questionBankProfiles'

const router = useRouter()
const papers = ref<any[]>([])
const error = ref('')
const batchMode = ref(false)
const selectedIds = ref<Set<number>>(new Set())
const moveDialogOpen = ref(false)
const moveTargetId = ref<number>(0)
let holdTimer: number | null = null

// 展开查看章节子组
const expandedPaperId = ref<number | null>(null)
const paperUnitsMap = ref<Record<number, any[]>>({})
const loadingUnits = ref<number | null>(null)

const emptyHint = platformRuntime.isAndroid
  ? '请先到“导入题库”选择 ESQ 题库包。'
  : '请先到“导入题库”上传题库文件。'

const moveTargets = () => questionBankProfilesState.items.filter(
  item => Number(item.id) !== questionBankProfilesState.activeId,
)

async function loadPapers() {
  selectedIds.value = new Set()
  expandedPaperId.value = null
  paperUnitsMap.value = {}
  try { papers.value = await get('/papers') } catch (e) { error.value = String(e) }
}

function reloadAfterAndroidStartup(event: Event) {
  if ((event as CustomEvent).detail?.needsHomeRefresh === true || (event as CustomEvent).detail?.changed === true) {
    void Promise.all([loadPapers(), loadQuestionBankProfiles()])
  }
}

onMounted(async () => {
  window.addEventListener('android-startup-prepared', reloadAfterAndroidStartup)
  await Promise.all([loadPapers(), loadQuestionBankProfiles()])
})

onBeforeUnmount(() => {
  window.removeEventListener('android-startup-prepared', reloadAfterAndroidStartup)
})

async function toggleExpand(paperId: number) {
  if (expandedPaperId.value === paperId) {
    expandedPaperId.value = null
    return
  }
  expandedPaperId.value = paperId
  if (!paperUnitsMap.value[paperId]) {
    loadingUnits.value = paperId
    try {
      const units = await get<any[]>(`/papers/${paperId}/units`)
      paperUnitsMap.value[paperId] = Array.isArray(units) ? units : []
    } catch (e) {
      error.value = '加载章节小节失败：' + String(e)
    } finally {
      loadingUnits.value = null
    }
  }
}

async function startPaper(id: number) {
  try {
    const session: any = await post('/practice/sessions', {
      mode: 'paper', paper_id: id, shuffle_options: true,
    })
    router.push(`/practice/${session.id}`)
  } catch (e) { error.value = String(e) }
}

async function startSingleUnit(paperId: number, unitId: number) {
  try {
    const session: any = await post('/practice/sessions', {
      mode: 'unit', paper_id: paperId, unit_ids: [unitId], shuffle_options: true,
    })
    router.push(`/practice/${session.id}`)
  } catch (e) { error.value = String(e) }
}

async function restartPaper(id: number) {
  const confirmed = await confirmDialog({
    title: '重新开始本章练习？',
    message: [
      '重新开始会重置本章未完成的练习进度。',
      '已提交判分的历史成绩仍会保留。',
    ],
    confirmLabel: '重新开始',
  })
  if (!confirmed) return
  try {
    const session: any = await post('/practice/sessions', {
      mode: 'paper', paper_id: id, shuffle_options: true, force_new: true,
    })
    router.push(`/practice/${session.id}`)
  } catch (e) { error.value = String(e) }
}

function scoreText(paper: any) {
  const fmt = (value: number) => (Number.isFinite(value) && Number.isInteger(value) ? String(value) : value.toFixed(1))
  return `${fmt(Number(paper.last_score) || 0)}/${fmt(Number(paper.last_max_score) || 0)}`
}

function togglePaper(id: number) {
  if (!batchMode.value) return
  const next = new Set(selectedIds.value)
  next.has(id) ? next.delete(id) : next.add(id)
  selectedIds.value = next
}

function beginHold(id: number) {
  if (holdTimer !== null) window.clearTimeout(holdTimer)
  holdTimer = window.setTimeout(() => {
    batchMode.value = true
    togglePaper(id)
  }, 520)
}

function cancelHold() {
  if (holdTimer !== null) window.clearTimeout(holdTimer)
  holdTimer = null
}

function leaveBatch() {
  batchMode.value = false
  selectedIds.value = new Set()
}

async function moveSelected() {
  const targets = moveTargets()
  if (!targets.length) {
    error.value = '请先新建另一个题库配置'
    return
  }
  moveTargetId.value = Number(targets[0].id)
  moveDialogOpen.value = true
}

async function confirmMoveSelected() {
  const targetId = Number(moveTargetId.value)
  if (!moveTargets().some(item => Number(item.id) === targetId)) return
  moveDialogOpen.value = false
  try {
    await post('/papers/batch-move', {
      paper_ids: [...selectedIds.value],
      target_profile_id: targetId,
    })
    leaveBatch()
    await loadPapers()
  } catch (cause) { error.value = String(cause) }
}

async function deleteSelected() {
  if (!selectedIds.value.size) return
  const confirmed = await confirmDialog({
    title: `将选中的 ${selectedIds.value.size} 个章节移入回收站？`,
    message: [
      '移动后这些章节不再出现在当前题库练习列表。',
      '内容将在回收站保留七天，期间可以恢复。',
    ],
    confirmLabel: '移入回收站',
    danger: true,
  })
  if (!confirmed) return
  try {
    for (const id of selectedIds.value) await del(`/papers/${id}`)
    leaveBatch()
    await loadPapers()
  } catch (cause) { error.value = String(cause) }
}
</script>

<template>
  <div class="page">
    <div class="page-head"><div><h1>按章节特训</h1></div></div>
    <QuestionBankSwitcher :show-library-link="true" class="library-bank-switcher" @changed="loadPapers">
      <template #actions>
        <span v-if="batchMode" class="bank-batch-status">已选 {{ selectedIds.size }} 章</span>
        <button v-if="!batchMode" class="button secondary compact" type="button" @click="batchMode=true"><CheckSquare :size="16" />批量管理</button>
        <template v-else>
          <button class="button secondary compact" type="button" :disabled="!selectedIds.size" @click="moveSelected"><MoveRight :size="16" />移动</button>
          <button class="button ghost danger compact" type="button" :disabled="!selectedIds.size" @click="deleteSelected"><Trash2 :size="16" />移入回收站</button>
          <button class="button ghost compact" type="button" @click="leaveBatch"><X :size="16" />取消</button>
        </template>
      </template>
    </QuestionBankSwitcher>
    <div v-if="error" class="warning">{{ error }}</div>
    
    <div v-if="papers.length" class="chapter-list">
      <article
        class="card paper-card chapter-card selectable"
        :class="{ selected: selectedIds.has(paper.id) }"
        v-for="paper in papers"
        :key="paper.id"
        @pointerdown="beginHold(paper.id)"
        @pointerup="cancelHold"
        @pointerleave="cancelHold"
      >
        <label v-if="batchMode" class="selection-option" @click.stop @pointerdown.stop>
          <input type="checkbox" :checked="selectedIds.has(paper.id)" aria-label="选择章节" @change="togglePaper(paper.id)">
          <span>选择章节</span>
        </label>
        
        <div class="paper-card-head">
          <span v-if="paper.active_session_id" class="pill">进行中 · 已做 {{ paper.active_done }}/{{ paper.unit_count }} 组</span>
          <span v-else-if="paper.last_score != null" class="pill">{{ scoreText(paper) }}</span>
          <span v-else class="pill pill-soft">{{ paper.unit_count }} 组 · {{ paper.question_count }} 题</span>
          <BookOpen :size="20" />
        </div>
        
        <div class="chapter-info-main" @click="!batchMode && toggleExpand(paper.id)" style="cursor: pointer;">
          <h3>{{ paper.title }}</h3>
          <p class="lead" style="display:flex;align-items:center;gap:6px">
            <span>{{ paper.subject }}</span>
            <span style="opacity:0.6">|</span>
            <span style="color:var(--primary);display:inline-flex;align-items:center">
              {{ expandedPaperId === paper.id ? '收起小节目录' : '展开小节目录' }}
              <ChevronDown v-if="expandedPaperId === paper.id" :size="16" />
              <ChevronRight v-else :size="16" />
            </span>
          </p>
        </div>

        <!-- 章节子组目录展开区 -->
        <div v-if="expandedPaperId === paper.id" class="chapter-units-panel" style="margin: 12px 0 14px; padding: 12px; background: rgba(0,0,0,0.03); border-radius: 12px;">
          <div v-if="loadingUnits === paper.id" style="font-size: 13px; color: var(--text-muted); text-align: center; padding: 10px;">
            正在加载小节目录…
          </div>
          <div v-else-if="paperUnitsMap[paper.id]?.length" class="units-sublist" style="display: flex; flex-direction: column; gap: 8px;">
            <div
              v-for="unit in paperUnitsMap[paper.id]"
              :key="unit.id"
              class="unit-row-item"
              style="display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; font-size: 13px;"
            >
              <div style="display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0;">
                <Layers :size="16" style="color: var(--primary); flex-shrink: 0;" />
                <span style="font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                  {{ unit.title }}
                </span>
                <span v-if="unit.is_submitted" style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background: rgba(16, 185, 129, 0.1); color: var(--success);">
                  已练 (错 {{ unit.wrong_count ?? 0 }})
                </span>
              </div>
              <button
                class="button compact secondary"
                type="button"
                style="margin-left: 10px; flex-shrink: 0;"
                @click.stop="startSingleUnit(paper.id, unit.id)"
              >
                <Play :size="13" />练这组
              </button>
            </div>
          </div>
          <div v-else style="font-size: 13px; color: var(--text-muted); text-align: center;">暂无小节数据</div>
        </div>
        
        <div class="paper-actions">
          <button class="button paper-primary-action" :disabled="paper.status !== 'published' || batchMode" @click.stop="startPaper(paper.id)">
            <Play :size="16" />{{ paper.active_session_id ? '继续本章' : '整章通刷' }}
          </button>
          <button v-if="paper.active_session_id" class="button ghost paper-restart-action" :disabled="batchMode" @click.stop="restartPaper(paper.id)">
            重置
          </button>
        </div>
      </article>
    </div>
    
    <div v-else class="card empty illustrated-empty">
      <img src="/assets/quiet-study-empty.webp" alt="" />
      <strong>题库还是空的</strong>
      <p>{{ emptyHint }}</p>
    </div>

    <section v-if="moveDialogOpen" class="app-overlay" role="presentation" @click.self="moveDialogOpen=false">
      <div class="app-dialog" role="dialog" aria-modal="true" aria-labelledby="move-dialog-title">
        <header class="app-dialog-head"><h2 id="move-dialog-title">移动到哪个题库配置？</h2></header>
        <div class="app-dialog-body">
          <p>将选中的 {{ selectedIds.size }} 个章节移动到目标配置；移动后可在该配置下继续练习。</p>
          <OptionSheet v-model="moveTargetId" :items="moveTargets().map(item => ({ value: Number(item.id), label: item.name }))" title="选择目标题库配置" />
        </div>
        <footer class="app-dialog-actions">
          <button class="button secondary" type="button" @click="moveDialogOpen=false">取消</button>
          <button class="button" type="button" @click="confirmMoveSelected">移动</button>
        </footer>
      </div>
    </section>
  </div>
</template>

<style scoped>
.chapter-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.chapter-card {
  width: 100%;
}
.pill-soft {
  background: rgba(0, 0, 0, 0.05);
  color: var(--text-muted);
}
</style>
