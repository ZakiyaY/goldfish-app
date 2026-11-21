import type { Meeting } from "@/api/types";
import { copy } from "@/copy";
import { cn } from "@/lib/utils";

function formatTime(time: string) {
  const [hour, minute] = time.split(":").map(Number);
  const period = hour >= 12 ? "pm" : "am";
  const hour12 = hour % 12 || 12;
  return `${hour12}${minute ? `:${String(minute).padStart(2, "0")}` : ""}${period}`;
}

export function CalendarAgenda({
  meetings,
  selectedId,
  onSelect,
}: {
  meetings: Meeting[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <ol className="space-y-2">
      {meetings.map((meeting) => {
        const selected = meeting.id === selectedId;
        const time = formatTime(meeting.start);
        return (
          <li key={meeting.id}>
            <button
              type="button"
              aria-pressed={selected}
              aria-label={`${time} ${meeting.title}${meeting.briefReady ? `, ${copy.calendar.briefReady}` : ""}`}
              onClick={() => onSelect(meeting.id)}
              className={cn(
                "flex w-full items-center gap-3 rounded-lg border p-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                selected
                  ? "border-primary bg-secondary text-secondary-foreground"
                  : "hover:border-primary",
              )}
            >
              <span className="shrink-0 font-mono text-sm font-semibold">{time}</span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-medium">{meeting.title}</span>
                {meeting.briefReady && (
                  <span className="text-xs text-muted-foreground">{copy.calendar.briefReady}</span>
                )}
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
