import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState, type ReactNode } from "react";
import { Folder, Lock, Mic, MicOff, RefreshCw, Send, FileText, AlertTriangle, RotateCw } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import type { BriefItem, CalendarStatus, Evidence, Folder as FolderInfo, ItemState, Meeting } from "@/api/types";
import { SessionProvider, useSession } from "@/state/session";
import { useMeetings } from "@/hooks/useMeetings";
import { useBrief } from "@/hooks/useBrief";
import { useAsk } from "@/hooks/useAsk";
import { useReceipt } from "@/hooks/useReceipt";
import { useCalendarStatus, useRefreshCalendar } from "@/hooks/useCalendarStatus";
import { useOpen } from "@/hooks/useOpen";
import { Toaster } from "@/components/ui/sonner";
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

const timeLabel = (iso: string | null) => iso ? new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date(iso)) : "";
const folderDomId = (id: string) => encodeURIComponent(id);

// Plain-language message that replaces the calendar and chips, or null when the calendar is usable.
function useCalendarMessage(): string | null {
  const { enabledFolders, folders, foldersLoading, foldersError } = useSession();
  const st = useCalendarStatus();
  if (foldersError) return copy.brief.error;
  if (foldersLoading) return copy.calendar.loading;
  const calendarFolder = folders.find((folder) => folder.id.toLowerCase() === "calendar");
  if (!calendarFolder) return copy.calendarStatus.states.file_missing;
  if (!(enabledFolders[calendarFolder.id] ?? calendarFolder.defaultEnabled)) return copy.calendarStatus.states.off;
  if (st.isError) return copy.calendarStatus.states.error;
  const state = st.data?.state;
  return state && state !== "connected" ? copy.calendarStatus.states[state] : null;
}

function FolderButton({ folder, on }: { folder: FolderInfo; on: boolean }) {
  const id = folder.id;
  const { openFolder } = useOpen();
  const tip = `ft-${folderDomId(id)}`;
  return (
    <span className="group relative">
      <button type="button" aria-label={copy.open.folder(folder.label)} aria-disabled={!on} aria-describedby={on ? undefined : tip}
        onClick={() => { if (on) void openFolder(id); }}
        className={cn("grid h-7 w-7 place-items-center rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring", on ? "hover:bg-sidebar-primary hover:text-sidebar-primary-foreground" : "cursor-not-allowed opacity-40")}>
        <Folder className="h-3.5 w-3.5" aria-hidden />
      </button>
      {!on && <span id={tip} role="tooltip" className="invisible absolute right-0 top-full z-20 mt-1 w-40 rounded-md bg-popover p-2 text-xs text-popover-foreground shadow-lg group-hover:visible group-focus-within:visible">{copy.open.folderOff}</span>}
    </span>
  );
}

function CalendarRow() {
  const st = useCalendarStatus();
  const refresh = useRefreshCalendar();
  const d: CalendarStatus | undefined = st.data;
  return (
    <div className="mt-3 flex items-center justify-between gap-2 rounded-lg border border-sidebar-border px-3 py-2 text-xs" aria-live="polite">
      <div className="min-w-0">
        <p className="font-semibold">{copy.calendarStatus.row}</p>
        {d && d.state === "connected" ? (
          <><p className="truncate opacity-80">{d.sourceLabel}</p><p className="opacity-70">{copy.calendarStatus.lastRead(timeLabel(d.lastReadAt))}</p></>
        ) : <p className="opacity-80">{d?.detail ?? ""}</p>}
      </div>
      <button type="button" aria-label={copy.calendarStatus.refresh} aria-busy={refresh.isPending} disabled={refresh.isPending} onClick={() => refresh.mutate()}
        className="grid h-7 w-7 shrink-0 place-items-center rounded-md hover:bg-sidebar-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring">
        <RefreshCw className={cn("h-3.5 w-3.5", refresh.isPending && "animate-spin")} aria-hidden />
      </button>
    </div>
  );
}

const pillCls: Record<ItemState, string> = {
  clear: "bg-success/15 text-success",
  check: "bg-warning text-secondary-foreground",
  not_found: "bg-muted text-muted-foreground",
};

function LeftColumn() {
  const { enabledFolders, folders, foldersLoading, foldersError, refetchFolders, setFolder, req, wipe } = useSession();
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
        {foldersLoading ? <li role="status" className="px-2 py-2 text-sm">{copy.calendar.loading}</li>
          : foldersError ? <li><Status kind="error" label={copy.brief.error} onRetry={refetchFolders} /></li>
          : folders.map((folder) => {
          const controlId = `f-${folderDomId(folder.id)}`;
          const sensitiveId = `sensitive-${folderDomId(folder.id)}`;
          const enabled = enabledFolders[folder.id] ?? folder.defaultEnabled;
          return (
          <li key={folder.id} className="rounded-lg px-2 py-2 hover:bg-sidebar-accent">
            <div className="flex items-center justify-between">
              <label htmlFor={controlId} className="flex items-center gap-1.5 text-sm">
                {folder.sensitive && <Lock className="h-3.5 w-3.5" aria-hidden />}{folder.label}
              </label>
              <span className="flex items-center gap-1"><FolderButton folder={folder} on={enabled} /><Switch id={controlId} checked={enabled} onCheckedChange={(v) => setFolder(folder.id, v)} aria-describedby={folder.sensitive ? sensitiveId : undefined} /></span>
            </div>
            {folder.sensitive && <p id={sensitiveId} className="mt-0.5 text-xs opacity-70">{copy.privacy.hrNote}</p>}
          </li>
          );
        })}
      </ul>
      <CalendarRow />
      <p aria-live="polite" className="mt-4 text-sm font-medium">{copy.privacy.canReadCount(req.folders.length)}</p>
      <div className="mt-3 rounded-lg bg-sidebar-accent px-3 py-2 text-sm">
        {copy.privacy.remembers} <strong className="text-sidebar-primary">{kept}</strong>
      </div>
      <button type="button" onClick={() => void wipe()} className="mt-4 w-full rounded-md border border-sidebar-primary px-3 py-2 text-sm font-semibold text-sidebar-primary hover:bg-sidebar-primary hover:text-sidebar-primary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring focus-visible:ring-offset-2 focus-visible:ring-offset-sidebar">
        {copy.privacy.wipe}
      </button>
    </Panel>
  );
}

function Chip({ ownerId, s }: { ownerId: string; s: Evidence }) {
  const { folders, excludedDocs, setExcludedDocs } = useSession();
  const { openSource } = useOpen();
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);
  const tip = `q-${ownerId}-${s.docId}`.replace(/[^\w-]/g, "_");
  const btn = "rounded-md px-2 py-1 font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2";
  return (
    <li className="relative" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)} onBlur={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setOpen(false); }}
>
      <button type="button" aria-expanded={open} aria-controls={tip} onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1 font-mono text-xs text-muted-foreground hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
        <FileText className="h-3 w-3" aria-hidden /> {s.docDate} · {s.path}
      </button>
      <div id={tip} role="dialog" aria-label={s.path} hidden={!open} className="absolute bottom-full left-0 z-20 w-72 pb-2">
        <div className="rounded-lg border bg-popover p-3 text-xs text-popover-foreground shadow-lg">
          <blockquote className="border-l-4 border-primary pl-2 italic">“{s.quote}”</blockquote>
          <p className="mt-2 text-muted-foreground">{copy.source.folder}: {folders.find((folder) => folder.id === s.folder)?.label ?? s.folder}</p>
          <p className="text-muted-foreground">{copy.source.foundBecause(s.matchedBy)}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <button type="button" onClick={() => void openSource(s.docId, "open")} className={cn(btn, "bg-primary text-primary-foreground")}>{copy.open.note}</button>
            <button type="button" onClick={() => void openSource(s.docId, "reveal")} className={cn(btn, "border border-primary text-primary")}>{copy.open.reveal}</button>
            <button type="button" onClick={() => setExcludedDocs([...excludedDocs, s.docId])} className={cn(btn, "bg-muted text-foreground")}>{copy.source.leaveOut}</button>
          </div>
        </div>
      </div>
    </li>
  );
}

function Chips({ ownerId, evidence }: { ownerId: string; evidence: Evidence[] }) {
  return (
    <ul className="mt-3 flex flex-wrap gap-2" aria-label={copy.brief.sources}>
      {evidence.map((s) => <Chip key={s.docId} ownerId={ownerId} s={s} />)}
    </ul>
  );
}

function Pill({ state }: { state: ItemState }) {
  return <span className={cn("shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold", pillCls[state])}>{copy.pills[state]}</span>;
}

function Item({ item, today, phase }: { item: BriefItem; today: string; phase: "enter" | "leave" | "idle" }) {
  const stale = item.flags.includes("stale");
  const sensitive = item.flags.includes("sensitive");
  const newest = item.evidence.map((e) => e.docDate).sort().at(-1);
  const staleLabel = newest ? copy.brief.weeksOld(weeksBetween(newest, today)) : copy.brief.stale;
  return (
    <li aria-hidden={phase === "leave" || undefined} className={cn("rounded-xl border p-4", phase === "enter" && "gf-enter", phase === "leave" && "gf-leave")}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-medium">{item.text}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">{item.reason}</p>
        </div>
        <div className="flex gap-1.5">
          {sensitive && <span className="inline-flex items-center gap-1 rounded-full border border-foreground px-2 py-0.5 text-xs font-semibold"><Lock className="h-3 w-3" aria-hidden />{copy.brief.sensitive}</span>}
          {stale && <span className="rounded-full bg-destructive px-2 py-0.5 text-xs font-semibold text-destructive-foreground">{staleLabel}</span>}
          <Pill state={item.state} />
        </div>
      </div>
      {item.evidence.length > 0 && <Chips ownerId={item.id} evidence={item.evidence} />}
    </li>
  );
}

// Keeps removed items briefly so they can fade out; marks newly added ones to fade in.
function useAnimatedList(items: BriefItem[] | undefined, resetKey: string | null) {
  const [shown, setShown] = useState<{ item: BriefItem; phase: "enter" | "leave" | "idle" }[]>([]);
  const [lastKey, setLastKey] = useState(resetKey);
  useEffect(() => {
    if (!items) return;
    const fresh = resetKey !== lastKey;
    setLastKey(resetKey);
    setShown((prev) => {
      if (fresh || prev.length === 0) return items.map((item) => ({ item, phase: "idle" as const }));
      const ids = new Set(items.map((i) => i.id));
      const prevIds = new Set(prev.filter((p) => p.phase !== "leave").map((p) => p.item.id));
      const next: { item: BriefItem; phase: "enter" | "leave" | "idle" }[] = items.map((item) => ({ item, phase: prevIds.has(item.id) ? ("idle" as const) : ("enter" as const) }));
      prev.forEach((p, idx) => { if (!ids.has(p.item.id) && p.phase !== "leave") next.splice(Math.min(idx, next.length), 0, { item: p.item, phase: "leave" }); });
      return next;
    });
    const t = setTimeout(() => setShown((s) => s.filter((p) => p.phase !== "leave")), 320);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, resetKey]);
  return shown;
}

function WrongPerson({ meeting }: { meeting: Meeting }) {
  return (
    <Popover>
      <PopoverTrigger className="text-xs font-semibold text-primary underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded">{copy.brief.wrongPerson}</PopoverTrigger>
      <PopoverContent className="w-56 p-2">
        <p className="px-2 pb-1 text-xs text-muted-foreground">{copy.brief.pickPerson}</p>
        <ul>{meeting.attendees.map((a) => <li key={a}><button type="button" className="w-full rounded px-2 py-1.5 text-left text-sm hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">{a}</button></li>)}</ul>
      </PopoverContent>
    </Popover>
  );
}

function BriefCard({ meeting }: { meeting: Meeting }) {
  const { date, req } = useSession();
  const q = useBrief(meeting.id);
  const shown = useAnimatedList(q.data?.items, meeting.id);
  const noFolders = req.folders.length === 0;
  return (
    <section aria-label={copy.brief.panel} className="mt-5 rounded-xl border-2 border-foreground p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-bold">{copy.brief.header(meeting.title, meeting.start)}</h2>
        <div className="flex items-center gap-3 text-sm"><span>{q.data?.subject || meeting.attendees[0]}</span><WrongPerson meeting={meeting} /></div>
      </div>
      {q.data && <p className="mt-1 text-xs text-muted-foreground">{copy.brief.builtFrom(q.data.sourcesChecked.notes, q.data.sourcesChecked.folders, q.data.notConnected)}</p>}
      <div className="mt-4">
        {noFolders ? <Status kind="empty" label={copy.brief.noFolders} />
          : q.isPending ? <Status kind="loading" label={copy.brief.loading} />
          : q.isError ? <Status kind="error" label={copy.brief.error} onRetry={() => q.refetch()} />
          : shown.length === 0 ? <Status kind="empty" label={copy.brief.empty} />
          : <ul className="space-y-3">{shown.map(({ item, phase }) => <Item key={item.id} item={item} today={date} phase={phase} />)}</ul>}
      </div>
    </section>
  );
}

function AskBar() {
  const [text, setText] = useState("");
  const [mic, setMic] = useState(false);
  const ask = useAsk();
  const a = ask.data;
  return (
    <div className="sticky bottom-4 mt-5 space-y-3">
      {a && (
        <div role="status" className="rounded-xl border bg-card p-4 text-sm shadow-md">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="font-medium">{a.state === "not_found" ? copy.ask.notFound(a.searched.notes) : a.answer ?? a.reason}</p>
              {a.state !== "not_found" && <p className="mt-0.5 text-xs text-muted-foreground">{a.reason}</p>}
            </div>
            <Pill state={a.state} />
          </div>
          {a.evidence.length > 0 && <Chips ownerId="ask" evidence={a.evidence} />}
        </div>
      )}
      {ask.isError && <p role="alert" className="text-sm text-destructive">{copy.ask.error}</p>}
      {mic && <p role="status" className="rounded-lg bg-warning px-3 py-2 text-sm font-semibold text-secondary-foreground">{copy.ask.micOn}</p>}
      <form className="flex items-center gap-2 rounded-full border-2 border-foreground bg-background p-1.5" onSubmit={(e) => { e.preventDefault(); if (text.trim()) ask.mutate(text.trim()); }}
        onKeyDown={(e) => { if (e.key === "Escape" && mic) setMic(false); }}>
        <button type="button" aria-pressed={mic} aria-label={mic ? copy.ask.voiceStop : copy.ask.voice} onClick={() => setMic((m) => !m)}
          className={cn("grid h-10 w-10 shrink-0 place-items-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring", mic ? "bg-destructive text-destructive-foreground" : "bg-secondary text-secondary-foreground")}>
          {mic ? <MicOff className="h-4 w-4" aria-hidden /> : <Mic className="h-4 w-4" aria-hidden />}
        </button>
        <label htmlFor="ask" className="sr-only">{copy.ask.placeholder}</label>
        <input id="ask" value={text} onChange={(e) => setText(e.target.value)} placeholder={copy.ask.placeholder} className="min-w-0 flex-1 bg-transparent px-2 text-sm outline-none placeholder:text-muted-foreground" />
        <button type="submit" disabled={ask.isPending} aria-label={copy.ask.send} className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
          <Send className="h-4 w-4" aria-hidden />
        </button>
      </form>
    </div>
  );
}

function Centre({ meetings, meeting, onSelect }: { meetings: Meeting[]; meeting: Meeting | null; onSelect: (id: string) => void }) {
  const calMsg = useCalendarMessage();
  return (
    <Panel title={copy.brief.panel} className="flex flex-col">
      <p className="text-sm text-muted-foreground">{copy.purpose}</p>
      <h1 className="mt-2 text-2xl font-bold tracking-tight">{copy.centre.heading}</h1>
      {calMsg ? <div className="mt-5"><Status kind="empty" label={calMsg} /></div> : (
        <>
          <div className="mt-5" role="group" aria-labelledby="prep-label">
            <h2 id="prep-label" className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">{copy.centre.prepareFor}</h2>
            <div className="flex flex-wrap gap-2">
              {meetings.map((m) => (
                <button key={m.id} type="button" aria-pressed={m.id === meeting?.id} onClick={() => onSelect(m.id)}
                  aria-label={`${m.start} ${m.title}${m.briefReady ? `, ${copy.centre.briefReady}` : ""}`}
                  className={cn("inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                    m.id === meeting?.id ? "border-primary bg-primary text-primary-foreground" : "hover:border-primary")}>
                  {m.briefReady && <span className="h-2 w-2 rounded-full bg-secondary" aria-hidden />}
                  <span className="font-mono">{m.start}</span> {m.title}
                </button>
              ))}
            </div>
          </div>
          {meeting ? <BriefCard meeting={meeting} /> : <div className="mt-5"><Status kind="empty" label={copy.brief.noMeeting} /></div>}
        </>
      )}
      <div className="flex-1" />
      <AskBar />
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
  const calMsg = useCalendarMessage();
  const st = useCalendarStatus();
  return (
    <Panel title={copy.calendar.panel}>
      <h2 className="mb-4 text-sm font-semibold">{copy.calendar.heading(dayLabel(date))}</h2>
      {!calMsg && st.data?.state === "connected" && <p className="-mt-3 mb-4 text-xs text-muted-foreground">{copy.calendarStatus.from(st.data.sourceLabel, timeLabel(st.data.lastReadAt))}</p>}
      {calMsg ? <Status kind="empty" label={calMsg} /> : isPending ? <Status kind="loading" label={copy.calendar.loading} /> : isError ? <Status kind="error" label={copy.calendar.error} onRetry={refetch} /> : !meetings?.length ? <Status kind="empty" label={copy.calendar.empty} /> : (
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
                  <button type="button" aria-pressed={selected} onClick={() => onSelect(e.id)}
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
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const update = () => setNow(new Date());
    const timer = window.setInterval(update, 30_000);
    document.addEventListener("visibilitychange", update);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", update);
    };
  }, []);
  const nowMin = new Date(`${date}T00:00:00`).toDateString() === now.toDateString()
    ? now.getHours() * 60 + now.getMinutes()
    : null;
  const list = m.data ?? [];
  const meeting = list.find((x) => x.id === selectedMeetingId) ?? pickDefault(list, nowMin);
  return (
    <main className="mx-auto grid min-h-screen max-w-7xl gap-4 p-4 lg:grid-cols-[260px_1fr_280px]">
      <LeftColumn />
      <Centre meetings={list} meeting={meeting} onSelect={setSelectedMeetingId} />
      <Right meetings={m.data} isPending={m.isPending} isError={m.isError} refetch={() => m.refetch()} selectedId={meeting?.id ?? null} onSelect={setSelectedMeetingId} />
    </main>
  );
}

function Index() {
  const today = new Date();
  const date = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  return <SessionProvider date={date}><Screen /><Toaster position="bottom-center" /></SessionProvider>;
}
