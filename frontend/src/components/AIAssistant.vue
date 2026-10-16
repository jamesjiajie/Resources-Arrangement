<template>
  <button class="ai-launcher" type="button" :aria-label="labels.title" :aria-expanded="open" @click="toggle">✦ {{ labels.title }}</button>
  <aside v-if="open" class="ai-panel" :class="{ expanded }" role="dialog" :aria-label="labels.title">
    <header class="ai-header">
      <div><strong>{{ labels.title }}</strong><small>{{ context }}</small></div>
      <button type="button" :title="labels.history" @click="showHistory = !showHistory">{{ labels.history }}</button>
      <button type="button" :title="labels.newChat" @click="newChat">＋</button>
      <button type="button" :title="labels.expand" @click="expanded = !expanded">{{ expanded ? '↘' : '⤢' }}</button>
      <button type="button" :title="labels.close" @click="open = false">×</button>
    </header>

    <div v-if="showHistory" class="ai-history">
      <button v-for="item in conversations" :key="item.id" type="button" :class="{ active: item.id === conversationId }" @click="selectChat(item.id)">{{ item.title }}</button>
      <p v-if="!conversations.length">{{ labels.noHistory }}</p>
      <button v-if="conversationId" class="ai-delete" type="button" @click="deleteChat">{{ labels.deleteChat }}</button>
    </div>

    <div v-else ref="feed" class="ai-feed" aria-live="polite">
      <div v-if="!messages.length" class="ai-welcome">
        <strong>{{ labels.welcome }}</strong>
        <p>{{ labels.explainer }}</p>
        <button type="button" @click="draft = labels.example">{{ labels.example }}</button>
      </div>
      <article v-for="(message, index) in messages" :key="index" class="ai-message" :class="message.role">
        <span>{{ message.role === 'user' ? labels.you : labels.title }}</span>
        <p>{{ message.content || (busy ? labels.thinking : '') }}</p>
        <small v-if="message.created_at">{{ message.created_at.replace('T', ' ') }}</small>
        <div v-if="message.sources?.length" class="ai-sources">
          <button v-for="source in message.sources" :key="source.ref" type="button" @click="inspectSource(source)">[{{ source.ref }}] {{ source.label }}</button>
        </div>
      </article>
      <p v-if="error" class="ai-error" role="alert">{{ error }}</p>
    </div>

    <div v-if="sourceDetail" class="ai-source-detail">
      <div><strong>{{ sourceDetail.label }}</strong><button type="button" @click="sourceDetail = null">×</button></div>
      <pre>{{ sourceDetail.record }}</pre>
      <button v-if="!['activity', 'import'].includes(sourceDetail.source.kind)" type="button" @click="goToSource">{{ labels.goToRecord }}</button>
    </div>

    <form class="ai-composer" @submit.prevent="send">
      <small v-if="!configured">{{ labels.notConfigured }}</small>
      <div class="ai-focus">
        <select v-model="focusKind" :aria-label="labels.focus" @change="focusId = ''"><option value="all">{{ labels.allData }}</option><option value="member">{{ labels.member }}</option><option value="project">{{ labels.project }}</option></select>
        <select v-if="focusKind !== 'all'" v-model="focusId" :aria-label="labels.focusRecord"><option value="">{{ labels.chooseRecord }}</option><option v-for="item in focusOptions" :key="item.id" :value="String(item.id)">{{ item.name }}</option></select>
      </div>
      <textarea v-model="draft" rows="2" :placeholder="labels.placeholder" :aria-label="labels.placeholder" :disabled="busy" @keydown.enter.exact.prevent="send"></textarea>
      <div><span>{{ labels.scope }}</span><button v-if="busy" type="button" @click="stop">{{ labels.stop }}</button><button v-else type="submit" :disabled="!draft.trim() || !configured || (focusKind !== 'all' && !focusId)">{{ labels.send }}</button></div>
    </form>
  </aside>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue';

const props = defineProps({ language: { type: String, default: 'zh' }, context: { type: String, default: '' }, members: { type: Array, default: () => [] }, projects: { type: Array, default: () => [] } });
const emit = defineEmits(['navigate']);
const labels = computed(() => props.language === 'en' ? {
  title: 'AI Assistant', history: 'History', newChat: 'New chat', expand: 'Expand', close: 'Close', noHistory: 'No conversations yet', deleteChat: 'Delete conversation',
  welcome: 'Ask about your portal data', explainer: 'Answers use saved records and show their sources.', example: 'Who has capacity for a new project next month, and why?',
  you: 'You', thinking: 'Reading records…', notConfigured: 'Set AGNES_API_KEY on the portal server to enable answers.', placeholder: 'Ask a question…',
  goToRecord: 'Open record', scope: 'Saved portal data · Read only', stop: 'Stop', send: 'Send', focus: 'Question focus', allData: 'All data', member: 'Member', project: 'Project', focusRecord: 'Selected record', chooseRecord: 'Choose a record',
} : {
  title: 'AI 助手', history: '历史', newChat: '新对话', expand: '展开', close: '关闭', noHistory: '暂无对话', deleteChat: '删除对话',
  welcome: '问问 portal 里的资料', explainer: '回答基于已保存记录，并标注来源。', example: '下个月接新项目，谁有余量，依据是什么？',
  you: '你', thinking: '正在读取资料…', notConfigured: '请在 portal 服务端配置 AGNES_API_KEY 后启用。', placeholder: '输入问题…',
  goToRecord: '定位记录', scope: '全部已保存资料 · 只读', stop: '停止', send: '发送', focus: '提问焦点', allData: '全部资料', member: '指定同事', project: '指定项目', focusRecord: '指定记录', chooseRecord: '选择记录',
});
const open = ref(false);
const expanded = ref(false);
const showHistory = ref(false);
const configured = ref(false);
const conversations = ref([]);
const conversationId = ref('');
const messages = ref([]);
const draft = ref('');
const busy = ref(false);
const error = ref('');
const feed = ref(null);
const sourceDetail = ref(null);
const focusKind = ref('all');
const focusId = ref('');
const focusOptions = computed(() => focusKind.value === 'member' ? props.members : props.projects);
let controller;

async function api(path, options) {
  const response = await fetch(`/api/assistant${path}`, { headers: { 'Content-Type': 'application/json' }, ...options });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  return data;
}
async function refresh() {
  const data = await api('/conversations');
  configured.value = data.configured;
  conversations.value = data.conversations;
}
async function toggle() {
  open.value = !open.value;
  if (open.value) {
    try {
      await refresh();
      const saved = localStorage.getItem('assistant-conversation-id');
      if (!conversationId.value && saved && conversations.value.some(item => item.id === saved)) await selectChat(saved);
    } catch (exc) { error.value = exc.message; }
  }
}
async function selectChat(id) {
  if (busy.value) stop();
  try {
    const data = await api(`/conversations/${id}`);
    conversationId.value = id;
    localStorage.setItem('assistant-conversation-id', id);
    messages.value = data.messages;
    showHistory.value = false;
    error.value = '';
    await scrollDown();
  } catch (exc) { error.value = exc.message; }
}
function newChat() {
  if (busy.value) stop();
  conversationId.value = '';
  localStorage.removeItem('assistant-conversation-id');
  messages.value = [];
  draft.value = '';
  error.value = '';
  sourceDetail.value = null;
  showHistory.value = false;
}
async function deleteChat() {
  if (!conversationId.value || !confirm(props.language === 'en' ? 'Delete this conversation?' : '删除这段对话？')) return;
  try {
    if (busy.value) stop();
    await api(`/conversations/${conversationId.value}`, { method: 'DELETE' });
    newChat();
    await refresh();
  } catch (exc) { error.value = exc.message; }
}
function stop() { controller?.abort(); busy.value = false; }
async function scrollDown() { await nextTick(); feed.value?.scrollTo({ top: feed.value.scrollHeight }); }

async function send() {
  const question = draft.value.trim();
  if (!question || busy.value || !configured.value || (focusKind.value !== 'all' && !focusId.value)) return;
  busy.value = true;
  error.value = '';
  controller = new AbortController();
  const signal = controller.signal;
  try {
    if (!conversationId.value) {
      const created = await api('/conversations', { method: 'POST', signal });
      conversationId.value = created.id;
      localStorage.setItem('assistant-conversation-id', created.id);
    }
    if (messages.value.at(-1)?.role !== 'user' || messages.value.at(-1)?.content !== question) messages.value.push({ role: 'user', content: question });
    messages.value.push({ role: 'assistant', content: '', sources: [] });
    draft.value = '';
    await scrollDown();
    const response = await fetch(`/api/assistant/conversations/${conversationId.value}/messages`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, page_context: `${props.context}；提问焦点：${focusKind.value === 'all' ? '全部资料' : `${focusKind.value} ${focusId.value} ${focusOptions.value.find(item => String(item.id) === focusId.value)?.name || '未选定'}`}` }), signal,
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || `HTTP ${response.status}`);
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let completed = false;
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      const parts = buffer.split('\n\n');
      buffer = parts.pop();
      for (const part of parts) {
        const line = part.split('\n').find(item => item.startsWith('data: '));
        if (!line) continue;
        const event = JSON.parse(line.slice(6));
        if (event.type === 'delta') messages.value.at(-1).content += event.text;
        if (event.type === 'done') { messages.value.at(-1).sources = event.sources; completed = true; }
        if (event.type === 'error') throw new Error(event.message);
      }
      await scrollDown();
      if (done) break;
    }
    if (!completed) throw new Error(props.language === 'en' ? 'Answer was interrupted.' : '回答中断，请重试。');
    await refresh();
  } catch (exc) {
    if (exc.name !== 'AbortError') error.value = exc.message;
    if (messages.value.at(-1)?.role === 'assistant') messages.value.pop();
    if (draft.value === '') draft.value = question;
  } finally { busy.value = false; controller = null; }
}
async function inspectSource(source) {
  try {
    const data = await api(`/sources/${encodeURIComponent(source.kind)}/${encodeURIComponent(source.id)}`);
    sourceDetail.value = { label: source.label, source, record: typeof data.record === 'string' ? data.record : JSON.stringify(data.record, null, 2) };
  } catch (exc) { error.value = exc.message; }
}
function goToSource() {
  emit('navigate', sourceDetail.value.source);
  sourceDetail.value = null;
  open.value = false;
}
</script>

<style scoped>
.ai-launcher{position:fixed;right:22px;bottom:22px;z-index:80;border:0;border-radius:999px;padding:13px 18px;background:#0f6b7f;color:white;font-weight:700;box-shadow:0 12px 32px #17203333;width:auto}
.ai-panel{position:fixed;z-index:81;top:18px;right:18px;bottom:18px;width:min(440px,calc(100vw - 36px));display:flex;flex-direction:column;border:1px solid #dbe3ef;border-radius:16px;background:white;box-shadow:0 24px 80px #17203344;overflow:hidden}
.ai-panel.expanded{width:min(850px,calc(100vw - 36px))}
.ai-header{display:flex;align-items:center;gap:5px;padding:12px;border-bottom:1px solid #dbe3ef;background:#f8fafc}.ai-header div{flex:1;min-width:0}.ai-header strong,.ai-header small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.ai-header small{color:#667085;font-size:11px}.ai-header button,.ai-composer button,.ai-history button,.ai-sources button,.ai-source-detail button,.ai-welcome button{width:auto;min-height:32px;border:1px solid #dbe3ef;border-radius:7px;background:white;padding:4px 9px;color:#172033}.ai-header button:hover,.ai-sources button:hover{border-color:#0f6b7f}
.ai-feed{flex:1;overflow:auto;padding:16px;display:flex;flex-direction:column;gap:14px}.ai-welcome{margin:auto 0;text-align:center}.ai-welcome p{color:#667085}.ai-welcome button{color:#0f6b7f}.ai-message{max-width:94%;padding:12px;border-radius:12px;background:#f4f7fb;align-self:flex-start}.ai-message.user{background:#e3f4f7;align-self:flex-end}.ai-message>span{display:block;font-weight:700;font-size:12px}.ai-message p{white-space:pre-wrap;overflow-wrap:anywhere;margin:7px 0;line-height:1.5}.ai-message small{color:#667085;font-size:10px}.ai-sources{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}.ai-sources button{text-align:left;font-size:11px;color:#0f6b7f}.ai-error{color:#bb3434}
.ai-history{flex:1;overflow:auto;padding:12px;display:flex;flex-direction:column;gap:7px}.ai-history button{text-align:left}.ai-history button.active{border-color:#0f6b7f}.ai-history .ai-delete{color:#bb3434;margin-top:auto}.ai-composer{padding:12px;border-top:1px solid #dbe3ef}.ai-composer small{display:block;color:#bb3434;margin-bottom:6px}.ai-composer textarea{width:100%;resize:vertical}.ai-composer>div{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:6px}.ai-composer span{font-size:11px;color:#667085}.ai-composer button:last-child{background:#0f6b7f;color:white}.ai-composer button:disabled{opacity:.5}
.ai-focus{display:flex;gap:6px;margin-bottom:8px}.ai-focus select{min-width:0;flex:1;font-size:12px}
.ai-source-detail{position:absolute;inset:55px 0 0;background:white;display:flex;flex-direction:column;padding:14px;box-shadow:0 -4px 20px #17203322}.ai-source-detail>div{display:flex;justify-content:space-between;align-items:center;gap:8px}.ai-source-detail pre{overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;flex:1;font-size:12px;background:#f8fafc;padding:10px}.ai-source-detail>button{align-self:flex-end;background:#0f6b7f;color:white}
@media(max-width:600px){.ai-panel,.ai-panel.expanded{inset:0;width:100vw;border-radius:0}.ai-launcher{right:12px;bottom:12px}}
</style>
