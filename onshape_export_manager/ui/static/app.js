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

function templateId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `tpl-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/* ---------------- App shell ---------------- */
function appShell() {
  return {
    icons: ICONS,
    isDark: true,
    collapsed: false,
    mobileOpen: false,
    connected: false,
    summary: {},
    toasts: [],
    _toastId: 0,
    palette: { open: false, query: "", groups: [], loading: false },

    init() {
      this.isDark = document.documentElement.classList.contains("dark");
      this.collapsed = localStorage.getItem("oem-collapsed") === "1";
      this.startLiveUpdates();
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
      if (meta && e.key.toLowerCase() === "k") {
        e.preventDefault();
        this.palette.open ? this.closePalette() : this.openPalette();
      } else if (meta && e.key.toLowerCase() === "b") {
        e.preventDefault();
        this.toggleSidebar();
      } else if (e.key === "/" && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) {
        e.preventDefault();
        this.openPalette();
      }
    },

    openPalette() {
      this.palette.open = true;
      this.$nextTick(() => this.$refs.paletteInput && this.$refs.paletteInput.focus());
    },
    closePalette() {
      this.palette.open = false;
      this.palette.query = "";
      this.palette.groups = [];
    },
    runSearch() {
      const q = this.palette.query.trim();
      if (!q) {
        this.palette.groups = [];
        return;
      }
      this.palette.loading = true;
      fetchJSON(`/api/search?q=${encodeURIComponent(q)}`)
        .then((data) => {
          this.palette.groups = data.groups || [];
        })
        .catch(() => {})
        .finally(() => (this.palette.loading = false));
    },

    startLiveUpdates() {
      if (typeof EventSource !== "undefined") {
        try {
          const es = new EventSource("/api/stream");
          es.onmessage = (ev) => {
            this.connected = true;
            try {
              this.summary = JSON.parse(ev.data);
            } catch (e) {}
            window.dispatchEvent(new CustomEvent("oem-summary", { detail: this.summary }));
          };
          es.onerror = () => {
            this.connected = false;
          };
          return;
        } catch (e) {}
      }
      // Fallback polling
      const poll = () =>
        fetchJSON("/api/summary")
          .then((d) => {
            this.connected = true;
            this.summary = d;
          })
          .catch(() => (this.connected = false));
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

/* ---------------- Dashboard ---------------- */
function dashboardPage() {
  return {
    loading: true,
    metrics: {},
    cards: [],
    recent: [],
    healthLegend: [],
    queueRows: [],
    _charts: {},

    load() {
      this.loading = true;
      fetchJSON("/api/metrics")
        .then((data) => {
          this.metrics = data;
          this.build(data);
          this.$nextTick(() => this.renderCharts(data));
        })
        .catch((e) => window.oem && window.oem.toast("Failed to load metrics", "error", e.message))
        .finally(() => (this.loading = false));
      window.addEventListener("oem-summary", () => this.refreshQuietly());
      window.addEventListener("oem-theme", () => this.$nextTick(() => this.renderCharts(this.metrics)));
    },

    refreshQuietly() {
      fetchJSON("/api/metrics").then((data) => {
        this.metrics = data;
        this.build(data);
        this.renderCharts(data);
      });
    },

    build(d) {
      const s = d.summary || {};
      this.cards = [
        { key: "apikeys", label: "API Keys", value: s.accounts ?? 0, icon: ICONS.accounts, badge: `${s.healthy_accounts ?? 0} healthy`, accent: "", href: "/api-keys" },
        { key: "labels", label: "Labels", value: s.labels ?? 0, icon: ICONS.labels, accent: "", href: "/labels" },
        { key: "exports", label: "Total Exports", value: s.total_exports ?? 0, icon: ICONS.files, accent: "accent-success", href: "/history" },
        { key: "queue", label: "In Queue", value: s.queue_size ?? 0, icon: ICONS.queue, accent: "", href: "/export" },
        { key: "failed", label: "Failed", value: s.failed_exports ?? 0, icon: ICONS.alert, accent: (s.failed_exports ?? 0) > 0 ? "accent-danger" : "", href: "/history" },
      ];
      this.recent = d.recent_history || [];

      const health = d.account_health || {};
      const palette = { healthy: "#34d399", degraded: "#fbbf24", rate_limited: "#fb923c", failed: "#f87171", disabled: "#6b7192" };
      this.healthLegend = Object.keys(palette)
        .filter((k) => (health[k] || 0) > 0)
        .map((k) => ({ label: k.replace("_", " "), count: health[k], color: palette[k] }));
      if (this.healthLegend.length === 0) this.healthLegend = [{ label: "no accounts", count: 0, color: "#6b7192" }];

      const q = (d.queue && d.queue.counts) || {};
      const max = Math.max(1, ...Object.values(q));
      this.queueRows = ["pending", "running", "completed", "failed", "cancelled"].map((k) => ({
        label: k,
        count: q[k] || 0,
        pct: ((q[k] || 0) / max) * 100,
        cls: "q-" + k,
      }));
    },

    renderCharts(d) {
      if (typeof Chart === "undefined") {
        setTimeout(() => this.renderCharts(d), 200);
        return;
      }
      const css = getComputedStyle(document.documentElement);
      const grid = css.getPropertyValue("--border").trim();
      const text = css.getPropertyValue("--text-muted").trim();
      Chart.defaults.color = text;
      Chart.defaults.font.family = "Inter, sans-serif";

      const act = (d.exports && d.exports.activity) || { labels: [], success: [], failed: [] };
      this.upsertChart("activityChart", {
        type: "line",
        data: {
          labels: act.labels.map((x) => x.slice(5)),
          datasets: [
            this.area("Success", act.success, "#34d399"),
            this.area("Failed", act.failed, "#f87171"),
          ],
        },
        options: {
          responsive: true, maintainAspectRatio: false, animation: false, resizeDelay: 0,
          interaction: { mode: "index", intersect: false },
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } },
            y: { grid: { color: grid }, beginAtZero: true, ticks: { precision: 0 } },
          },
        },
      });

      const health = d.account_health || {};
      const labels = ["healthy", "degraded", "rate_limited", "failed", "disabled"].filter((k) => (health[k] || 0) > 0);
      const colors = { healthy: "#34d399", degraded: "#fbbf24", rate_limited: "#fb923c", failed: "#f87171", disabled: "#6b7192" };
      this.upsertChart("healthChart", {
        type: "doughnut",
        data: {
          labels: labels.length ? labels : ["none"],
          datasets: [{
            data: labels.length ? labels.map((k) => health[k]) : [1],
            backgroundColor: labels.length ? labels.map((k) => colors[k]) : ["#2a2d40"],
            borderWidth: 0, hoverOffset: 6,
          }],
        },
        options: { responsive: true, maintainAspectRatio: false, animation: false, resizeDelay: 0, cutout: "68%", plugins: { legend: { display: false } } },
      });
    },

    area(label, data, color) {
      return {
        label, data, borderColor: color, backgroundColor: color + "22",
        fill: true, tension: 0.38, borderWidth: 2, pointRadius: 0, pointHoverRadius: 4,
      };
    },

    upsertChart(ref, config) {
      const el = this.$refs[ref];
      if (!el) return;
      if (this._charts[ref]) this._charts[ref].destroy();
      this._charts[ref] = new Chart(el.getContext("2d"), config);
    },

    formatTime(iso) {
      return relativeTime(iso);
    },
  };
}

/* ---------------- Section pages ---------------- */
const PAGE_CONFIG = {
  // ── New Phase 0 pages ────────────────────────────────────────────
  "api-keys": {
    // Unified view: organizations + credentials merged.
    // Renders the organizations template (cards with nested creds).
    endpoint: "/api/organizations",
    root: "organizations",
    empty: "No API keys configured yet. Add your Onshape API key to get started.",
    columns: [],  // card-based, not table
  },
  export: {
    // Merged manual-export + queue.  Uses custom template blocks.
    endpoint: null,
    root: null,
    empty: "",
    columns: [],
  },
  // ── Legacy pages (still accessible via URL) ──────────────────────
  accounts: {
    endpoint: "/api/accounts", root: "accounts", empty: "No accounts configured yet.",
    columns: [
      { key: "name", label: "Name", type: "strong" },
      { key: "status", label: "Status", type: "badge" },
      { key: "api_usage", label: "API Usage", type: "number" },
      { key: "failure_count", label: "Failures", type: "number" },
      { key: "access_key", label: "Access Key", type: "code" },
      { key: "last_used", label: "Last Used", type: "time" },
      { key: "enabled", label: "Enabled", type: "bool" },
    ],
  },
  labels: {
    endpoint: "/api/labels", root: "labels", empty: "No labels configured yet.",
    columns: [],  // card-based view, not table
  },
  "export-profiles": {
    endpoint: "/api/profiles", root: "profiles", empty: "No export profiles yet.",
    columns: [
      { key: "name", label: "Profile", type: "strong" },
      { key: "formats", label: "Formats", type: "join" },
      { key: "bambu.enabled", label: "Bambu", type: "bool" },
      { key: "enabled", label: "Enabled", type: "bool" },
    ],
  },
  queue: {
    endpoint: "/api/queue", root: "items", empty: "The export queue is empty.",
    columns: [
      { key: "label_name", label: "Label", type: "strong" },
      { key: "profile_name", label: "Profile", type: "text" },
      { key: "status", label: "Status", type: "badge" },
      { key: "retry_count", label: "Retries", type: "number" },
      { key: "next_run_at", label: "Next Run", type: "time" },
      { key: "last_error", label: "Last Error", type: "text" },
      { key: "id", label: "Actions", type: "queue-actions" },
    ],
  },
  scheduler: {
    endpoint: "/api/scheduler", root: "jobs", empty: "No scheduled jobs configured.",
    columns: [
      { key: "name", label: "Job", type: "strong" },
      { key: "label_name", label: "Label", type: "text" },
      { key: "interval", label: "Interval", type: "text" },
      { key: "enabled", label: "Enabled", type: "bool" },
      { key: "next_run_at", label: "Next Run", type: "time" },
      { key: "last_run_at", label: "Last Run", type: "time" },
    ],
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
    tabs: [],
    activeTab: "All",
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
    manual: { label: "", profile: "", start: "", end: "", destination: "", mode: "range", preset: "today", templateId: "" },
    preview: null,
    previewBusy: false,
    exportBusy: false,
    worker: { running: false },
    manualTemplates: [],
    manualRecentTemplates: [],
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
    // organizations
    orgs: [],
    orgTypes: ["school", "company", "department", "customer", "workshop", "team", "other"],
    newOrg: { name: "", type: "company", description: "" },
    credForm: { name: "Primary", environment: "production", access_key: "", secret_key: "", priority: 1 },
    // system
    system: {},
    remote: {},
    backups: [],
    systemCards: [],
    remoteRows: [],
    backupBusy: false,
    // activity / live event feed
    events: [],
    activityCards: [],
    activityCategories: [],
    activitySeverities: [],
    activityCategory: "",
    activitySeverity: "",
    activitySummary: {},
    wsConnected: false,
    _ws: null,
    _activityPoll: null,
    // notifications
    notifChannels: [],
    notifKinds: ["discord", "slack", "teams", "email", "webhook"],
    notifSeverities: ["info", "success", "warning", "error", "critical"],
    notifEnabled: true,
    notifForm: { id: "", name: "", kind: "discord", target: "", min_severity: "info", enabled: true, options: {} },
    // plugins
    pluginHooks: [
      { name: "Export Formats", desc: "Register custom Onshape export translators." },
      { name: "Storage Providers", desc: "Ship exports to S3, SFTP, NAS, or cloud drives." },
      { name: "Notifications", desc: "Discord, Slack, Teams, email, and webhooks." },
      { name: "Post-Processing", desc: "Run slicers, scripts, or conversions after export." },
      { name: "Validators", desc: "Verify checksums and detect duplicates." },
      { name: "Reports", desc: "Generate HTML, JSON, CSV, and PDF summaries." },
    ],
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
    // label creation form
    showLabelForm: false,
    labelForm: { name: "", onshape_id: "", profile: "STL", schedule: "" },

    load() {
      // ── New Phase 0 pages ──────────────────────────────────────
      if (this.page === "api-keys") return this.loadOrganizations();
      if (this.page === "export")   return this.loadExportPage();
      if (this.page === "labels")   return this.loadLabelsPage();
      // ── Legacy pages ───────────────────────────────────────────
      if (this.page === "logs") return this.selectLog(this.activeLog);
      if (this.page === "settings") return this.loadSettings();
      if (this.page === "system") return this.loadSystem();
      if (this.page === "organizations") return this.loadOrganizations();
      if (this.page === "activity") return this.loadActivity();
      if (this.page === "notifications") return this.loadNotifications();
      if (!cfg) return this.loadAux();
      this.loading = true;
      fetchJSON(cfg.endpoint)
        .then((data) => {
          this.rows = data[cfg.root] || [];
        })
        .catch((e) => window.oem && window.oem.toast("Failed to load", "error", e.message))
        .finally(() => (this.loading = false));
    },

    // ── New: Export page (manual export + queue combined) ────────
    loadExportPage() {
      this.loading = true;
      this.loadManualTemplates();
      this.ensureManualWindow();
      Promise.all([
        fetchJSON("/api/labels"),
        fetchJSON("/api/profiles"),
        fetchJSON("/api/worker").catch(() => ({ running: false })),
        fetchJSON("/api/queue").catch(() => ({ items: [] })),
      ])
        .then(([labels, profiles, worker, queue]) => {
          this.rows = labels.labels || [];
          this.profiles = profiles.profiles || [];
          this.worker = worker || { running: false };
          this.queueItems = (queue && queue.items) || [];
          if (this.rows.length && !this.manual.label) {
            this.manual.label = this.rows[0].friendly_name;
          }
          this.schedulePreview(100);
        })
        .catch((e) => window.oem && window.oem.toast("Failed to load export planner", "error", e.message))
        .finally(() => (this.loading = false));
    },

    // ── Labels page (card view) ──────────────────────────────────
    loadLabelsPage() {
      this.loading = true;
      Promise.all([
        fetchJSON("/api/labels"),
        fetchJSON("/api/profiles").catch(() => ({ profiles: [] })),
      ])
        .then(([labelsData, profilesData]) => {
          this.rows = labelsData.labels || [];
          this.profiles = profilesData.profiles || [];
        })
        .catch((e) => window.oem && window.oem.toast("Failed to load labels", "error", e.message))
        .finally(() => (this.loading = false));
    },

    createLabel() {
      const f = this.labelForm;
      if (!(f.name || "").trim()) return window.oem && window.oem.toast("Label name is required", "error");
      const body = {
        friendly_name: f.name.trim(),
        onshape_label_id: (f.onshape_id || "").trim(),
        export_profile: f.profile || "STL",
      };
      if (f.schedule) body.scheduler = { interval: f.schedule, enabled: true };
      fetch("/api/labels", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
        .then((r) => r.json())
        .then((d) => {
          if (d.error) throw new Error(d.error);
          window.oem && window.oem.toast("Label created", "success", f.name);
          this.showLabelForm = false;
          this.labelForm = { name: "", onshape_id: "", profile: "STL", schedule: "" };
          this.loadLabelsPage();
        })
        .catch((e) => window.oem && window.oem.toast("Create failed", "error", e.message));
    },

    triggerLabelExport(labelName) {
      if (!labelName) return;
      fetch("/api/exports/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label: labelName, profile: "", start: new Date().toISOString().slice(0, 10), end: "" }),
      })
        .then((r) => r.json())
        .then((d) => {
          if (d.error) throw new Error(d.error);
          window.oem && window.oem.toast("Export queued", "success", labelName);
        })
        .catch((e) => window.oem && window.oem.toast("Export failed", "error", e.message));
    },

    loadAux() {
      // manual-export / export need label list
      if (this.page === "manual-export" || this.page === "export") {
        this.loading = true;
        this.loadManualTemplates();
        this.ensureManualWindow();
        const fetches = [
          fetchJSON("/api/labels"),
          fetchJSON("/api/profiles"),
          fetchJSON("/api/worker").catch(() => ({ running: false })),
        ];
        if (this.page === "export") {
          fetches.push(fetchJSON("/api/queue").catch(() => ({ items: [] })));
        }
        Promise.all(fetches)
          .then(([labels, profiles, worker, queue]) => {
            this.rows = labels.labels || [];
            this.profiles = profiles.profiles || [];
            if (this.rows.length && !this.manual.label) this.manual.label = this.rows[0].friendly_name;
            this.worker = worker || { running: false };
            if (queue) this.queueItems = (queue && queue.items) || [];
            this.schedulePreview(100);
          })
          .catch((e) => window.oem && window.oem.toast("Failed to load export planner", "error", e.message))
          .finally(() => (this.loading = false));
      }
    },

    initManualPlanner() {
      if (this.page !== "manual-export" && this.page !== "export") return;
      this.loadManualTemplates();
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
      this.exportBusy = true;
      fetch("/api/exports/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.manualRequestBody()),
      })
        .then((r) => r.json())
        .then((d) => {
          if (d.error) throw new Error(d.error);
          window.oem && window.oem.toast("Export queued", "success", `${d.label} · ${d.profile}`);
          this.rememberRecentTemplate(this.currentTemplateSnapshot(`${d.label} · ${d.profile}`));
          fetchJSON("/api/worker").then((w) => (this.worker = w || this.worker)).catch(() => {});
        })
        .catch((e) => window.oem && window.oem.toast("Could not queue export", "error", e.message))
        .finally(() => (this.exportBusy = false));
    },

    loadManualTemplates() {
      try {
        this.manualTemplates = JSON.parse(localStorage.getItem("oem-manual-templates") || "[]");
        this.manualRecentTemplates = JSON.parse(localStorage.getItem("oem-manual-recents") || "[]");
      } catch (e) {
        this.manualTemplates = [];
        this.manualRecentTemplates = [];
      }
    },

    persistManualTemplates() {
      try {
        localStorage.setItem("oem-manual-templates", JSON.stringify(this.manualTemplates));
        localStorage.setItem("oem-manual-recents", JSON.stringify(this.manualRecentTemplates));
      } catch (e) {}
    },

    currentTemplateSnapshot(name) {
      return {
        id: templateId(),
        name,
        label: this.manual.label,
        profile: this.manual.profile,
        start: this.manual.start,
        end: this.manual.end,
        destination: this.manual.destination,
        mode: this.manual.mode,
        preset: this.manual.preset,
        favorite: false,
        updated_at: new Date().toISOString(),
      };
    },

    defaultTemplateName() {
      const selectedLabel = this.rows.find((row) => row.friendly_name === this.manual.label);
      const profile = this.manual.profile || (selectedLabel && selectedLabel.export_profile) || "Default";
      const preset = (this.datePresets.find((item) => item.key === this.manual.preset) || {}).label || "Custom";
      return `${this.manual.label || "Export"} · ${profile} · ${preset}`;
    },

    saveManualTemplate() {
      if (!this.manual.label) return window.oem && window.oem.toast("Choose a label first", "error");
      const name = prompt("Template name", this.defaultTemplateName());
      if (!name) return;
      const snapshot = this.currentTemplateSnapshot(name.trim());
      const existing = this.manualTemplates.findIndex((tpl) => tpl.name === snapshot.name);
      if (existing >= 0) {
        snapshot.id = this.manualTemplates[existing].id;
        snapshot.favorite = this.manualTemplates[existing].favorite === true;
        this.manualTemplates.splice(existing, 1, snapshot);
      } else {
        this.manualTemplates.unshift(snapshot);
      }
      this.manualTemplates = this.manualTemplates.slice(0, 30);
      this.manual.templateId = snapshot.id;
      this.persistManualTemplates();
      window.oem && window.oem.toast("Template saved", "success", snapshot.name);
    },

    applySavedTemplate(id) {
      const tpl = this.manualTemplates.find((item) => item.id === id);
      if (tpl) this.applyTemplate(tpl);
    },

    applyTemplate(tpl) {
      this.manual.label = tpl.label || this.manual.label;
      this.manual.profile = tpl.profile || "";
      this.manual.start = tpl.start || this.manual.start;
      this.manual.end = tpl.end || this.manual.end;
      this.manual.destination = tpl.destination || "";
      this.manual.mode = tpl.mode || "range";
      this.manual.preset = tpl.preset || "custom";
      this.manual.templateId = this.manualTemplates.some((item) => item.id === tpl.id) ? tpl.id : "";
      this.syncManualPickers();
      this.schedulePreview(50);
    },

    toggleFavoriteTemplate(id) {
      const tpl = this.manualTemplates.find((item) => item.id === id);
      if (!tpl) return;
      tpl.favorite = tpl.favorite !== true;
      this.persistManualTemplates();
      window.oem && window.oem.toast(tpl.favorite ? "Marked favorite" : "Favorite removed", "success", tpl.name);
    },

    rememberRecentTemplate(tpl) {
      const normalized = { ...tpl, favorite: false };
      this.manualRecentTemplates = [
        normalized,
        ...this.manualRecentTemplates.filter((item) =>
          !(item.label === normalized.label && item.profile === normalized.profile && item.start === normalized.start && item.end === normalized.end)
        ),
      ].slice(0, 8);
      this.persistManualTemplates();
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
      if (slug === "logs" && this.logLines.length === 0) this.selectLog(this.activeLog || "app");
    },

    setTheme(mode) {
      const dark = mode === "dark";
      document.documentElement.classList.toggle("dark", dark);
      try { localStorage.setItem("oem-theme", dark ? "dark" : "light"); } catch (e) {}
      if (window.oem) { window.oem.isDark = dark; }
    },

    loadOrganizations() {
      this.loading = true;
      fetchJSON("/api/organizations")
        .then((d) => {
          this.orgs = d.organizations || [];
          if (d.types) this.orgTypes = d.types;
        })
        .catch((e) => window.oem && window.oem.toast("Failed to load organizations", "error", e.message))
        .finally(() => (this.loading = false));
    },

    loadActivity() {
      this.loading = true;
      const params = new URLSearchParams({ limit: "200" });
      if (this.activityCategory) params.set("category", this.activityCategory);
      if (this.activitySeverity) params.set("severity", this.activitySeverity);
      fetchJSON(`/api/events?${params.toString()}`)
        .then((d) => {
          this.events = d.events || [];
          this.activityCategories = d.categories || [];
          this.activitySeverities = d.severities || [];
          this.activitySummary = d.summary || {};
          this.buildActivityCards();
        })
        .catch((e) => window.oem && window.oem.toast("Failed to load activity", "error", e.message))
        .finally(() => (this.loading = false));
      this.connectEventStream();
    },

    buildActivityCards() {
      const s = this.activitySummary || {};
      this.activityCards = [
        { key: "total", label: "Total Events", value: s.total ?? 0, icon: ICONS.activity, accent: "" },
        { key: "warnings", label: "Warnings", value: s.warnings ?? 0, icon: ICONS.alert, accent: (s.warnings ?? 0) > 0 ? "accent-warn" : "" },
        { key: "errors", label: "Errors", value: s.errors ?? 0, icon: ICONS.alert, accent: (s.errors ?? 0) > 0 ? "accent-danger" : "" },
        { key: "critical", label: "Critical", value: s.critical ?? 0, icon: ICONS.alert, accent: (s.critical ?? 0) > 0 ? "accent-danger" : "" },
      ];
    },

    connectEventStream() {
      if (this._ws || typeof WebSocket === "undefined") return;
      try {
        const proto = location.protocol === "https:" ? "wss:" : "ws:";
        const ws = new WebSocket(`${proto}//${location.host}/ws/events`);
        this._ws = ws;
        ws.onopen = () => (this.wsConnected = true);
        ws.onmessage = (msg) => {
          try {
            const ev = JSON.parse(msg.data);
            if (this.activityCategory && ev.category !== this.activityCategory) return;
            if (this.activitySeverity && ev.severity !== this.activitySeverity) return;
            this.events.unshift(ev);
            if (this.events.length > 300) this.events.pop();
          } catch (e) {}
        };
        ws.onclose = () => {
          this.wsConnected = false;
          this._ws = null;
          this.startActivityPolling();
        };
        ws.onerror = () => {
          this.wsConnected = false;
        };
      } catch (e) {
        this.startActivityPolling();
      }
    },

    startActivityPolling() {
      if (this._activityPoll || this.page !== "activity") return;
      this._activityPoll = setInterval(() => {
        if (this.page !== "activity") {
          clearInterval(this._activityPoll);
          this._activityPoll = null;
          return;
        }
        fetchJSON("/api/events/recent?limit=50")
          .then((d) => (this.events = d.events || this.events))
          .catch(() => {});
      }, 6000);
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

    createOrg() {
      const name = (this.newOrg.name || "").trim();
      if (!name) return window.oem && window.oem.toast("Organization name is required", "error");
      this._post("/api/organizations", this.newOrg, "Organization created", () => {
        this.newOrg = { name: "", type: "company", description: "" };
        this.loadOrganizations();
      });
    },

    deleteOrg(id) {
      if (!confirm("Delete this organization and all its credentials?")) return;
      fetch(`/api/organizations/${id}`, { method: "DELETE" })
        .then((r) => r.json())
        .then(() => { window.oem && window.oem.toast("Organization deleted", "success"); this.loadOrganizations(); })
        .catch((e) => window.oem && window.oem.toast("Delete failed", "error", e.message));
    },

    duplicateOrg(id) {
      fetch(`/api/organizations/${id}/duplicate`, { method: "POST" })
        .then((r) => r.json())
        .then(() => { window.oem && window.oem.toast("Organization duplicated", "success"); this.loadOrganizations(); })
        .catch((e) => window.oem && window.oem.toast("Duplicate failed", "error", e.message));
    },

    addCredential(orgId) {
      if (!(this.credForm.name || "").trim()) return window.oem && window.oem.toast("Credential name required", "error");
      this._post(`/api/organizations/${orgId}/credentials`, this.credForm, "Credential added", () => {
        this.credForm = { name: "Primary", environment: "production", access_key: "", secret_key: "", priority: 1 };
        this.loadOrganizations();
      });
    },

    deleteCredential(orgId, credId) {
      if (!confirm("Delete this credential?")) return;
      fetch(`/api/organizations/${orgId}/credentials/${credId}`, { method: "DELETE" })
        .then((r) => r.json())
        .then(() => { window.oem && window.oem.toast("Credential deleted", "success"); this.loadOrganizations(); })
        .catch((e) => window.oem && window.oem.toast("Delete failed", "error", e.message));
    },

    testCredential(orgId, credId) {
      window.oem && window.oem.toast("Testing connection…", "info");
      fetch(`/api/organizations/${orgId}/credentials/${credId}/test`, { method: "POST" })
        .then((r) => r.json())
        .then((d) => {
          if (d.ok) window.oem && window.oem.toast("Connected", "success", (d.latency_ms || 0) + "ms");
          else window.oem && window.oem.toast("Connection failed", "error", d.error || "Unknown error");
        })
        .catch((e) => window.oem && window.oem.toast("Test failed", "error", e.message));
    },

    importAccounts() {
      this._post("/api/organizations/import", {}, "Imported from accounts", () => this.loadOrganizations());
    },

    healthClass(health) {
      return { healthy: "badge-ok", degraded: "badge-warn", rate_limited: "badge-warn", failed: "badge-fail" }[health] || "badge-muted";
    },

    _post(url, body, okMsg, then) {
      fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
        .then((r) => r.json())
        .then((d) => {
          if (d.error) throw new Error(d.error);
          window.oem && window.oem.toast(okMsg, "success");
          then && then(d);
        })
        .catch((e) => window.oem && window.oem.toast("Action failed", "error", e.message));
    },

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
      return !!(this.manual.label && this.preview && this.preview.valid && !this.exportBusy);
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

    get favoriteTemplates() {
      return this.manualTemplates.filter((tpl) => tpl.favorite).slice(0, 8);
    },

    get recentTemplates() {
      return this.manualRecentTemplates.slice(0, 6);
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

    setTab(tab) {
      this.activeTab = tab;
    },
    sortBy(key) {
      if (this.sortKey === key) this.sortDir = this.sortDir === "asc" ? "desc" : "asc";
      else {
        this.sortKey = key;
        this.sortDir = "asc";
      }
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
// -- Tree Selector (Account → Groups hierarchy) ------------------------------

let treeSelector = () => ({
  accounts: [],
  loading: true,
  expanded: {},       // account_name → bool
  selected: {},       // group friendly_name → bool
  selectAllAccounts: {},
  icons: ICONS,

  async init() {
    try {
      const resp = await fetchJSON("/api/tree");
      this.accounts = resp.accounts || [];
    } catch (e) {
      console.warn("Tree load failed", e);
    }
    this.loading = false;
  },

  toggle(accountName) {
    this.expanded[accountName] = !this.expanded[accountName];
  },

  toggleAccount(accountName) {
    const acc = this.accounts.find(a => a.name === accountName);
    if (!acc) return;
    const select = !this.selectAllAccounts[accountName];
    this.selectAllAccounts[accountName] = select;
    for (const g of acc.groups) {
      this.selected[g.friendly_name] = select;
    }
  },

  toggleGroup(groupName) {
    this.selected[groupName] = !this.selected[groupName];
  },

  get selectedCount() {
    return Object.values(this.selected).filter(Boolean).length;
  },

  get selectedAccounts() {
    return this.accounts.filter(a =>
      this.selectAllAccounts[a.name] ||
      a.groups.some(g => this.selected[g.friendly_name])
    ).length;
  },

  get selectedLabels() {
    return Object.keys(this.selected).filter(k => this.selected[k]);
  },

  queueExport() {
    const labels = this.selectedLabels;
    if (!labels.length) return;
    fetch("/api/exports/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ labels }),
    })
      .then(r => r.json())
      .then(r => {
        if (r.error) throw new Error(r.error);
        if (window.oem) window.oem.toast("Queued", `${r.count} export(s) enqueued`, "success");
        // Clear selection
        for (const l of labels) this.selected[l] = false;
        for (const k of Object.keys(this.selectAllAccounts)) this.selectAllAccounts[k] = false;
      })
      .catch(e => {
        if (window.oem) window.oem.toast("Error", "Export failed: " + e.message, "error");
      });
  },
});


document.addEventListener("alpine:init", () => {
  window.Alpine.data("appShell", appShell);
  window.Alpine.data("dashboardPage", dashboardPage);
  window.Alpine.data("sectionPage", sectionPage);
  window.Alpine.data("treeSelector", treeSelector);
});
