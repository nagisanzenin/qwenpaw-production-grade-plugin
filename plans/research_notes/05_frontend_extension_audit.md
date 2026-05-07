# QwenPaw Frontend Plugin Surface — Feasibility Audit

> Verifies whether the production-grade plugin's UI primitives (AskUserQuestion, task lists, gate ceremonies) can be replicated **without modifying QwenPaw source**.

## Bottom line

| Target | Verdict | Mechanism |
|---|---|---|
| `AskUserQuestion` | ✅ feasible | `registerToolRender` + POST to `/console/chat` |
| Task dashboard (inline) | ✅ feasible | `registerToolRender` for streaming task tool calls |
| Task dashboard (persistent) | ⚠️ caveats | `registerRoutes` sidebar + backend SSE endpoint we ship |
| Gate ceremonies | ✅ feasible | `registerToolRender` mimicking `ApprovalCard.tsx` styling |

**All three production-grade UI primitives can be replicated.** No QwenPaw source changes required.

---

## 1. Plugin loading mechanics

Plugins are loaded at app startup by `loadAllPlugins()` (`console/src/plugins/usePluginLoader.ts:71-116`). Flow:

1. `GET /api/plugins` → list of installed plugins
2. Filter to `frontend_entry` non-null
3. For each: download JS bundle, wrap in same-origin Blob URL, dynamic-import
4. Plugin code runs synchronously during import → must register itself before resolving
5. App routes mount only after all plugins finish (`App.tsx:163-165` → `if (pluginsLoading) return null;`)

```ts
// usePluginLoader.ts:39-58
const jsText = await response.text();
const blobUrl = URL.createObjectURL(
  new Blob([jsText], { type: "application/javascript" }),
);
try {
  await import(/* @vite-ignore */ blobUrl);
} finally {
  URL.revokeObjectURL(blobUrl);
}
```

---

## 2. `window.QwenPaw` namespace — the public API

Source: `console/src/plugins/hostExternals.ts:124-146`.

```ts
export interface WindowNamespace {
  host: HostExternals;                    // React, antd, antdIcons, getApiUrl, getApiToken, …
  modules: Record<string, Record<string, unknown>>;   // ⚠️ explicitly unstable
  registerRoutes?: (pluginId, routes[]) => void;
  registerToolRender?: (pluginId, renderers) => void;
}
```

`HostExternals` (lines 24-32) — full surface:

```ts
{
  React: typeof React;
  ReactDOM: typeof ReactDOM;        // source-only (not in docs)
  antd: typeof antd;
  antdIcons: typeof antdIcons;      // source-only
  apiBaseUrl: string;               // source-only
  getApiUrl: typeof getApiUrl;
  getApiToken: typeof getApiToken;
}
```

`PluginRouteDeclaration`:
```ts
{ path: string;                  // e.g. "/plugin/my-plugin/dashboard"
  component: React.ComponentType;
  label: string;
  icon?: string;
  priority?: number; }            // lower = earlier
```

**No working frontend plugin example ships in QwenPaw repo** — only `plugins/tool/gpt-image2/` (backend-only). The 5 frontend examples in `plugins.en.md:658-885` are the canonical templates.

---

## 3. How `registerToolRender` actually wires through

Renderers are merged into a flat `Record<string, React.FC<any>>` (`hostExternals.ts:81-86`) and passed to `@agentscope-ai/chat`'s `AgentScopeRuntimeWebUI` as `customToolRenderConfig`:

```tsx
// console/src/pages/Chat/index.tsx:1170-1171
customToolRenderConfig:
  Object.keys(toolRenderConfig).length > 0 ? toolRenderConfig : undefined,
```

→ **renderers run inline inside the chat transcript**, replacing the default tool-call card for any matching tool name. They cannot render in a sidebar (use `registerRoutes` for that) or as a persistent panel.

Renderer prop shape: docs show `{ result }` where `result` is parsed `ToolResponse.content` (`plugins.en.md:779`). **This is example-only** — not in any source-controlled type. Defensive destructuring recommended.

Tool-call data flow:
- Tool emits `agentscope.tool.ToolResponse` (typed content blocks: `TextBlock`, `ImageBlock`, etc.)
- Streamed via SSE through `POST /console/chat` (`Chat/index.tsx:955-960`)
- Parsed in `responseParser` (lines 1115-1124)
- `AgentScopeRuntimeWebUI` knits chunks → routes by tool name → custom renderer

---

## 4. Sending structured response back from a custom renderer

Three paths:

### Path A — Synthetic textarea injection (brittle)

`setTextareaValue()` (`console/src/pages/Chat/utils.ts:194-207`) is the host's own technique. Plugin can locate the textarea via DOM (`document.querySelector('[class*="sender"] textarea')`) and dispatch a synthetic submit. Works but fragile.

### Path B — Direct POST to `/console/chat` (RECOMMENDED)

`getApiUrl` and `getApiToken` host helpers exist for this. Body shape (`Chat/index.tsx:931-938`):

```ts
const requestBody = {
  input: rewrittenInput,                 // OpenAI-style messages
  session_id: window.currentSessionId,
  user_id: window.currentUserId,
  channel: window.currentChannel,
  stream: true,
  ...biz_params,
};
```

A plugin can POST `{role: "user", content: [{type: "text", text: "<chosen option>"}]}`. Caveat: bypasses `AgentScopeRuntimeWebUI`'s optimistic UI — the choice may not appear in chat until SSE chunk lands. Mitigation: render the choice locally before POSTing.

### Path C — `/approval/{action}` endpoint (too narrow)

`commands.ts:24-48` exposes typed approve/deny only. Useful as a fallback for binary gates but **does not support 2-4 labeled options with descriptions**, which production-grade requires.

**Verdict:** Use Path B for AskUserQuestion + gate ceremonies. Use Path C as a secondary enforcement layer if needed.

---

## 5. Implementation sketches

### 5.1 AskUserQuestion replacement

```tsx
// frontend/index.tsx (compiled to dist/index.js)
const { React, antd, getApiUrl, getApiToken } = (window as any).QwenPaw.host;
const { Button, Card, Space, Typography } = antd;

function AskUserQuestionCard({ result }: any) {
  const data = typeof result === "string" ? JSON.parse(result) : result;
  const send = async (optionLabel: string) => {
    await fetch(getApiUrl("/console/chat"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getApiToken()}`,
      },
      body: JSON.stringify({
        input: [{ role: "user", content: [{ type: "text", text: optionLabel }] }],
        session_id: (window as any).currentSessionId,
        stream: true,
      }),
    });
  };
  return (
    <Card title={data.header} style={{ marginTop: 12 }}>
      <Typography.Paragraph>{data.question}</Typography.Paragraph>
      <Space direction="vertical" style={{ width: "100%" }}>
        {data.options.map((o: any) => (
          <Button key={o.label} block onClick={() => send(o.label)}>
            <strong>{o.label}</strong> — {o.description}
          </Button>
        ))}
      </Space>
    </Card>
  );
}

(window as any).QwenPaw.registerToolRender?.("production-grade", {
  mcp__pg__ask_user_question: AskUserQuestionCard,
});
```

### 5.2 Gate ceremony (mimic `ApprovalCard.tsx`)

Same pattern. Replace body with antd `<Table dataSource={data.metrics}/>`, 3-4 decision `<Button>`s, and an optional `<Collapse>` for the BRD/architecture diff. Reference styling: `console/src/components/ApprovalCard/ApprovalCard.tsx:106-235`.

### 5.3 Task dashboard (sidebar + SSE)

```tsx
// frontend route
const { React, antd, getApiUrl } = (window as any).QwenPaw.host;
function TaskDashboard() {
  const [tasks, setTasks] = React.useState([]);
  React.useEffect(() => {
    const es = new EventSource(getApiUrl("/plugins/pg/tasks/stream"));
    es.onmessage = (e) => setTasks(JSON.parse(e.data));
    return () => es.close();
  }, []);
  return (
    <antd.List
      dataSource={tasks}
      renderItem={(t: any) => (
        <antd.List.Item>
          <antd.Tag color={stateColor(t.state)}>{t.state}</antd.Tag>
          {t.name}
        </antd.List.Item>
      )}
    />
  );
}
(window as any).QwenPaw.registerRoutes?.("production-grade", [{
  path: "/plugin/pg/tasks",
  component: TaskDashboard,
  label: "PG Tasks",
  icon: "📋",
  priority: 5,
}]);
```

The SSE endpoint `/plugins/pg/tasks/stream` is something **the backend plugin must expose**. Pattern reference: `console/src/api/modules/plan.ts:52-115` (`/plan/stream`).

---

## 6. Stability tier per API

| API | Tier | Source |
|---|---|---|
| `host.{React, antd, getApiUrl, getApiToken}` | **Documented** | plugins.en.md:244-252 |
| `host.{ReactDOM, antdIcons, apiBaseUrl}` | Source-only | hostExternals.ts:24-32 |
| `registerRoutes(id, routes[])` | Documented (example) | plugins.en.md:177, 677-685 |
| `registerToolRender(id, renderers)` | Documented (example) | plugins.en.md:809-811 |
| `window.QwenPaw.modules` | **Explicitly unstable** ⚠️ | plugins.en.md:258-260 |
| Renderer `{result}` prop shape | Example-only | plugins.en.md:779 |
| `POST /console/chat` body shape | Source-only | Chat/index.tsx:931-938 |
| `window.currentSessionId / currentUserId / currentChannel` | Source-only | Chat/index.tsx:75-81 |
| `setTextareaValue` DOM trick | Source-only | utils.ts:194-207 |
| `/approval/{action}` endpoint | **Documented** | commands.en.md:639-663 |
| `/plan/stream` SSE | Source-only | plan.ts:52-115 |

The doc carves out one explicitly unstable region (`modules`); everything else is officially supported. The *usable* surface for production-grade replication leans on multiple source-only details — low risk if QwenPaw minor-version is pinned, higher risk across major bumps. Tight version pin in `plugin.json.min_version` and CI tests against the pinned version handle this.

---

## 7. Critical reference files

- `console/src/plugins/hostExternals.ts` — full plugin host API
- `console/src/plugins/PluginContext.tsx` — React subscription
- `console/src/plugins/usePluginLoader.ts` — bundle loader
- `console/src/pages/Chat/index.tsx` lines 500, 889-963, 1170-1171 — `customToolRenderConfig` consumption + `/console/chat` POST shape
- `console/src/components/ApprovalCard/ApprovalCard.tsx` — gate ceremony styling template
- `console/src/components/PlanPanel/index.tsx` — task dashboard template
- `console/src/api/modules/plan.ts` — SSE pattern for live updates
- `console/src/api/modules/commands.ts` — `/approval/{action}` reference
- `website/public/docs/plugins.en.md` lines 138-260, 750-816 — official frontend plugin docs

---

## 8. Net implication for 100% retention port

Production-grade's three UI-heavy primitives port cleanly:

1. **AskUserQuestion ceremonies** (Visual Identity §3, Gate ceremonies) → custom MCP tool + tool renderer + POST.
2. **Gate ceremonies** (BRD, Architecture, Production Readiness) → same pattern, richer body.
3. **Task progress** (TaskCreate/Update/List) → backend SSE + sidebar route.

These were the largest UX-degradation risks in the v1 plan. They are now **non-issues**. The frontend plugin route restores Claude Code's interactive UI quality on QwenPaw.

The cost: the plugin must ship a JS bundle (`entry.frontend`) alongside the Python backend (`entry.backend`). Build pipeline: TypeScript → Vite/esbuild bundle → ship `dist/index.js`. Examples in `plugins.en.md:658-885`.
