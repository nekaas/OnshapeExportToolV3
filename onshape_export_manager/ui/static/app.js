/* ============================================================
   Onshape Export Manager — front-end controllers (Alpine.js)
   ============================================================ */

const I = (p) =>
  `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${p}</svg>`;

const ICONS = {
  search: I('<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>'),
  sun: I('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19"/>'),
  moon: I('<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>'),
  menu: I('<path d="M3 6h18M3 12h18M3 18h18"/>'),
  refresh: I('<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>'),
  collapse: I('<path d="M15 6l-6 6 6 6"/>'),
  expand: I('<path d="M9 6l6 6-6 6"/>'),
  accounts: I('<circle cx="7.5" cy="15.5" r="4"/><path d="M10.4 12.6 20 3"/><path d="M16 7l3 3"/>'),
  labels: I('<path d="M3 3h7l11 11-7 7L3 10V3z"/>'),
  layers: I('<path d="M12 3 3 8l9 5 9-5-9-5z"/><path d="M3 13l9 5 9-5"/>'),
  queue: I('<path d="M4 6h16M4 12h16M4 18h10"/>'),
  clock: I('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
  check: I('<path d="M20 6 9 17l-5-5"/>'),
  save: I('<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><path d="M17 21v-8H7v8"/><path d="M7 3v5h8"/>'),
  star: I('<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8-6.2-3.2L5.8 21 7 14.2 2 9.3l6.9-1L12 2z"/>'),
  alert: I('<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>'),
  info: I('<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>'),
  bolt: I('<path d="M13 2 4 14h7l-1 8 9-12h-7l1-8z"/>'),
  files: I('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>'),
  activity: I('<path d="M3 12h4l3 8 4-16 3 8h4"/>'),
  logout: I('<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>'),
};

function fetchJSON(url) {
  return fetch(url, { headers: { Accept: "application/json" } }).then((r) => {
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  });
}

function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

function relativeTime(iso) {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const diff = Date.now() - then;
  const mins = Math.round(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

function cloneDate(value) {
  return new Date(value.getTime());
}

function startOfDay(value) {
  const date = cloneDate(value);
  date.setHours(0, 0, 0, 0);
  return date;
}

function endOfDay(value) {
  const date = cloneDate(value);
  date.setHours(23, 59, 59, 999);
  return date;
}

function startOfWeek(value) {
  const date = startOfDay(value);
  const day = date.getDay() || 7;
  date.setDate(date.getDate() - day + 1);
  return date;
}

function formatLocalDateTime(value) {
  if (!value) return "";
  return new Date(value).toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/* Audio notification stub — uses Web Audio API for a gentle completion chime.
   Called after export completes, respecting user preference. */
function playNotificationSound() {
  try {
    if (localStorage.getItem("oem-sound") === "off") return;
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = "sine";
    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    // Two-tone chime: C5 → E5
    osc.frequency.setValueAtTime(523.25, ctx.currentTime);
    osc.frequency.setValueAtTime(659.25, ctx.currentTime + 0.12);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.35);
  } catch (e) { /* silently ignore if audio not available */ }
}

/* ---------------- App shell ---------------- */
function appShell() {
  return {
    icons: ICONS,
    isDark: true,
    collapsed: false,
    mobileOpen: false,
    summary: {},
    toasts: [],
    _toastId: 0,

    init() {
      this.isDark = document.documentElement.classList.contains("dark");
      this.collapsed = localStorage.getItem("oem-collapsed") === "1";
      this.startPolling();
      window.addEventListener("keydown", (e) => this.onKey(e));
      window.oem = this; // expose for toasts from other components
    },

    toggleTheme() {
      this.isDark = !this.isDark;
      document.documentElement.classList.toggle("dark", this.isDark);
      try {
        localStorage.setItem("oem-theme", this.isDark ? "dark" : "light");
      } catch (e) {}
      window.dispatchEvent(new CustomEvent("oem-theme", { detail: { dark: this.isDark } }));
    },

    toggleSidebar() {
      this.collapsed = !this.collapsed;
      try {
        localStorage.setItem("oem-collapsed", this.collapsed ? "1" : "0");
      } catch (e) {}
    },

    onKey(e) {
      const meta = e.metaKey || e.ctrlKey;
      if (meta && e.key.toLowerCase() === "b") {
        e.preventDefault();
        this.toggleSidebar();
      }
    },

    startPolling() {
      const poll = () =>
        fetchJSON("/api/summary")
          .then((d) => { this.summary = d; })
          .catch(() => {});
      poll();
      setInterval(poll, 6000);
    },

    toast(title, kind = "info", message = "") {
      const id = ++this._toastId;
      this.toasts.push({ id, title, kind, message });
      setTimeout(() => this.dismissToast(id), 4500);
    },
    dismissToast(id) {
      this.toasts = this.toasts.filter((t) => t.id !== id);
    },
    toastIcon(kind) {
      return ICONS[{ success: "check", error: "alert", info: "info" }[kind] || "info"];
    },
  };
}

/* ---------------- Home page ---------------- */
function homePage() {
  return {
    icons: ICONS,
    loading: true,
    cards: { orgs: 0, groups: 0, exports: 0, queue: 0, failed: 0 },
    recent: [],

    load() {
      this.loading = true;
      fetchJSON("/api/metrics")
        .then((data) => {
          this.build(data);
        })
        .catch(() => {})
        .finally(() => (this.loading = false));
    },

    build(d) {
      const s = d.summary || {};
      this.cards = {
        orgs: s.organizations ?? 0,
        groups: s.labels ?? 0,
        exports: s.total_exports ?? 0,
        queue: s.queue_size ?? 0,
        failed: s.failed_exports ?? 0,
      };
      this.recent = d.recent_history || [];
    },

    relTime(iso) {
      return relativeTime(iso);
    },
  };
}

/* ---------------- Section pages ---------------- */
const PAGE_CONFIG = {
  export: {
    endpoint: null, root: null, empty: "", columns: [],
  },
  organizations: {
    endpoint: "/api/tree", root: "organisations", empty: "",
    columns: [],  // tree-based view, not table
  },
  history: {
    endpoint: "/api/history?limit=500", root: "history", empty: "No export history yet.",
    columns: [
      { key: "started_at", label: "Started", type: "time" },
      { key: "label_name", label: "Label", type: "strong" },
      { key: "export_profile", label: "Profile", type: "text" },
      { key: "account_name", label: "Account", type: "text" },
      { key: "file_count", label: "Files", type: "number" },
      { key: "duration_seconds", label: "Duration", type: "seconds" },
      { key: "success", label: "Result", type: "result" },
    ],
  },
};

function sectionPage(page) {
  const cfg = PAGE_CONFIG[page];
  return {
    page,
    icons: ICONS,
    loading: false,
    rows: [],
    filter: "",
    sortKey: null,
    sortDir: "asc",
    columns: cfg ? cfg.columns : [],
    emptyText: cfg ? cfg.empty : "Nothing here.",
    hasTable: cfg && cfg.columns && cfg.columns.length > 0,
    profiles: [],
    // export page: queue items for combined view
    queueItems: [],
    // logs
    logAreas: ["app", "errors", "api", "export", "scheduler", "queue", "web", "worker", "events", "audit", "notifications"],
    activeLog: "app",
    logLines: [],
    // manual export
    manual: { label: "", profile: "", start: "", end: "", destination: "", mode: "range", preset: "today" },
    preview: null,
    previewBusy: false,
    exportBusy: false,
    worker: { running: false },
    datePresets: [
      { key: "today", label: "Today" },
      { key: "yesterday", label: "Yesterday" },
      { key: "this-week", label: "This Week" },
      { key: "last-week", label: "Last Week" },
      { key: "this-month", label: "This Month" },
      { key: "last-month", label: "Last Month" },
      { key: "custom", label: "Custom Range" },
    ],
    _manualPlannerReady: false,
    _manualPickers: {},
    _previewTimer: null,
    // retention / cleanup
    retentionDays: 0,
    // system
    system: {},
    remote: {},
    backups: [],
    systemCards: [],
    remoteRows: [],
    backupBusy: false,
    // notifications
    notifChannels: [],
    notifKinds: ["discord", "slack", "teams", "email", "webhook"],
    notifSeverities: ["info", "success", "warning", "error", "critical"],
    notifEnabled: true,
    notifForm: { id: "", name: "", kind: "discord", target: "", min_severity: "info", enabled: true, options: {} },
    // settings
    settingsTabs: [
      { slug: "general", label: "General" },
      { slug: "notifications", label: "Notifications" },
      { slug: "backups", label: "Backups" },
      { slug: "remote-access", label: "Remote Access" },
      { slug: "logs", label: "Logs" },
      { slug: "about", label: "About" },
    ],
    settingsActiveTab: "general",
    settingsGroups: [],

    load() {
      if (this.page === "export" || this.page === "manual-export") return this.loadExportPage();
      if (this.page === "organizations") return; // treeSelector handles loading
      if (this.page === "logs") return this.selectLog(this.activeLog);
      if (this.page === "settings") return this.loadSettings();
      if (this.page === "system") return this.loadSystem();
      if (this.page === "notifications") return this.loadNotifications();
      if (!cfg) return;
      this.loading = true;
      fetchJSON(cfg.endpoint)
        .then((data) => {
          this.rows = data[cfg.root] || [];
        })
        .catch((e) => window.oem && window.oem.toast("Failed to load", "error", e.message))
        .finally(() => (this.loading = false));
    },

    // ── Export page (manual export + queue combined) ─────────────
    loadExportPage() {
      this.loading = true;
      this.loadLastUsed();
      this.ensureManualWindow();
      // Reuse treeSelector data if already loaded on this page (avoids double fetch)
      const treePromise = window.__treeData
        ? Promise.resolve(window.__treeData)
        : fetchJSON("/api/tree").catch(() => ({ organisations: [] }));
      const fetches = [
        treePromise,
        fetchJSON("/api/profiles").catch(() => ({ profiles: [] })),
        fetchJSON("/api/worker").catch(() => ({ running: false })),
      ];
      if (this.page === "export") {
        fetches.push(fetchJSON("/api/queue").catch(() => ({ items: [] })));
      }
      Promise.all(fetches)
        .then((results) => {
          const tree = results[0], profiles = results[1], worker = results[2];
          this._treeData = tree; // cache for selectedOrgName()
          const allGroups = [];
          for (const org of (tree.organisations || [])) {
            for (const g of (org.groups || [])) allGroups.push(g);
          }
          this.rows = allGroups;
          this.profiles = profiles.profiles || [];
          this.worker = worker || { running: false };
          if (results.length > 3) this.queueItems = (results[3] && results[3].items) || [];
          if (this.rows.length && !this.manual.label) {
            this.manual.label = this.rows[0].friendly_name;
          }
          // Only auto-preview if a label is actually selected
          if (this.manual.label) this.schedulePreview(150);
        })
        .catch((e) => window.oem && window.oem.toast("Failed to load export planner", "error", e.message))
        .finally(() => (this.loading = false));
    },

    // Resolve which org the selected group belongs to (for destination path)
    selectedOrgName() {
      if (!this.manual.label || !this._treeData) return "";
      for (const org of (this._treeData.organisations || [])) {
        for (const g of (org.groups || [])) {
          if (g.friendly_name === this.manual.label) return org.name;
        }
      }
      return "";
    },

    isExportBusy() { return this.exportBusy || this.previewBusy; },

    initManualPlanner() {
      if (this.page !== "manual-export" && this.page !== "export") return;
      this.loadLastUsed();
      this.ensureManualWindow();
      this.initManualFlatpickrs();
      this.syncManualPickers();
      if (this.manual.label) this.schedulePreview(150);
    },

    initManualFlatpickrs() {
      if (this._manualPlannerReady) return;
      if (typeof flatpickr === "undefined") {
        setTimeout(() => this.initManualFlatpickrs(), 150);
        return;
      }
      const common = {
        enableTime: true,
        time_24hr: true,
        minuteIncrement: 5,
        dateFormat: "M j, Y H:i",
      };
      if (this.$refs.manualStartPicker) {
        this._manualPickers.start = flatpickr(this.$refs.manualStartPicker, {
          ...common,
          onChange: ([date]) => {
            if (!date) return;
            this.manual.start = date.toISOString();
            if (this.manual.end && date > new Date(this.manual.end)) {
              this.manual.end = endOfDay(date).toISOString();
            }
            this.manual.preset = "custom";
            this.syncManualPickers();
            this.schedulePreview();
          },
        });
      }
      if (this.$refs.manualEndPicker) {
        this._manualPickers.end = flatpickr(this.$refs.manualEndPicker, {
          ...common,
          onChange: ([date]) => {
            if (!date) return;
            this.manual.end = date.toISOString();
            if (this.manual.start && date < new Date(this.manual.start)) {
              this.manual.start = startOfDay(date).toISOString();
            }
            this.manual.preset = "custom";
            this.syncManualPickers();
            this.schedulePreview();
          },
        });
      }
      if (this.$refs.manualSinglePicker) {
        this._manualPickers.single = flatpickr(this.$refs.manualSinglePicker, {
          dateFormat: "M j, Y",
          onChange: ([date]) => {
            if (!date) return;
            this.setManualWindow(startOfDay(date), endOfDay(date), {
              mode: "single",
              preset: "custom",
            });
          },
        });
      }
      this._manualPlannerReady = true;
      this.syncManualPickers();
    },

    ensureManualWindow() {
      if (this.manual.start && this.manual.end) return;
      const now = new Date();
      this.setManualWindow(startOfDay(now), endOfDay(now), {
        mode: "single",
        preset: "today",
        preview: false,
      });
    },

    setManualWindow(start, end, options = {}) {
      this.manual.start = start.toISOString();
      this.manual.end = end.toISOString();
      if (options.mode) this.manual.mode = options.mode;
      if (options.preset !== undefined) this.manual.preset = options.preset;
      this.syncManualPickers();
      if (options.preview !== false) this.schedulePreview();
    },

    syncManualPickers() {
      const start = this.manual.start ? new Date(this.manual.start) : null;
      const end = this.manual.end ? new Date(this.manual.end) : null;
      if (this._manualPickers.start && start) this._manualPickers.start.setDate(start, false);
      if (this._manualPickers.end && end) this._manualPickers.end.setDate(end, false);
      if (this._manualPickers.single && start) this._manualPickers.single.setDate(start, false);
    },

    setManualMode(mode) {
      this.manual.mode = mode;
      if (mode === "single") {
        const current = this.manual.start ? new Date(this.manual.start) : new Date();
        this.setManualWindow(startOfDay(current), endOfDay(current), {
          mode: "single",
          preset: this.manual.preset === "custom" ? "custom" : this.manual.preset,
        });
        return;
      }
      this.syncManualPickers();
      this.schedulePreview();
    },

    applyDatePreset(key) {
      const now = new Date();
      let start = startOfDay(now);
      let end = endOfDay(now);
      let mode = "range";
      if (key === "yesterday") {
        start.setDate(start.getDate() - 1);
        end = endOfDay(start);
        mode = "single";
      } else if (key === "today") {
        mode = "single";
      } else if (key === "this-week") {
        start = startOfWeek(now);
      } else if (key === "last-week") {
        end = startOfWeek(now);
        end.setMilliseconds(-1);
        start = startOfWeek(end);
      } else if (key === "this-month") {
        start = new Date(now.getFullYear(), now.getMonth(), 1);
        end = endOfDay(now);
      } else if (key === "last-month") {
        start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        end = new Date(now.getFullYear(), now.getMonth(), 1);
        end.setMilliseconds(-1);
      } else if (key === "custom") {
        this.manual.mode = "range";
        this.manual.preset = "custom";
        this.$nextTick(() => this._manualPickers.start && this._manualPickers.start.open());
        return;
      }
      this.setManualWindow(start, end, { mode, preset: key });
    },

    onManualSelectionChanged() {
      this.schedulePreview();
    },

    manualRequestBody() {
      return {
        label: this.manual.label || "",
        profile: this.manual.profile || "",
        start: this.manual.start || "",
        end: this.manual.end || "",
        destination: this.manual.destination || "",
      };
    },

    schedulePreview(delay = 350) {
      clearTimeout(this._previewTimer);
      if (!this.manual.label) return; // don't preview without a label selected
      this._previewTimer = setTimeout(() => this.previewExport({ quiet: true }), delay);
    },

    previewExport(options = {}) {
      const quiet = options.quiet === true;
      if (!this.manual.label) return Promise.resolve();
      if (!quiet) this.previewBusy = true;
      return fetch("/api/exports/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.manualRequestBody()),
      })
        .then((r) => r.json().then((d) => ({ ok: r.ok, data: d })))
        .then(({ ok, data }) => {
          if (!ok || data.error) throw new Error(data.error || "Preview failed");
          this.preview = data;
          if (!quiet) window.oem && window.oem.toast("Preview ready", "success", data.profile.name);
        })
        .catch((e) => {
          this.preview = {
            valid: false,
            checks: [{ key: "preview", label: "Preview", status: "error", detail: e.message }],
            timeline: [],
            estimates: {},
          };
          if (!quiet) window.oem && window.oem.toast("Preview failed", "error", e.message);
        })
        .finally(() => {
          if (!quiet) this.previewBusy = false;
        });
    },

    runExport() {
      if (this.exportBusy) return;
      const label = (this.manual.label || "").trim();
      if (!label) return window.oem && window.oem.toast("Choose a label first", "error");
      const profileName = this.manual.profile || "default";
      this.exportBusy = true;
      const body = this.manualRequestBody();
      fetch("/api/exports/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
        .then((r) => r.json())
        .then((d) => {
          if (d.error) throw new Error(d.error);
          const displayName = `${body.label} · ${profileName}`;
          window.oem && window.oem.toast("Export queued", "success", displayName);
          this.saveLastUsed();
          playNotificationSound();
          fetchJSON("/api/worker").then((w) => (this.worker = w || this.worker)).catch(() => {});
        })
        .catch((e) => window.oem && window.oem.toast("Could not queue export", "error", e.message))
        .finally(() => (this.exportBusy = false));
    },

    saveLastUsed() {
      try {
        localStorage.setItem("oem-last-export", JSON.stringify({
          label: this.manual.label,
          profile: this.manual.profile,
          destination: this.manual.destination,
        }));
      } catch (e) {}
    },

    loadLastUsed() {
      try {
        const saved = JSON.parse(localStorage.getItem("oem-last-export") || "{}");
        if (saved.label) this.manual.label = saved.label;
        if (saved.profile) this.manual.profile = saved.profile;
        if (saved.destination) this.manual.destination = saved.destination;
      } catch (e) {}
    },

    onQueueAction(event) {
      const btn = event.target.closest("[data-qaction]");
      if (!btn) return;
      const action = btn.getAttribute("data-qaction");
      const id = btn.getAttribute("data-qid");
      if (!id) return;
      if (action === "cancel" && !confirm("Cancel this queued job?")) return;
      fetch(`/api/queue/${id}/${action}`, { method: "POST" })
        .then((r) => r.json())
        .then((d) => {
          if (d.error) throw new Error(d.error);
          window.oem && window.oem.toast(action === "cancel" ? "Job cancelled" : "Job requeued", "success");
          this.load();
        })
        .catch((e) => window.oem && window.oem.toast("Action failed", "error", e.message));
    },

    loadSettings() {
      // Load all data needed across settings tabs
      this.loading = true;
      this.loadNotifications();
      // Load retention setting
      fetchJSON("/api/settings/retention").then(d => { this.retentionDays = d.retention_days || 0; }).catch(() => {});
      Promise.all([
        fetchJSON("/api/metrics"),
        fetchJSON("/api/system").catch(() => ({})),
        fetchJSON("/api/remote-access").catch(() => ({})),
        fetchJSON("/api/backups").catch(() => ({ backups: [] })),
      ])
        .then(([metrics, sys, remote, backupsData]) => {
          const db = metrics.database || {};
          this.settingsGroups = [
            { title: "Application", rows: [
              { k: "Version", v: metrics.version },
              { k: "Generated", v: relativeTime(metrics.generated_at) },
            ]},
            { title: "Database", rows: [
              { k: "Schema version", v: "v" + (db.schema_version ?? 0) },
              { k: "Export history rows", v: db.export_history ?? 0 },
              { k: "Queue rows", v: db.export_queue ?? 0 },
              { k: "Scheduler rows", v: db.scheduler_jobs ?? 0 },
            ]},
            { title: "Storage", rows: [
              { k: "Exports size", v: metrics.disk?.human ?? "0 B" },
              { k: "Exported files", v: metrics.disk?.file_count ?? 0 },
            ]},
            { title: "Exports", rows: [
              { k: "Success rate", v: (metrics.exports?.success_rate ?? 0) + "%" },
              { k: "Average duration", v: (metrics.exports?.average_duration_seconds ?? 0) + "s" },
              { k: "Total files", v: metrics.exports?.total_files ?? 0 },
            ]},
          ];
          this.system = sys;
          this.remote = remote || {};
          this.backups = (backupsData && backupsData.backups) || [];
          this.buildSystem(sys, remote || {});
        })
        .catch((e) => window.oem && window.oem.toast("Failed to load settings", "error", e.message))
        .finally(() => (this.loading = false));
    },

    switchSettingsTab(slug) {
      this.settingsActiveTab = slug;
      if (slug === "logs" && this.logLines.length === 0) this.selectLog(this.activeLog || "app");
      if (slug === "general") this.loadSettings();
      if (slug === "notifications") this.loadNotifications();
      if (slug === "backups") this.loadBackups();
      if (slug === "remote-access") this.loadRemoteAccess();
    },

    loadBackups() {
      fetchJSON("/api/backups").then(d => { this.backups = (d && d.backups) || []; }).catch(() => {});
    },

    loadRemoteAccess() {
      fetchJSON("/api/remote-access").then(d => {
        this.remote = d || {};
        // Build remoteRows if not already built by buildSystem
        if (!this.remoteRows.length) {
          const ts = (d.tailscale || {}), cf = (d.cloudflare || {}), https = (d.https || {});
          const proxies = (d.reverse_proxies || []).filter(p => p.installed).map(p => p.name).join(", ");
          const badge = (ok, instOnly) => (ok ? "badge-ok" : instOnly ? "badge-warn" : "badge-muted");
          this.remoteRows = [
            { k: "Hostname", v: d.hostname || "—" },
            { k: "Tailscale", badge: ts.connected ? "Connected" : ts.installed ? "Idle" : "Off", cls: badge(ts.connected, ts.installed), v: ts.detail || "" },
            { k: "Cloudflare Tunnel", badge: cf.connected ? "Connected" : cf.installed ? "Idle" : "Off", cls: badge(cf.connected, cf.installed), v: cf.detail || "" },
            { k: "HTTPS", badge: https.enabled ? "On" : "Off", cls: https.enabled ? "badge-ok" : "badge-muted", v: (https.letsencrypt_domains || []).join(", ") },
            { k: "Reverse Proxy", v: proxies || "none detected" },
          ];
        }
      }).catch(() => {});
    },

    setTheme(mode) {
      const dark = mode === "dark";
      document.documentElement.classList.toggle("dark", dark);
      try { localStorage.setItem("oem-theme", dark ? "dark" : "light"); } catch (e) {}
      if (window.oem) { window.oem.isDark = dark; }
    },

    sortBy(key) {
      if (this.sortKey === key) this.sortDir = this.sortDir === "asc" ? "desc" : "asc";
      else { this.sortKey = key; this.sortDir = "asc"; }
    },

    // ── Retention / Cleanup ──────────────────────────────────────────
    saveRetention() {
      const days = parseInt(this.retentionDays) || 0;
      fetch("/api/settings/retention", {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ retention_days: Math.max(0, days) }),
      }).then(r => r.json()).then(d => {
        this.retentionDays = d.retention_days;
        if (window.oem) window.oem.toast("Saved", "success", `Retention: ${d.retention_days} days`);
      }).catch(e => { if (window.oem) window.oem.toast("Save failed", "error", e.message); });
    },

    runCleanup() {
      if (window.oem) window.oem.toast("Cleaning up…", "info");
      fetch("/api/cleanup/run", { method: "POST" }).then(r => r.json()).then(d => {
        if (d.error) throw new Error(d.error);
        if (window.oem) window.oem.toast("Cleanup done", "success", `${d.cleaned} folders removed (${d.freed_human})`);
      }).catch(e => { if (window.oem) window.oem.toast("Cleanup failed", "error", e.message); });
    },

    loadNotifications() {
      this.loading = true;
      fetchJSON("/api/notifications")
        .then((d) => {
          this.notifChannels = d.channels || [];
          this.notifKinds = d.kinds || this.notifKinds;
          this.notifSeverities = d.severities || this.notifSeverities;
          this.notifEnabled = d.enabled !== false;
        })
        .catch((e) => window.oem && window.oem.toast("Failed to load notifications", "error", e.message))
        .finally(() => (this.loading = false));
    },

    resetNotifForm() {
      this.notifForm = { id: "", name: "", kind: "discord", target: "", min_severity: "info", enabled: true, options: {} };
    },

    editNotification(ch) {
      this.notifForm = {
        id: ch.id,
        name: ch.name || "",
        kind: ch.kind || "webhook",
        target: ch.target || "",
        min_severity: ch.min_severity || "info",
        enabled: ch.enabled !== false,
        options: Object.assign({}, ch.options || {}),
      };
      window.scrollTo({ top: 0, behavior: "smooth" });
    },

    saveNotification() {
      const f = this.notifForm;
      if (!(f.name || "").trim()) return window.oem && window.oem.toast("Channel name is required", "error");
      if (!(f.target || "").trim()) return window.oem && window.oem.toast("Target/URL is required", "error");
      const body = {
        name: f.name,
        kind: f.kind,
        target: f.target,
        min_severity: f.min_severity,
        enabled: f.enabled === true || f.enabled === "true",
        options: f.options || {},
      };
      const url = f.id ? `/api/notifications/${f.id}` : "/api/notifications";
      const method = f.id ? "PUT" : "POST";
      fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
        .then((r) => r.json())
        .then((d) => {
          if (d.error) throw new Error(d.error);
          window.oem && window.oem.toast(f.id ? "Channel updated" : "Channel added", "success");
          this.resetNotifForm();
          this.loadNotifications();
        })
        .catch((e) => window.oem && window.oem.toast("Save failed", "error", e.message));
    },

    deleteNotification(id) {
      if (!confirm("Delete this notification channel?")) return;
      fetch(`/api/notifications/${id}`, { method: "DELETE" })
        .then((r) => r.json())
        .then((d) => {
          if (d.error) throw new Error(d.error);
          window.oem && window.oem.toast("Channel deleted", "success");
          this.loadNotifications();
        })
        .catch((e) => window.oem && window.oem.toast("Delete failed", "error", e.message));
    },

    testNotification(id) {
      window.oem && window.oem.toast("Sending test…", "info");
      fetch(`/api/notifications/${id}/test`, { method: "POST" })
        .then((r) => r.json())
        .then((d) => {
          if (d.error) throw new Error(d.error);
          if (d.ok) window.oem && window.oem.toast("Test delivered", "success", d.detail);
          else window.oem && window.oem.toast("Test failed", "error", d.detail);
        })
        .catch((e) => window.oem && window.oem.toast("Test failed", "error", e.message));
    },

    // ── System page ────────────────────────────────────────────────
    loadSystem() {
      this.loading = true;
      Promise.all([
        fetchJSON("/api/system"),
        fetchJSON("/api/remote-access").catch(() => ({})),
        fetchJSON("/api/backups").catch(() => ({ backups: [] })),
      ])
        .then(([sys, remote, backups]) => {
          this.system = sys;
          this.remote = remote || {};
          this.backups = (backups && backups.backups) || [];
          this.buildSystem(sys, remote || {});
        })
        .catch((e) => window.oem && window.oem.toast("Failed to load system", "error", e.message))
        .finally(() => (this.loading = false));
    },

    buildSystem(payload, remote) {
      const s = payload.system || {};
      const mem = s.memory || {};
      const disk = s.disk || {};
      const tempBadge = s.temperature_c != null ? (s.temperature_c >= 75 ? "hot" : "") : "";
      this.systemCards = [
        { key: "cpu", label: "CPU", value: (s.cpu_percent ?? 0) + "%", icon: ICONS.activity || ICONS.bolt, accent: (s.cpu_percent ?? 0) > 85 ? "accent-danger" : "" },
        { key: "ram", label: "RAM", value: (mem.percent ?? 0) + "%", icon: ICONS.layers, badge: mem.used_human ? mem.used_human + " / " + mem.total_human : "", accent: (mem.percent ?? 0) > 90 ? "accent-danger" : "" },
        { key: "temp", label: "Temperature", value: s.temperature_c != null ? s.temperature_c + "°C" : "—", icon: ICONS.activity || ICONS.bolt, accent: tempBadge === "hot" ? "accent-danger" : "" },
        { key: "disk", label: "Disk", value: (disk.percent ?? 0) + "%", icon: ICONS.files, badge: disk.used_human ? disk.used_human + " / " + disk.total_human : "", accent: (disk.percent ?? 0) > 90 ? "accent-danger" : "" },
        { key: "uptime", label: "Uptime", value: s.uptime_human || "—", icon: ICONS.clock },
        { key: "jobs", label: "Running / Queue", value: (payload.jobs_running ?? 0) + " / " + (payload.jobs_queued ?? 0), icon: ICONS.queue, badge: (payload.workers ?? 0) + " workers" },
      ];

      const ts = remote.tailscale || {};
      const cf = remote.cloudflare || {};
      const https = remote.https || {};
      const proxies = (remote.reverse_proxies || []).filter((p) => p.installed).map((p) => p.name).join(", ");
      const badge = (ok, instOnly) => (ok ? "badge-ok" : instOnly ? "badge-warn" : "badge-muted");
      this.remoteRows = [
        { k: "Hostname", v: s.hostname || "—" },
        { k: "Device", v: s.pi_model || (s.platform + " / " + s.machine) },
        { k: "Tailscale", badge: ts.connected ? "Connected" : ts.installed ? "Idle" : "Off", cls: badge(ts.connected, ts.installed), v: ts.detail || "" },
        { k: "Cloudflare Tunnel", badge: cf.connected ? "Connected" : cf.installed ? "Idle" : "Off", cls: badge(cf.connected, cf.installed), v: cf.detail || "" },
        { k: "HTTPS", badge: https.enabled ? "On" : "Off", cls: https.enabled ? "badge-ok" : "badge-muted", v: (https.letsencrypt_domains || []).join(", ") },
        { k: "Reverse Proxy", v: proxies || "none detected" },
      ];
    },

    workerControl(action) {
      fetch(`/api/worker/${action}`, { method: "POST" })
        .then((r) => r.json())
        .then((w) => {
          if (w.error) throw new Error(w.error);
          this.system = { ...this.system, worker: w };
          window.oem && window.oem.toast(action === "start" ? "Worker started" : "Worker stopped", "success");
        })
        .catch((e) => window.oem && window.oem.toast("Worker control failed", "error", e.message));
    },

    createBackup() {
      if (this.backupBusy) return;
      this.backupBusy = true;
      fetch("/api/backups", { method: "POST" })
        .then((r) => r.json())
        .then((info) => {
          if (info.error) throw new Error(info.error);
          window.oem && window.oem.toast("Backup created", "success", info.name);
          return fetchJSON("/api/backups");
        })
        .then((d) => (this.backups = (d && d.backups) || this.backups))
        .catch((e) => window.oem && window.oem.toast("Backup failed", "error", e.message))
        .finally(() => (this.backupBusy = false));
    },

    get canRunExport() {
      return !!(this.manual.label && !this.exportBusy);
    },

    get estimateCards() {
      const e = (this.preview && this.preview.estimates) || {};
      return [
        { key: "documents", label: "Documents", value: e.documents_label || "Preview", icon: ICONS.files },
        { key: "api", label: "API Calls", value: e.api_calls_label || "—", icon: ICONS.activity },
        { key: "runtime", label: "Runtime", value: e.runtime_label || "—", icon: ICONS.clock },
        { key: "storage", label: "Storage", value: e.storage_label || "—", icon: ICONS.layers },
      ];
    },

    get previewChecks() {
      if (this.preview && Array.isArray(this.preview.checks) && this.preview.checks.length) {
        return this.preview.checks;
      }
      return [
        {
          key: "planner",
          label: "Planner",
          status: this.manual.label ? "pending" : "warning",
          detail: this.manual.label ? "Waiting for preview" : "Choose a label",
        },
      ];
    },

    get previewTimeline() {
      return (this.preview && this.preview.timeline) || [];
    },

    formatTime(iso) {
      return relativeTime(iso);
    },

    selectLog(area) {
      this.activeLog = area;
      this.loading = true;
      fetchJSON(`/api/logs/${area}?limit=300`)
        .then((d) => {
          this.logLines = d.lines || [];
          this.$nextTick(() => {
            const v = this.$refs.logView;
            if (v) v.scrollTop = v.scrollHeight;
          });
        })
        .catch(() => (this.logLines = []))
        .finally(() => (this.loading = false));
    },
    logClass(line) {
      if (/\bERROR\b|\bCRITICAL\b/.test(line)) return "lvl-error";
      if (/\bWARNING\b|\bWARN\b/.test(line)) return "lvl-warn";
      if (/\bINFO\b/.test(line)) return "lvl-info";
      return "";
    },

    setTheme(mode) {
      const dark = mode === "dark";
      document.documentElement.classList.toggle("dark", dark);
      try { localStorage.setItem("oem-theme", dark ? "dark" : "light"); } catch (e) {}
      if (window.oem) { window.oem.isDark = dark; }
    },

    get visibleRows() {
      let rows = [...this.rows];
      const f = this.filter.trim().toLowerCase();
      if (f) {
        rows = rows.filter((r) => JSON.stringify(r).toLowerCase().includes(f));
      }
      if (this.sortKey) {
        const k = this.sortKey;
        rows.sort((a, b) => {
          const av = this.pick(a, k), bv = this.pick(b, k);
          if (av === bv) return 0;
          const cmp = av > bv ? 1 : -1;
          return this.sortDir === "asc" ? cmp : -cmp;
        });
      }
      return rows;
    },

    pick(row, key) {
      return key.split(".").reduce((o, k) => (o == null ? undefined : o[k]), row);
    },

    renderCell(col, row) {
      const v = this.pick(row, col.key);
      switch (col.type) {
        case "strong":
          return `<strong>${escapeHtml(v)}</strong>`;
        case "code":
          return v ? `<code>${escapeHtml(v)}</code>` : "—";
        case "number":
          return `${v ?? 0}`;
        case "seconds":
          return `${v ?? 0}s`;
        case "time":
          return `<span title="${escapeHtml(v)}">${relativeTime(v)}</span>`;
        case "join":
          return Array.isArray(v) && v.length ? v.map(escapeHtml).join(", ") : "—";
        case "bool":
          return v
            ? `<span class="badge badge-ok">Yes</span>`
            : `<span class="badge badge-muted">No</span>`;
        case "result":
          return v
            ? `<span class="badge badge-ok">Success</span>`
            : `<span class="badge badge-fail">Failed</span>`;
        case "badge": {
          const map = { available: "badge-ok", healthy: "badge-ok", completed: "badge-ok", running: "badge-warn", pending: "badge-muted", rate_limited: "badge-warn", failed: "badge-fail", cancelled: "badge-muted" };
          return `<span class="badge ${map[v] || "badge-muted"}">${escapeHtml(v)}</span>`;
        }
        case "queue-actions": {
          const status = row.status;
          const id = escapeHtml(v);
          const buttons = [];
          if (status === "pending" || status === "running") {
            buttons.push(`<button class="btn btn-ghost btn-sm" data-qaction="cancel" data-qid="${id}">Cancel</button>`);
          }
          if (status === "failed" || status === "cancelled") {
            buttons.push(`<button class="btn btn-ghost btn-sm" data-qaction="retry" data-qid="${id}">Retry</button>`);
          }
          return buttons.join(" ") || "—";
        }
        default:
          return v === null || v === undefined || v === "" ? "—" : escapeHtml(v);
      }
    },

    get manualCommand() {
      let cmd = `python -m onshape_export_manager.cli --run-export "${this.manual.label || "Label"}"`;
      if (this.manual.profile) cmd += ` --profile "${this.manual.profile}"`;
      if (this.manual.start) cmd += ` --start ${this.manual.start}`;
      if (this.manual.end) cmd += ` --end ${this.manual.end}`;
      return cmd;
    },

    copy(text) {
      navigator.clipboard &&
        navigator.clipboard.writeText(text).then(
          () => window.oem && window.oem.toast("Copied to clipboard", "success"),
          () => window.oem && window.oem.toast("Copy failed", "error")
        );
    },
  };
}

/* Register with Alpine's registry so initialization never races the
   defer-loaded factory definitions. */
// -- Tree Selector (Self-contained School accordions) --------------------

let treeSelector = () => ({
  organisations: [],
  accounts: [],
  loading: true,
  expanded: {},
  selected: {},
  selectAllOrgs: {},
  icons: ICONS,

  // ── All forms are INLINE — nothing floats at page level ──────────────

  showNewOrgForm: false,
  newOrgForm: { name: "", type: "company", description: "" },

  editingOrgId: null,
  editOrgForm: { name: "", type: "company", description: "" },

  credFormOrgId: null,
  credForm: { name: "", access_key: "", secret_key: "", environment: "production" },

  groupFormOrgId: null,
  groupForm: { name: "", onshape_id: "", profile: "STL", schedule: "" },

  // Inline delete confirmations (org-level or group-level)
  orgToDelete: null,
  orgToDeleteName: "",
  credToDelete: null,       // "orgId::credId"
  credToDeleteName: "",
  groupToDelete: null,

  async init() { await this.loadTree(); },

  async loadTree() {
    this.loading = true;
    try {
      const resp = await fetchJSON("/api/tree");
      this.organisations = resp.organisations || [];
      this.accounts = this.organisations;
      window.__treeData = resp; // shared cache for sectionPage (avoids double fetch)
    } catch (e) { console.warn("Tree load failed", e); }
    this.loading = false;
  },

  // ── Expand / Select ──────────────────────────────────────────────────

  toggle(orgName) { this.expanded[orgName] = !this.expanded[orgName]; },
  toggleOrg(orgName) {
    const org = this.organisations.find(a => a.name === orgName);
    if (!org) return;
    const select = !this.selectAllOrgs[orgName];
    this.selectAllOrgs[orgName] = select;
    for (const g of (org.groups || [])) this.selected[g.friendly_name] = select;
  },
  toggleAccount(n) { return this.toggleOrg(n); },
  toggleGroup(n) { this.selected[n] = !this.selected[n]; },

  get selectedCount() { return Object.values(this.selected).filter(Boolean).length; },
  get selectedLabels() { return Object.keys(this.selected).filter(k => this.selected[k]); },

  // ── Create School (inline at top of list) ───────────────────────────

  async createOrg() {
    const f = this.newOrgForm;
    if (!(f.name || "").trim()) { if (window.oem) window.oem.toast("Name required", "error"); return; }
    try {
      const r = await fetch("/api/organizations", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: f.name.trim(), type: f.type, description: (f.description || "").trim() }),
      });
      const d = await r.json();
      if (d.error) throw new Error(d.error);
      if (window.oem) window.oem.toast("Created", "success", d.name);
      this.showNewOrgForm = false;
      this.newOrgForm = { name: "", type: "company", description: "" };
      await this.loadTree();
    } catch (e) { if (window.oem) window.oem.toast("Create org failed", "error", e.message); }
  },

  // ── Edit School (inline within the org card) ─────────────────────────

  startEditOrg(org) {
    this.editingOrgId = org.id;
    this.editOrgForm = { name: org.name || "", type: org.type || "company", description: org.description || "" };
  },
  cancelEditOrg() { this.editingOrgId = null; },

  async saveEditOrg(orgId) {
    const f = this.editOrgForm;
    if (!(f.name || "").trim()) { if (window.oem) window.oem.toast("Name required", "error"); return; }
    try {
      const r = await fetch(`/api/organizations/${orgId}`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: f.name.trim(), type: f.type, description: (f.description || "").trim() }),
      });
      const d = await r.json();
      if (d.error) throw new Error(d.error);
      if (window.oem) window.oem.toast("Updated", "success", d.name);
      this.editingOrgId = null;
      await this.loadTree();
    } catch (e) { if (window.oem) window.oem.toast("Edit org failed", "error", e.message); }
  },

  // ── Delete / Duplicate School ────────────────────────────────────────

  confirmOrgDelete(orgId, orgName) { this.orgToDelete = orgId; this.orgToDeleteName = orgName; },
  cancelOrgDelete() { this.orgToDelete = null; this.orgToDeleteName = ""; },

  async deleteOrg(orgId) {
    try {
      const r = await fetch(`/api/organizations/${orgId}`, { method: "DELETE" });
      const d = await r.json();
      if (d.error) throw new Error(d.error);
      if (window.oem) window.oem.toast("Deleted", "success", "School removed");
      this.orgToDelete = null;
      await this.loadTree();
    } catch (e) { if (window.oem) window.oem.toast("Delete org failed", "error", e.message); }
  },

  async duplicateOrg(orgId) {
    try {
      const r = await fetch(`/api/organizations/${orgId}/duplicate`, { method: "POST" });
      const d = await r.json();
      if (d.error) throw new Error(d.error);
      if (window.oem) window.oem.toast("Duplicated", "success", d.name);
      await this.loadTree();
    } catch (e) { if (window.oem) window.oem.toast("Duplicate org failed", "error", e.message); }
  },

  // ── Credentials (inline within the API Keys section) ─────────────────

  toggleCredForm(orgId) {
    this.credFormOrgId = (this.credFormOrgId === orgId) ? null : orgId;
    if (this.credFormOrgId) this.credForm = { name: "", access_key: "", secret_key: "", environment: "production" };
  },

  async addCredential(orgId) {
    const f = this.credForm;
    if (!(f.name || "").trim() || !(f.access_key || "").trim() || !(f.secret_key || "").trim()) {
      if (window.oem) window.oem.toast("All fields required", "error"); return;
    }
    try {
      const r = await fetch(`/api/organizations/${orgId}/credentials`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: f.name.trim(), access_key: f.access_key.trim(), secret_key: f.secret_key.trim(), environment: f.environment }),
      });
      const d = await r.json();
      if (d.error) throw new Error(d.error);
      if (window.oem) window.oem.toast("Added", "success", d.name);
      this.credFormOrgId = null;
      await this.loadTree();
    } catch (e) { if (window.oem) window.oem.toast("Add key failed", "error", e.message); }
  },

  confirmCredDelete(orgId, credId, credName) {
    this.credToDelete = `${orgId}::${credId}`;
    this.credToDeleteName = credName;
  },
  cancelCredDelete() { this.credToDelete = null; this.credToDeleteName = ""; },

  async deleteCredential() {
    const parts = (this.credToDelete || "").split("::");
    const orgId = parts[0];
    const credId = parts.slice(1).join("::");
    if (!orgId || !credId) return;
    try {
      const r = await fetch(`/api/organizations/${orgId}/credentials/${encodeURIComponent(credId)}`, { method: "DELETE" });
      const d = await r.json();
      if (d.error) throw new Error(d.error);
      if (window.oem) window.oem.toast("Removed", "success", "API key deleted");
      this.credToDelete = null;
      await this.loadTree();
    } catch (e) { if (window.oem) window.oem.toast("Delete key failed", "error", e.message); }
  },

  // ── Groups (inline within the Groups section) ────────────────────────

  toggleGroupForm(orgId) {
    this.groupFormOrgId = (this.groupFormOrgId === orgId) ? null : orgId;
    if (this.groupFormOrgId) this.groupForm = { name: "", onshape_id: "", profile: "STL", schedule: "" };
  },

  async createGroup(orgId) {
    const f = this.groupForm;
    if (!(f.name || "").trim()) { if (window.oem) window.oem.toast("Group name required", "error"); return; }
    if (!(f.onshape_id || "").trim()) { if (window.oem) window.oem.toast("Label ID required", "error"); return; }
    const org = this.organisations.find(o => o.id === orgId);
    // Use credential names (not org name) so the tree API can match groups to orgs
    const credNames = org ? (org.credentials || []).map(c => c.name) : [];
    const body = {
      friendly_name: f.name.trim(), onshape_label_id: f.onshape_id.trim(),
      assigned_accounts: credNames.length ? credNames : (org ? [org.name] : []),
      export_profile: f.profile || "STL",
    };
    if (f.schedule) body.scheduler = { interval: f.schedule, enabled: true };
    try {
      const r = await fetch("/api/groups", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      });
      const d = await r.json();
      if (d.error) throw new Error(d.error);
      if (window.oem) window.oem.toast("Created", "success", d.friendly_name);
      this.groupFormOrgId = null;
      await this.loadTree();
    } catch (e) { if (window.oem) window.oem.toast("Create group failed", "error", e.message); }
  },

  confirmDelete(groupName) { this.groupToDelete = groupName; },
  cancelDelete() { this.groupToDelete = null; },

  async deleteGroup(groupName) {
    try {
      const r = await fetch(`/api/groups/${encodeURIComponent(groupName)}`, { method: "DELETE" });
      const d = await r.json();
      if (d.error) throw new Error(d.error);
      if (window.oem) window.oem.toast("Deleted", "success", `${groupName} removed`);
      this.groupToDelete = null;
      this.selected[groupName] = false;
      await this.loadTree();
    } catch (e) { if (window.oem) window.oem.toast("Delete group failed", "error", e.message); }
  },

  async moveGroup(groupName, targetOrgName) {
    if (!targetOrgName) return;
    // Resolve org name to its first credential name (backend uses account names)
    const targetOrg = this.organisations.find(o => o.name === targetOrgName);
    const credName = (targetOrg && targetOrg.credentials && targetOrg.credentials.length)
      ? targetOrg.credentials[0].name : targetOrgName;
    try {
      const r = await fetch(`/api/groups/${encodeURIComponent(groupName)}/move`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ account: credName }),
      });
      const d = await r.json();
      if (d.error) throw new Error(d.error);
      if (window.oem) window.oem.toast("Moved", "success", `Group moved to ${targetOrgName}`);
      await this.loadTree();
    } catch (e) { if (window.oem) window.oem.toast("Move group failed", "error", e.message); }
  },

  async toggleGroupEnabled(groupName, currentlyEnabled) {
    try {
      const newEnabled = currentlyEnabled === false ? true : false;
      const r = await fetch(`/api/groups/${encodeURIComponent(groupName)}`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: newEnabled }),
      });
      const d = await r.json();
      if (d.error) throw new Error(d.error);
      await this.loadTree();
    } catch (e) { if (window.oem) window.oem.toast("Toggle group failed", "error", e.message); }
  },

  // ── Batch Export ─────────────────────────────────────────────────────

  queueExport() {
    const labels = this.selectedLabels;
    if (!labels.length) return;
    fetch("/api/exports/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ labels }) })
      .then(r => r.json())
      .then(r => {
        if (r.error) throw new Error(r.error);
        if (window.oem) window.oem.toast("Queued", "success", `${r.count} export(s) enqueued`);
        for (const l of labels) this.selected[l] = false;
        for (const k of Object.keys(this.selectAllOrgs)) this.selectAllOrgs[k] = false;
      })
      .catch(e => { if (window.oem) window.oem.toast("Export failed", "error", e.message); });
  },
});


document.addEventListener("alpine:init", () => {
  window.Alpine.data("appShell", appShell);
  window.Alpine.data("dashboardPage", dashboardPage);
  window.Alpine.data("sectionPage", sectionPage);
  window.Alpine.data("treeSelector", treeSelector);
});
