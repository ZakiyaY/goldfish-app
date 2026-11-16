import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState, type ReactNode } from "react";
import { Mic, Send, FileText, AlertTriangle, RotateCw } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import type { BriefItem, Evidence, ItemState, Meeting } from "@/api/types";
import { FIXTURE_DATE } from "@/api/fixtures";
import { SessionProvider, useSession, FOLDER_IDS } from "@/state/session";
import { useMeetings } from "@/hooks/useMeetings";
import { useBrief } from "@/hooks/useBrief";
import { useAsk } from "@/hooks/useAsk";
import { useReceipt } from "@/hooks/useReceipt";
import { copy } from "@/copy";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: copy.meta.title },
      { name: "description", content: copy.meta.description },
      { property: "og:title", content: copy.meta.title },
      { property: "og:description", content: copy.meta.description },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Index,
});

const DAY_MS = 86_400_000;
const weeksBetween = (from: string, to: string) => Math.floor((Date.parse(to) - Date.parse(from)) / DAY_MS / 7);
const dayLabel = (date: string) =>
  new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" }).format(new Date(date));

function Panel({ title, children, className }: { title: string; children: ReactNode; className?: string }) {
  return <section aria-label={title} className={cn("rounded-2xl border bg-card p-5", className)}>{children}</section>;
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
          <RotateCw className="h-3.5 w-3.5" aria-hidden /> {copy.retry}
        </button>
      )}
    </div>
  );
}

const pillCls: Record<ItemState, string> = {
  clear: "bg-success/15 text-success",
  check: "bg-warning text-secondary-foreground",
  not_found: "bg-muted text-muted-foreground",
};

function LeftColumn() {
  const { enabledFolders, setFolder } = useSession();
  const r = useReceipt();
  const retained = r.data?.itemsRetained ?? 0;
  const kept = retained === 0 ? copy.privacy.rememberedNothing : copy.privacy.rememberedItems(retained);
  return (
    <Panel title={copy.privacy.panel} className="bg-sidebar text-sidebar-foreground border-sidebar-border">
      <div className="mb-6 flex items-center gap-2">
        <span className="grid h-8 w-8 place-items-center rounded-full bg-sidebar-primary text-sidebar-primary-foreground font-black" aria-hidden>{copy.appInitial}</span>
        <span className="text-lg font-bold tracking-tight">{copy.appName}</span>
      </div>
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest opacity-70">{copy.privacy.canRead}</h2>
      <ul className="space-y-1">
        {FOLDER_IDS.map((id) => (
          <li key={id} className="flex items-center justify-between rounded-lg px-2 py-2 hover:bg-sidebar-accent">
            <label htmlFor={`f-${id}`} className="text-sm">{copy.folders[id]}</label>
            <Switch id={`f-${id}`} checked={enabledFolders[id]} onCheckedChange={(v) => setFolder(id, v)} />
          </li>
        ))}
      </ul>
      <div className="mt-6 rounded-lg bg-sidebar-accent px-3 py-2 text-sm">
        {copy.privacy.remembers} <strong className="text-sidebar-primary">{kept}</strong>
      </div>
      {r.isError ? (
        <div className="mt-4"><Status kind="error" label={copy.privacy.receiptError} onRetry={() => r.refetch()} /></div>
      ) : (
        <pre aria-busy={r.isPending} className="mt-4 whitespace-pre-wrap border-t border-dashed border-sidebar-border pt-4 font-mono text-xs leading-relaxed opacity-90">
          {copy.privacy.receipt(r.data?.bytesSentOffDevice ?? 0, kept, r.data?.filesRead ?? 0)}
        </pre>
      )}
    </Panel>
  );
}

function Chips({ ownerId, evidence }: { ownerId: string; evidence: Evidence[] }) {
  return (
    <ul className="mt-3 flex flex-wrap gap-2" aria-label={copy.brief.sources}>
      {evidence.map((s) => {
        const tip = `q-${ownerId}-${s.docId}`.replace(/[^\w-]/g, "_");
        return (
          <li key={s.docId} className="group relative">
            <button className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1 font-mono text-xs text-muted-foreground hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" aria-describedby={tip}>
              <FileText className="h-3 w-3" aria-hidden /> {s.docDate} · {s.path}
            </button>
            <span role="tooltip" id={tip} className="pointer-events-none absolute bottom-full left-0 z-10 mb-2 w-64 rounded-lg bg-popover p-3 text-xs text-popover-foreground opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
              “{s.quote}”
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function Item({ item, today }: { item: BriefItem; today: string }) {
  const stale = item.flags.includes("stale");
  const newest = item.evidence.map((e) => e.docDate).sort().at(-1);
  const staleLabel = newest ? copy.brief.weeksOld(weeksBetween(newest, today)) : copy.brief.stale;
  return (
    <li className="rounded-xl border p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="font-medium">{item.text}</p>
        <div className="flex gap-1.5">
          {stale && <span className="rounded-full bg-destructive px-2 py-0.5 text-xs font-semibold text-destructive-foreground">{staleLabel}</span>}
          <span className={cn("rounded-full px-2 py-0.5 text-xs font-semibold", pillCls[item.state])}>{copy.pills[item.state]}</span>
        </div>
      </div>
      {item.evidence.length > 0 ? <Chips ownerId={item.id} evidence={item.evidence} /> : <p className="mt-2 text-xs text-muted-foreground">{copy.brief.noSources}</p>}
    </li>
  );
}

function Centre({ meeting }: { meeting: Meeting | null }) {
  const { date } = useSession();
  const q = useBrief(meeting?.id ?? null);
  const [text, setText] = useState("");
  const ask = useAsk();
  const name = (q.data?.subject || meeting?.attendees[0] || "").split(" ")[0];
  return (
    <Panel title={copy.brief.panel} className="flex flex-col">
      {meeting && (
        <h1 className="text-2xl font-bold tracking-tight">
          {copy.brief.heading(name ?? "")} <span className="text-primary">· {meeting.start}</span>
        </h1>
      )}
      <div className="mt-5 flex-1">
        {!meeting ? <Status kind="empty" label={copy.brief.noMeeting} />
          : q.isPending ? <Status kind="loading" label={copy.brief.loading} />
          : q.isError ? <Status kind="error" label={copy.brief.error} onRetry={() => q.refetch()} />
          : q.data.items.length === 0 ? <Status kind="empty" label={copy.brief.empty} />
          : <ul className="space-y-3">{q.data.items.map((i) => <Item key={i.id} item={i} today={date} />)}</ul>}
      </div>
      {ask.data && (
        <div role="status" className="mt-4 rounded-lg bg-muted p-3 text-sm">
          <div className="flex items-start justify-between gap-2">
            <p>{ask.data.answer ?? ask.data.reason}</p>
            <span className={cn("shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold", pillCls[ask.data.state])}>{copy.pills[ask.data.state]}</span>
          </div>
          {ask.data.evidence.length > 0 && <Chips ownerId="ask" evidence={ask.data.evidence} />}
        </div>
      )}
      {ask.isError && <p role="alert" className="mt-4 text-sm text-destructive">{copy.ask.error}</p>}
      <form className="mt-5 flex items-center gap-2 rounded-full border-2 border-foreground bg-background p-1.5" onSubmit={(e) => { e.preventDefault(); if (text.trim()) ask.mutate(text.trim()); }}>
        <button type="button" aria-label={copy.ask.voice} className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-secondary text-secondary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <Mic className="h-4 w-4" aria-hidden />
        </button>
        <label htmlFor="ask" className="sr-only">{copy.ask.placeholder}</label>
        <input id="ask" value={text} onChange={(e) => setText(e.target.value)} placeholder={copy.ask.placeholder} className="min-w-0 flex-1 bg-transparent px-2 text-sm outline-none placeholder:text-muted-foreground" />
        <button type="submit" disabled={ask.isPending} aria-label={copy.ask.send} className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
          <Send className="h-4 w-4" aria-hidden />
        </button>
      </form>
    </Panel>
  );
}

const HOURS = Array.from({ length: 10 }, (_, i) => 8 + i);
const ROW = 56;
const toMin = (t: string) => { const [h, m] = t.split(":").map(Number); return (h ?? 0) * 60 + (m ?? 0); };

function Right({ meetings, isPending, isError, refetch, selectedId, onSelect }: {
  meetings: Meeting[] | undefined; isPending: boolean; isError: boolean; refetch: () => void; selectedId: string | null; onSelect: (id: string) => void;
}) {
  const { date } = useSession();
  return (
    <Panel title={copy.calendar.panel}>
      <h2 className="mb-4 text-sm font-semibold">{copy.calendar.heading(dayLabel(date))}</h2>
      {isPending ? <Status kind="loading" label={copy.calendar.loading} /> : isError ? <Status kind="error" label={copy.calendar.error} onRetry={refetch} /> : !meetings?.length ? <Status kind="empty" label={copy.calendar.empty} /> : (
        <div className="relative" style={{ height: HOURS.length * ROW }}>
          {HOURS.map((h, i) => (
            <div key={h} className="absolute inset-x-0 flex border-t text-[11px] text-muted-foreground" style={{ top: i * ROW }}>
              <span className="w-10 -translate-y-2 bg-card pr-1 font-mono">{String(h).padStart(2, "0")}:00</span>
            </div>
          ))}
          <ol>
            {meetings.map((e) => {
              const top = ((toMin(e.start) - 8 * 60) / 60) * ROW;
              const height = Math.max(((toMin(e.end) - toMin(e.start)) / 60) * ROW - 4, 24);
              const selected = e.id === selectedId;
              return (
                <li key={e.id} className="absolute left-12 right-0" style={{ top, height }}>
                  <button type="button" disabled={!e.briefReady} aria-pressed={e.briefReady ? selected : undefined} onClick={() => onSelect(e.id)}
                    aria-label={`${e.start}–${e.end} ${e.title}${e.briefReady ? `, ${copy.calendar.briefReady}` : ""}`}
                    className={cn("h-full w-full overflow-hidden rounded-lg px-2 py-1 text-left text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      selected ? "bg-secondary font-semibold text-secondary-foreground border-l-4 border-primary"
                        : e.briefReady ? "bg-secondary/50 text-secondary-foreground" : "bg-muted text-muted-foreground")}>
                    {e.start} {e.title}{e.briefReady && ` · ${copy.calendar.briefReady}`}
                  </button>
                </li>
              );
            })}
          </ol>
        </div>
      )}
    </Panel>
  );
}

// Default selection: next brief-ready meeting that hasn't ended yet, else the first brief-ready one.
function pickDefault(meetings: Meeting[], nowMin: number | null) {
  const ready = meetings.filter((m) => m.briefReady);
  return (nowMin !== null ? ready.find((m) => toMin(m.end) > nowMin) : undefined) ?? ready[0] ?? null;
}

function Screen() {
  const { date, selectedMeetingId, setSelectedMeetingId } = useSession();
  const m = useMeetings();
  const [nowMin, setNowMin] = useState<number | null>(null);
  useEffect(() => { const d = new Date(); if (d.toISOString().slice(0, 10) === date) setNowMin(d.getHours() * 60 + d.getMinutes()); }, [date]);
  const list = m.data ?? [];
  const meeting = list.find((x) => x.id === selectedMeetingId) ?? pickDefault(list, nowMin);
  return (
    <main className="mx-auto grid min-h-screen max-w-7xl gap-4 p-4 lg:grid-cols-[260px_1fr_280px]">
      <LeftColumn />
      <Centre meeting={meeting} />
      <Right meetings={m.data} isPending={m.isPending} isError={m.isError} refetch={() => m.refetch()} selectedId={meeting?.id ?? null} onSelect={setSelectedMeetingId} />
    </main>
  );
}

function Index() {
  return <SessionProvider date={FIXTURE_DATE}><Screen /></SessionProvider>;
}
