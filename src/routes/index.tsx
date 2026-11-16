import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { Mic, Send, FileText, AlertTriangle, RotateCw } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { api, type BriefItem, type ItemState, type Folder } from "@/api";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Goldfish — Before you see Priya" },
      { name: "description", content: "A private brief for your next meeting, built only from the notes you let it read." },
      { property: "og:title", content: "Goldfish — Before you see Priya" },
      { property: "og:description", content: "A private brief for your next meeting, built only from the notes you let it read." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Index,
});

function Panel({ title, children, className }: { title: string; children: ReactNode; className?: string }) {
  return (
    <section aria-label={title} className={cn("rounded-2xl border bg-card p-5", className)}>
      {children}
    </section>
  );
}

function Status({ kind, label, onRetry }: { kind: "loading" | "empty" | "error"; label: string; onRetry?: () => void }) {
  if (kind === "loading")
    return (
      <div role="status" aria-live="polite" className="space-y-2">
        <span className="sr-only">{label}</span>
        {[0, 1, 2].map((i) => <div key={i} className="h-10 animate-pulse rounded-lg bg-muted" />)}
      </div>
    );
  return (
    <div role={kind === "error" ? "alert" : "status"} className="flex flex-col items-start gap-3 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
      {kind === "error" && <AlertTriangle className="h-4 w-4 text-destructive" aria-hidden />}
      <p>{label}</p>
      {onRetry && (
        <button onClick={onRetry} className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-primary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
          <RotateCw className="h-3.5 w-3.5" aria-hidden /> Try again
        </button>
      )}
    </div>
  );
}

const pill: Record<ItemState, { label: string; cls: string }> = {
  clear: { label: "Clear", cls: "bg-success/15 text-success" },
  check: { label: "Check this", cls: "bg-warning text-secondary-foreground" },
  not_found: { label: "Not found", cls: "bg-muted text-muted-foreground" },
};

function LeftColumn() {
  const q = useQuery({ queryKey: ["folders"], queryFn: api.folders });
  const [overrides, setOverrides] = useState<Record<string, boolean>>({});
  const on = (f: Folder) => overrides[f.id] ?? f.enabled;
  return (
    <Panel title="Privacy" className="bg-sidebar text-sidebar-foreground border-sidebar-border">
      <div className="mb-6 flex items-center gap-2">
        <span className="grid h-8 w-8 place-items-center rounded-full bg-sidebar-primary text-sidebar-primary-foreground font-black" aria-hidden>g</span>
        <span className="text-lg font-bold tracking-tight">Goldfish</span>
      </div>
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest opacity-70">Can read</h2>
      {q.isPending ? <Status kind="loading" label="Loading folders" /> : q.isError ? <Status kind="error" label="Couldn't load folders." onRetry={() => q.refetch()} /> : q.data.folders.length === 0 ? <Status kind="empty" label="No folders found on this device." /> : (
        <ul className="space-y-1">
          {q.data.folders.map((f) => (
            <li key={f.id} className="flex items-center justify-between rounded-lg px-2 py-2 hover:bg-sidebar-accent">
              <label htmlFor={`f-${f.id}`} className="text-sm">{f.name}</label>
              <Switch id={`f-${f.id}`} checked={on(f)} onCheckedChange={(v) => setOverrides((o) => ({ ...o, [f.id]: v }))} />
            </li>
          ))}
        </ul>
      )}
      <div className="mt-6 rounded-lg bg-sidebar-accent px-3 py-2 text-sm">
        Remembers: <strong className="text-sidebar-primary">{q.data?.memory ?? "nothing"}</strong>
      </div>
      <pre className="mt-4 whitespace-pre-wrap border-t border-dashed border-sidebar-border pt-4 font-mono text-xs leading-relaxed opacity-90">
{`RECEIPT
Left this device: ${q.data?.receipt.bytesLeftDevice ?? 0} bytes
Kept: ${q.data?.receipt.kept ?? "nothing"}`}
      </pre>
    </Panel>
  );
}

function Item({ item }: { item: BriefItem }) {
  const p = pill[item.state];
  return (
    <li className="rounded-xl border p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="font-medium">{item.text}</p>
        <div className="flex gap-1.5">
          {item.stale && <span className="rounded-full bg-destructive px-2 py-0.5 text-xs font-semibold text-destructive-foreground">{item.ageLabel ?? "Stale"}</span>}
          <span className={cn("rounded-full px-2 py-0.5 text-xs font-semibold", p.cls)}>{p.label}</span>
        </div>
      </div>
      {item.sources.length > 0 ? (
        <ul className="mt-3 flex flex-wrap gap-2" aria-label="Sources">
          {item.sources.map((s) => (
            <li key={s.file + s.date} className="group relative">
              <button className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1 font-mono text-xs text-muted-foreground hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" aria-describedby={`q-${item.id}-${s.date}`}>
                <FileText className="h-3 w-3" aria-hidden /> {s.date} · {s.file}
              </button>
              <span role="tooltip" id={`q-${item.id}-${s.date}`} className="pointer-events-none absolute bottom-full left-0 z-10 mb-2 w-64 rounded-lg bg-popover p-3 text-xs text-popover-foreground opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                “{s.quote}”
              </span>
            </li>
          ))}
        </ul>
      ) : <p className="mt-2 text-xs text-muted-foreground">Nothing in the folders you allowed.</p>}
    </li>
  );
}

function Centre() {
  const q = useQuery({ queryKey: ["brief", "e3"], queryFn: () => api.brief("e3") });
  const [text, setText] = useState("");
  const ask = useMutation({ mutationFn: api.ask });
  return (
    <Panel title="Brief" className="flex flex-col">
      <h1 className="text-2xl font-bold tracking-tight">
        Before you see {q.data?.person ?? "Priya"} <span className="text-primary">· {q.data?.time ?? "14:00"}</span>
      </h1>
      <div className="mt-5 flex-1">
        {q.isPending ? <Status kind="loading" label="Preparing brief" /> : q.isError ? <Status kind="error" label="Couldn't prepare this brief." onRetry={() => q.refetch()} /> : q.data.items.length === 0 ? <Status kind="empty" label="Nothing to prepare — no notes mention this person." /> : (
          <ul className="space-y-3">{q.data.items.map((i) => <Item key={i.id} item={i} />)}</ul>
        )}
      </div>
      {ask.data && <p role="status" className="mt-4 rounded-lg bg-muted p-3 text-sm">{ask.data.answer}</p>}
      {ask.isError && <p role="alert" className="mt-4 text-sm text-destructive">Couldn't answer that. Try again.</p>}
      <form className="mt-5 flex items-center gap-2 rounded-full border-2 border-foreground bg-background p-1.5" onSubmit={(e) => { e.preventDefault(); if (text.trim()) ask.mutate(text.trim()); }}>
        <button type="button" aria-label="Ask by voice" className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-secondary text-secondary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <Mic className="h-4 w-4" aria-hidden />
        </button>
        <label htmlFor="ask" className="sr-only">Ask about your notes</label>
        <input id="ask" value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask about your notes" className="min-w-0 flex-1 bg-transparent px-2 text-sm outline-none placeholder:text-muted-foreground" />
        <button type="submit" disabled={ask.isPending} aria-label="Send question" className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
          <Send className="h-4 w-4" aria-hidden />
        </button>
      </form>
    </Panel>
  );
}

const HOURS = Array.from({ length: 10 }, (_, i) => 8 + i);
const ROW = 56;
const toMin = (t: string) => { const [h, m] = t.split(":").map(Number); return h * 60 + m; };

function Right() {
  const q = useQuery({ queryKey: ["calendar", "2026-11-16"], queryFn: () => api.calendar("2026-11-16") });
  return (
    <Panel title="Today">
      <h2 className="mb-4 text-sm font-semibold">Today · Mon 16 Nov</h2>
      {q.isPending ? <Status kind="loading" label="Loading calendar" /> : q.isError ? <Status kind="error" label="Couldn't load your calendar." onRetry={() => q.refetch()} /> : q.data.events.length === 0 ? <Status kind="empty" label="Nothing on today." /> : (
        <div className="relative" style={{ height: HOURS.length * ROW }}>
          {HOURS.map((h, i) => (
            <div key={h} className="absolute inset-x-0 flex border-t text-[11px] text-muted-foreground" style={{ top: i * ROW }}>
              <span className="w-10 -translate-y-2 bg-card pr-1 font-mono">{String(h).padStart(2, "0")}:00</span>
            </div>
          ))}
          <ol>
            {q.data.events.map((e) => {
              const top = ((toMin(e.start) - 8 * 60) / 60) * ROW;
              const height = Math.max(((toMin(e.end) - toMin(e.start)) / 60) * ROW - 4, 24);
              return (
                <li key={e.id} tabIndex={0} aria-label={`${e.start}–${e.end} ${e.title}${e.briefReady ? ", brief ready" : ""}`}
                  className={cn("absolute left-12 right-0 overflow-hidden rounded-lg px-2 py-1 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    e.briefReady ? "bg-secondary font-semibold text-secondary-foreground border-l-4 border-primary" : "bg-muted text-muted-foreground")}
                  style={{ top, height }}>
                  {e.start} {e.title}{e.briefReady && " · brief ready"}
                </li>
              );
            })}
          </ol>
        </div>
      )}
    </Panel>
  );
}

function Index() {
  return (
    <main className="mx-auto grid min-h-screen max-w-7xl gap-4 p-4 lg:grid-cols-[260px_1fr_280px]">
      <LeftColumn />
      <Centre />
      <Right />
    </main>
  );
}
