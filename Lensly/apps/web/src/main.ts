export {};
type Provider = { id: string; model: string; configured: boolean };
type Config = {
  providers: Provider[];
  limits: { max_image_bytes: number; max_text_length: number };
  retention_days: number;
};
type Message = {
  id: string;
  role: string;
  text: string;
  image_id: string | null;
};
type Conversation = {
  id: string;
  title: string;
  active_image_id: string | null;
  messages: Message[];
};
type SavedImage = {
  id: string;
  mime_type: string;
  width: number;
  height: number;
  size_bytes: number;
  created_at: string;
};
type PairedDevice = { token: string; expires_at: string };
const rememberedDeviceKey = 'lensagent.remembered-device';

function el<T extends HTMLElement = HTMLElement>(id: string): T {
  const element = document.getElementById(id);
  if (!element) throw new Error(`Missing interface element: ${id}`);
  return element as T;
}
function textNode(tag: string, text: string, className = ''): HTMLElement {
  const node = document.createElement(tag);
  node.textContent = text;
  node.className = className;
  return node;
}
// Glasses storage may be unavailable or cleared; keep this session usable.
function browserStorage(kind: 'sessionStorage' | 'localStorage') {
  const fallback = new Map<string, string>();
  return {
    getItem(key: string): string | null {
      try {
        return window[kind].getItem(key) ?? fallback.get(key) ?? null;
      } catch {
        return fallback.get(key) ?? null;
      }
    },
    setItem(key: string, value: string): boolean {
      fallback.set(key, value);
      try {
        window[kind].setItem(key, value);
        return window[kind].getItem(key) === value;
      } catch {
        return false;
      }
    },
    removeItem(key: string): void {
      fallback.delete(key);
      try {
        window[kind].removeItem(key);
      } catch {
        /* Storage may be denied. */
      }
    },
  };
}
const session = browserStorage('sessionStorage');
const preferences = browserStorage('localStorage');
function readRememberedDevice(): PairedDevice | null {
  const saved = preferences.getItem(rememberedDeviceKey);
  if (!saved) return null;
  try {
    const device = JSON.parse(saved) as Partial<PairedDevice> | null;
    if (
      device &&
      typeof device.token === 'string' &&
      device.token.length > 0 &&
      typeof device.expires_at === 'string' &&
      Date.parse(device.expires_at) > Date.now()
    )
      return { token: device.token, expires_at: device.expires_at };
  } catch {
    /* Discard damaged or outdated saved credentials. */
  }
  preferences.removeItem(rememberedDeviceKey);
  return null;
}
let rememberedDevice = readRememberedDevice();
let token = session.getItem('lensagent.token') ?? rememberedDevice?.token ?? '';
let rememberFailed = false;
let config: Config | null = null;
let conversation: Conversation | null = null;
let selectedImage: string | null = null;
let busy = false;
let uploading = false;
let pending: { fingerprint: string; id: string } | null = null;
const imageUrls = new Map<string, string>();
let imageEpoch = 0;
let imageListVersion = 0;
let confirmationResolver: ((confirmed: boolean) => void) | null = null;
function confirmAction(message: string): Promise<boolean> {
  confirmationResolver?.(false);
  el('confirm-message').textContent = message;
  el('confirm-panel').hidden = false;
  el('confirm-action').focus();
  return new Promise((resolve) => {
    confirmationResolver = resolve;
  });
}
function resolveConfirmation(confirmed: boolean): void {
  confirmationResolver?.(confirmed);
  confirmationResolver = null;
  el('confirm-panel').hidden = true;
}

function status(message = '', error = false): void {
  el('status').textContent = message;
  el('status').classList.toggle('error', error);
}
class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code = '',
  ) {
    super(message);
  }
}
async function api<T>(path: string, init: RequestInit = {}, anonymous = false): Promise<T> {
  const headers = new Headers(init.headers);
  if (!anonymous) headers.set('Authorization', `Bearer ${token}`);
  if (typeof init.body === 'string') headers.set('Content-Type', 'application/json');
  const response = await fetch(`/api${path}`, {
    ...init,
    headers,
    cache: 'no-store',
    signal: AbortSignal.timeout(100_000),
  });
  if (!response.ok) {
    const data = (await response.json().catch(() => null)) as {
      error?: { code?: string; message?: string };
      detail?: unknown;
    } | null;
    throw new ApiError(
      data?.error?.message ?? `Request failed (${response.status}).`,
      response.status,
      data?.error?.code,
    );
  }
  if (response.status === 204) return undefined as T;
  if (response.headers.get('content-type')?.startsWith('image/'))
    return (await response.blob()) as T;
  if (!response.headers.get('content-type')?.includes('application/json'))
    throw new Error(
      'The server returned an unexpected page. Check that the laptop and tunnel are running.',
    );
  return (await response.json()) as T;
}
async function run(action: () => Promise<void>): Promise<void> {
  try {
    await action();
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) disconnect();
    status(
      error instanceof DOMException && error.name === 'TimeoutError'
        ? 'The server is taking longer than expected. Try the same question again to check its saved result.'
        : error instanceof Error
          ? error.message
          : 'An unexpected error occurred.',
      true,
    );
  }
}
function showView(name: string): void {
  resolveConfirmation(false);
  closeAttachmentMenu();
  for (const view of document.querySelectorAll<HTMLElement>('.view'))
    view.hidden = view.id !== `${name}-view`;
  for (const tab of document.querySelectorAll<HTMLButtonElement>('[data-view]')) {
    if (tab.dataset.view === name) tab.setAttribute('aria-current', 'page');
    else tab.removeAttribute('aria-current');
  }
}
function closeAttachmentMenu(): void {
  el('attachment-menu').hidden = true;
  el('add-image').setAttribute('aria-expanded', 'false');
}
function updateComposerControls(): void {
  const working = busy || uploading;
  for (const id of [
    'send',
    'add-image',
    'upload-image',
    'upload-library',
    'saved-images',
    'refresh-images',
    'new-conversation',
    'clear-context',
  ])
    el<HTMLButtonElement>(id).disabled = working;
  for (const tab of document.querySelectorAll<HTMLButtonElement>('[data-view]'))
    tab.disabled = working;
  el<HTMLSelectElement>('provider').disabled = working;
  el<HTMLTextAreaElement>('question').disabled = busy;
  el('message-form').setAttribute('aria-busy', String(working));
}
async function imageUrl(conversationId: string, imageId: string): Promise<string | null> {
  const key = `${conversationId}/${imageId}`;
  const cached = imageUrls.get(key);
  if (cached) return cached;
  const epoch = imageEpoch;
  const blob = await api<Blob>(`/conversations/${conversationId}/images/${imageId}`);
  if (conversation?.id !== conversationId || epoch !== imageEpoch) return null;
  const existing = imageUrls.get(key);
  if (existing) return existing;
  const url = URL.createObjectURL(blob);
  imageUrls.set(key, url);
  return url;
}
function renderConversation(): void {
  const list = el('messages');
  list.replaceChildren();
  if (!conversation?.messages.length) {
    const empty = textNode('div', '', 'empty');
    const orbit = textNode('div', '', 'orbit');
    orbit.setAttribute('aria-hidden', 'true');
    empty.append(
      orbit,
      textNode('h2', 'What are we exploring?'),
      textNode('p', 'Bring a question. Or a picture.', 'muted'),
    );
    list.append(empty);
  }
  for (const message of conversation?.messages ?? []) {
    const row = textNode(
      'article',
      '',
      `message ${message.role === 'user' ? 'user' : 'assistant'}`,
    );
    row.append(textNode('span', message.role === 'user' ? 'You' : 'Lensly', 'role'));
    if (message.role === 'user' && message.image_id && conversation) {
      const preview = document.createElement('img');
      preview.className = 'message-image';
      preview.alt = 'Image sent with this question';
      row.append(preview);
      const cid = conversation.id;
      const imageId = message.image_id;
      void run(async () => {
        try {
          const url = await imageUrl(cid, imageId);
          if (url && row.isConnected) preview.src = url;
        } catch (error) {
          if (error instanceof ApiError && error.status === 401) throw error;
          preview.replaceWith(textNode('small', 'Image unavailable', 'fine'));
        }
      });
    }
    row.append(document.createTextNode(message.text));
    list.append(row);
  }
  el('conversation-title').textContent = conversation?.title || 'New conversation';
  list.scrollTop = list.scrollHeight;
  renderContext();
}
function renderContext(): void {
  el('context-label').textContent = selectedImage
    ? `Image selected · ${selectedImage.slice(0, 8)}`
    : 'Text only · no image sent';
  el('clear-context').hidden = !selectedImage;
  el('attachment-preview').hidden = !selectedImage;
  const preview = el<HTMLImageElement>('attachment-image');
  preview.hidden = true;
  preview.removeAttribute('src');
  el('attachment-title').textContent = 'Image attached';
  if (!selectedImage || !conversation) return;
  const imageId = selectedImage;
  const cid = conversation.id;
  void run(async () => {
    try {
      const url = await imageUrl(cid, imageId);
      if (url && selectedImage === imageId && conversation?.id === cid) {
        preview.src = url;
        preview.hidden = false;
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) throw error;
      if (selectedImage !== imageId || conversation?.id !== cid) return;
      if (error instanceof ApiError && error.status === 404) {
        selectedImage = null;
        renderContext();
        status('That image is no longer available. Add or choose another image.', true);
      } else el('attachment-title').textContent = 'Image attached · preview unavailable';
    }
  });
}
async function loadConversation(id: string): Promise<void> {
  if (conversation?.id !== id) clearImageUrls();
  conversation = await api<Conversation>(`/conversations/${id}`);
  selectedImage = conversation.active_image_id;
  preferences.setItem('lensagent.conversation', id);
  pending = null;
  renderConversation();
}
async function newConversation(): Promise<void> {
  clearImageUrls();
  conversation = await api<Conversation>('/conversations', {
    method: 'POST',
    body: JSON.stringify({ title: 'New conversation' }),
  });
  conversation.messages ??= [];
  selectedImage = null;
  preferences.setItem('lensagent.conversation', conversation.id);
  pending = null;
  el<HTMLTextAreaElement>('question').value = '';
  renderConversation();
  showView('chat');
  status();
}
async function connect(): Promise<void> {
  const loaded = await api<Config>('/config');
  config = loaded;
  session.setItem('lensagent.token', token);
  el<HTMLInputElement>('token').value = '';
  el('remembered-status').textContent =
    rememberedDevice?.token === token
      ? `This device stays signed in until ${new Date(rememberedDevice.expires_at).toLocaleString()}. Disconnecting forgets the saved login.`
      : rememberFailed
        ? 'This browser could not save your login. You can use this session, but may need to pair again after closing.'
        : 'This login lasts for this browser session. To stay signed in on glasses, pair with Remember this device selected.';
  const select = el<HTMLSelectElement>('provider');
  select.replaceChildren();
  for (const provider of loaded.providers) {
    const option = document.createElement('option');
    option.value = provider.id;
    option.textContent = `${provider.id === 'gemini' ? 'Gemini' : 'Ollama'}${provider.configured ? '' : ' · setup needed'}`;
    select.append(option);
  }
  select.value =
    loaded.providers.find((provider) => provider.configured)?.id ??
    loaded.providers[0]?.id ??
    'gemini';
  el<HTMLTextAreaElement>('question').maxLength = loaded.limits.max_text_length;
  const cards = el('provider-status');
  cards.replaceChildren();
  for (const provider of loaded.providers) {
    const card = textNode('div', '', 'provider-card');
    card.append(
      textNode('strong', provider.id === 'gemini' ? 'Google Gemini' : 'Local Ollama'),
      textNode('p', provider.model),
      textNode(
        'p',
        provider.configured
          ? 'Configured on the server. Live availability is checked when you ask.'
          : 'Not configured. Update the server .env file and restart.',
      ),
    );
    if (provider.id === 'ollama') {
      card.append(
        textNode(
          'p',
          'Questions load this model on your laptop when needed. Stopping it in Ollama frees memory; the next question loads it again. To disable it, set OLLAMA_ENABLED=false in the server .env and restart the server.',
          'fine',
        ),
      );
    }
    cards.append(card);
  }
  el('retention').textContent =
    `Images expire after ${loaded.retention_days} days; conversations after ${loaded.retention_days} inactive days. Cleanup runs when the app is used. You can also delete them here. Gemini receives your text and selected image when used; check your account’s data terms first.`;
  const previous = preferences.getItem('lensagent.conversation');
  if (previous) {
    try {
      await loadConversation(previous);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) await newConversation();
      else throw error;
    }
  } else await newConversation();
  el('connect-view').hidden = true;
  el('workspace').hidden = false;
  document.querySelector('.app')?.classList.add('connected');
  el('connection').textContent = 'CONNECTED';
  showView('chat');
  el('messages').scrollTop = el('messages').scrollHeight;
  status(
    rememberFailed
      ? 'Connected, but this browser could not remember your login. You may need to pair again after closing.'
      : loaded.providers.some((p) => p.configured)
        ? ''
        : 'Connected. Add a Gemini key or configure Ollama to receive AI answers.',
  );
}
function disconnect(): void {
  resolveConfirmation(false);
  closeAttachmentMenu();
  token = '';
  session.removeItem('lensagent.token');
  preferences.removeItem(rememberedDeviceKey);
  rememberedDevice = null;
  rememberFailed = false;
  conversation = null;
  config = null;
  pending = null;
  selectedImage = null;
  renderContext();
  clearImageUrls();
  el('messages').replaceChildren();
  el('image-list').replaceChildren();
  el('history-list').replaceChildren();
  el('pairing-result').textContent = '';
  el('remembered-status').textContent = '';
  el('workspace').hidden = true;
  document.querySelector('.app')?.classList.remove('connected');
  el('connect-view').hidden = false;
  el('connection').textContent = 'PAIR DEVICE';
  status('Disconnected.');
}
function clearImageUrls(): void {
  imageEpoch += 1;
  imageListVersion += 1;
  imageUrls.forEach((url) => URL.revokeObjectURL(url));
  imageUrls.clear();
}
async function loadImages(): Promise<void> {
  if (!conversation) return;
  const version = ++imageListVersion;
  const conversationId = conversation.id;
  const images = await api<SavedImage[]>(`/conversations/${conversationId}/images`);
  if (conversation?.id !== conversationId || version !== imageListVersion) return;
  const list = el('image-list');
  list.replaceChildren();
  if (!images.length) list.append(textNode('p', 'No images in this conversation yet.', 'muted'));
  for (const item of images) {
    const row = textNode(
      'div',
      '',
      `image-item${selectedImage === item.id ? ' selected-image' : ''}`,
    );
    const preview = document.createElement('img');
    preview.alt = `Saved image ${item.id.slice(0, 8)}`;
    const url = await imageUrl(conversationId, item.id);
    if (conversation?.id !== conversationId || version !== imageListVersion) return;
    if (!url) continue;
    preview.src = url;
    const info = textNode('div', '');
    info.append(
      textNode('p', `${item.width} × ${item.height} · ${Math.ceil(item.size_bytes / 1024)} KB`),
    );
    const actions = textNode('div', '', 'image-actions');
    const use = textNode(
      'button',
      selectedImage === item.id ? 'Selected' : 'Use image',
      'compact',
    ) as HTMLButtonElement;
    use.addEventListener('click', () => {
      if (busy || uploading) return;
      selectedImage = item.id;
      pending = null;
      renderContext();
      showView('chat');
      status('Image selected for your next question.');
    });
    const remove = textNode('button', 'Delete', 'compact') as HTMLButtonElement;
    remove.setAttribute('aria-label', `Delete image ${item.id.slice(0, 8)}`);
    remove.addEventListener('click', () => {
      void run(async () => {
        if (!(await confirmAction('Delete this image and remove it from conversation context?')))
          return;
        await api(`/conversations/${conversationId}/images/${item.id}`, {
          method: 'DELETE',
        });
        if (selectedImage === item.id) selectedImage = null;
        clearImageUrls();
        pending = null;
        renderConversation();
        await loadImages();
        status('Image deleted. Earlier text discussing it may remain in the conversation.');
      });
    });
    actions.append(use, remove);
    info.append(actions);
    row.append(preview, info);
    list.append(row);
  }
}
async function loadHistory(): Promise<void> {
  const history = await api<Conversation[]>('/conversations');
  const list = el('history-list');
  list.replaceChildren();
  if (!history.length) list.append(textNode('p', 'Your conversations will appear here.', 'muted'));
  for (const item of history) {
    const row = textNode('div', '', 'history-row');
    const open = textNode('button', item.title || 'Untitled conversation');
    open.addEventListener('click', () => {
      void run(async () => {
        await loadConversation(item.id);
        showView('chat');
        status();
      });
    });
    const remove = textNode('button', 'Delete conversation', 'compact');
    remove.addEventListener('click', () => {
      void run(async () => {
        if (!(await confirmAction('Delete this conversation, its messages and all its images?')))
          return;
        await api(`/conversations/${item.id}`, { method: 'DELETE' });
        if (conversation?.id === item.id) await newConversation();
        await loadHistory();
        showView('history');
        status('Conversation deleted.');
      });
    });
    row.append(open, remove);
    list.append(row);
  }
}
el('connect-form').addEventListener('submit', (event) => {
  event.preventDefault();
  void run(async () => {
    // The permanent laptop administrator token must remain session-only.
    preferences.removeItem(rememberedDeviceKey);
    rememberedDevice = null;
    rememberFailed = false;
    token = el<HTMLInputElement>('token').value.trim();
    status('Connecting…');
    await connect();
  });
});
el('pair-form').addEventListener('submit', (event) => {
  event.preventDefault();
  void run(async () => {
    status('Pairing…');
    const result = await api<PairedDevice>(
      '/pairing/redeem',
      {
        method: 'POST',
        body: JSON.stringify({
          code: el<HTMLInputElement>('pair-code').value.trim(),
        }),
      },
      true,
    );
    token = result.token;
    session.setItem('lensagent.token', token);
    preferences.removeItem(rememberedDeviceKey);
    rememberedDevice = null;
    rememberFailed = false;
    if (el<HTMLInputElement>('remember-device').checked) {
      const device: PairedDevice = { token, expires_at: result.expires_at };
      if (preferences.setItem(rememberedDeviceKey, JSON.stringify(device)))
        rememberedDevice = device;
      else {
        preferences.removeItem(rememberedDeviceKey);
        rememberFailed = true;
      }
    }
    el<HTMLInputElement>('pair-code').value = '';
    await connect();
  });
});
for (const tab of document.querySelectorAll<HTMLButtonElement>('[data-view]')) {
  tab.addEventListener('click', () => {
    void run(async () => {
      if (busy || uploading) return;
      showView(tab.dataset.view ?? 'chat');
      status();
      if (tab.dataset.view === 'images') await loadImages();
      if (tab.dataset.view === 'history') await loadHistory();
    });
  });
}
el('new-conversation').addEventListener('click', () => {
  if (!busy && !uploading) void run(newConversation);
});
el('clear-context').addEventListener('click', () => {
  selectedImage = null;
  pending = null;
  renderContext();
  status('Your next question will not send an image.');
});
el('message-form').addEventListener('submit', (event) => {
  event.preventDefault();
  if (busy || uploading || !conversation) return;
  closeAttachmentMenu();
  const question = el<HTMLTextAreaElement>('question');
  const text = question.value.trim();
  if (!text) return;
  const provider = el<HTMLSelectElement>('provider').value;
  const conversationId = conversation.id;
  const body = {
    text,
    provider,
    image_id: selectedImage,
    use_recent_image: false,
  };
  el('new-attempt').hidden = true;
  const fingerprint = JSON.stringify({ conversationId, ...body });
  if (pending?.fingerprint !== fingerprint) pending = { fingerprint, id: crypto.randomUUID() };
  const requestId = pending.id;
  busy = true;
  updateComposerControls();
  el('messages').setAttribute('aria-busy', 'true');
  status('Thinking…');
  void run(async () => {
    try {
      await api(`/conversations/${conversationId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ ...body, request_id: requestId }),
      });
      question.value = '';
      await loadConversation(conversationId);
      status();
    } catch (error) {
      if (
        error instanceof ApiError &&
        [
          'provider_unconfigured',
          'provider_credentials',
          'provider_rate_limit',
          'provider_error',
          'provider_unreachable',
          'empty_response',
          'provider_response',
          'response_size',
          'idempotency_conflict',
          'image_not_found',
        ].includes(error.code)
      )
        pending = null;
      if (
        error instanceof ApiError &&
        ['provider_timeout', 'internal_error', 'request_interrupted'].includes(error.code)
      )
        el('new-attempt').hidden = false;
      throw error;
    } finally {
      busy = false;
      updateComposerControls();
      el('messages').removeAttribute('aria-busy');
    }
  });
});
async function uploadImage(file: File): Promise<void> {
  if (busy || uploading || !conversation || !config) return;
  if (file.size > config.limits.max_image_bytes)
    throw new Error(
      `Image is too large. Maximum ${Math.floor(config.limits.max_image_bytes / 1024 / 1024)} MB.`,
    );
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type))
    throw new Error('Use JPEG, PNG or WebP. Convert HEIC photos on your phone or computer first.');
  const data = new FormData();
  data.append('file', file);
  const cid = conversation.id;
  closeAttachmentMenu();
  uploading = true;
  updateComposerControls();
  status('Uploading image…');
  try {
    const image = await api<SavedImage>(`/conversations/${cid}/images`, {
      method: 'POST',
      body: data,
    });
    if (conversation?.id !== cid) return;
    selectedImage = image.id;
    pending = null;
    renderContext();
    showView('chat');
    status('Image ready. What would you like to know?');
  } finally {
    uploading = false;
    updateComposerControls();
  }
}
el('image-file').addEventListener('change', () => {
  const input = el<HTMLInputElement>('image-file');
  const file = input.files?.[0];
  input.value = '';
  if (file) void run(() => uploadImage(file));
});
el('add-image').addEventListener('click', () => {
  if (busy || uploading) return;
  const open = el('attachment-menu').hidden;
  el('attachment-menu').hidden = !open;
  el('add-image').setAttribute('aria-expanded', String(open));
  if (open) el('upload-image').focus();
});
for (const id of ['upload-image', 'upload-library'])
  el(id).addEventListener('click', () => {
    if (busy || uploading) return;
    closeAttachmentMenu();
    el<HTMLInputElement>('image-file').click();
  });
el('saved-images').addEventListener('click', () => {
  if (busy || uploading) return;
  showView('images');
  void run(loadImages);
});
el('refresh-images').addEventListener('click', () => {
  void run(loadImages);
});
document.addEventListener('click', (event) => {
  if (event.target instanceof Element && !event.target.closest('.attachment-control'))
    closeAttachmentMenu();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !el('attachment-menu').hidden) {
    closeAttachmentMenu();
    el('add-image').focus();
  }
});
el('question').addEventListener('paste', (event) => {
  const file = (event as ClipboardEvent).clipboardData?.files[0];
  if (!file || !file.type.startsWith('image/')) return;
  event.preventDefault();
  void run(() => uploadImage(file));
});
el('create-pairing').addEventListener('click', () => {
  void run(async () => {
    const pairing = await api<{ code: string; expires_at: string }>('/pairing', { method: 'POST' });
    el('pairing-result').textContent =
      `Code: ${pairing.code} · valid for 5 minutes, one use. Enter it on the glasses connection screen.`;
    status();
  });
});
el('revoke-devices').addEventListener('click', () => {
  void run(async () => {
    if (!(await confirmAction('Disconnect all paired devices? They will need a new pairing code.')))
      return;
    const devices = await api<{ id: string }[]>('/devices');
    for (const device of devices) await api(`/devices/${device.id}`, { method: 'DELETE' });
    status('Paired device access revoked.');
  });
});
el('disconnect').addEventListener('click', disconnect);
el('new-attempt').addEventListener('click', () => {
  void run(async () => {
    if (
      !(await confirmAction(
        'The previous provider outcome may be unknown. Send another request? Cloud providers may charge again.',
      ))
    )
      return;
    pending = null;
    el('new-attempt').hidden = true;
    el<HTMLFormElement>('message-form').requestSubmit();
  });
});
el('confirm-action').addEventListener('click', () => resolveConfirmation(true));
el('cancel-action').addEventListener('click', () => resolveConfirmation(false));
window.addEventListener('pagehide', (event) => {
  if (!event.persisted) clearImageUrls();
});
document.documentElement.dataset.lensagentReady = 'true';
el('startup-status').textContent = 'Ready · Lensly build 4';
if (token) {
  status('Restoring connection…');
  void run(connect);
} else {
  el('connection').textContent = 'PAIR DEVICE';
  el<HTMLInputElement>('pair-code').focus();
}
