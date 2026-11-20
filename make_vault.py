"""
make_vault.py - creates a demo Obsidian vault of fake, messy manager notes.

Run once:   python3 make_vault.py
It creates: GoldfishVault/Meetings, People, Inbox, Attachments

Then in Obsidian choose "Open folder as vault" and pick GoldfishVault.
Everything here is invented. Never use real notes.
"""
import os
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent / "GoldfishVault"

# (subfolder, filename, last-edited date, text)
FILES = [
    ("Meetings", "2026-09-15 Priya 1-1.md", "2026-09-15",
     "# Priya 1:1\n#1on1\n\n- wants promo to senior analyst by spring\n"
     "- I said realistic IF she leads the Q4 [[vendor review]]\n"
     "- workload ok, a bit bored\n- on leave w/c 14 Dec??\n"),

    ("Meetings", "misc thurs.md", "2026-10-08",
     "P 1:1 quick one\n\nkeen on design stuff - maybe shadow the UX lot?\n"
     "said she's fed up of only doing reporting dashboards\n"
     "told her id look into it. (did i?)\n"),

    ("Meetings", "team mtg notes.md", "2026-10-20",
     "team mtg #team\n\nDECIDED: [[Priya]] leads [[vendor review]], due 30 Nov. "
     "[[Tom]] supports.\nbudget - finance still to confirm\nnew starter in Jan\n"),

    ("Meetings", "untitled 3.md", "2026-11-10",
     "call w/ finance\n\nbudget freeze. vendor review pushed to Jan.\n"
     "Priya NOT leading it now - Tom picking it up as he's around in Jan\n"
     "NEED TO TELL P!! she won't be happy (promo)\n"),

    ("Meetings", "Tom 1-1.md", "2026-11-03",
     "[[Tom]] 1:1 #1on1\n\nasked about compressed hours. laptop is dying, raise with IT.\n"
     "happy to take on more supplier work.\n"),

    ("People", "Priya.md", "2026-11-12",
     "---\naliases: [P]\n---\nanalyst, joined 2024. strong on client stuff.\n\n"
     "notes: [[2026-09-15 Priya 1-1]] , [[misc thurs]]\n"
     "her msg about the course: ![[Screenshot chat.png]]\n"),

    ("People", "Tom.md", "2026-11-03",
     "senior analyst. see [[Tom 1-1]]\n"),

    ("Inbox", "todo.md", "2026-11-16",
     "- [ ] ask Sam (UX lead) about shadowing for P\n"
     "- [ ] sign off Priya training budget - figma course, 400 quid\n"
     "- [x] book room for thurs\n- [ ] Tom laptop -> IT\n- [ ] expenses\n"),

    ("Inbox", "reminders.md", "2026-11-17",
     "27 Nov - Priya course booking closes\n"),

    ("Inbox", "half update for director.md", "2026-11-12",
     "Team update (DRAFT - not sent)\n\nHighlights:\n"
     "- Priya's onboarding deck went down really well, client asked to reuse it\n"
     "- vendor review\n- \n"),

    ("Inbox", "random.md", "2026-10-29",
     "car MOT friday\nbiscuits for thursday\nask facilities about the heating AGAIN\n"),
]

CHAT = [
    ("Priya", "hey, any news on the UX shadowing?"),
    ("Priya", "also the Figma course closes for booking on the 27th"),
    ("You", "on it - will sort this week"),
    ("Priya", "thanks! still ok for me to lead the vendor review?"),
]


def set_date(path, day):
    ts = datetime.strptime(day, "%Y-%m-%d").replace(hour=17).timestamp()
    os.utime(path, (ts, ts))


def font(size):
    for name in ("/System/Library/Fonts/Helvetica.ttc", "Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def make_screenshot(path):
    img = Image.new("RGB", (900, 420), "white")
    d = ImageDraw.Draw(img)
    d.text((30, 20), "Chat with Priya", fill="black", font=font(30))
    y = 90
    for who, msg in CHAT:
        mine = who == "You"
        d.rounded_rectangle((30, y, 870, y + 62), radius=14,
                            fill="#dbeafe" if mine else "#f1f5f9")
        d.text((48, y + 16), f"{who}: {msg}", fill="black", font=font(24))
        y += 78
    img.save(path)


def make_calendar(path):
    """A fake calendar for today, timed around right now so the demo always works.
    Re-run this script just before recording to refresh the times."""
    now = datetime.now().replace(second=0, microsecond=0)
    stamp = lambda d: d.strftime("%Y%m%dT%H%M%S")
    events = [
        ("Standup", now - timedelta(hours=2)),
        ("1:1 Priya", now + timedelta(minutes=15)),
        ("Team meeting", now + timedelta(hours=2)),
        ("Vendor review planning (Tom)", (now + timedelta(days=1)).replace(hour=9, minute=30)),
    ]
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0"]
    for title, start in events:
        lines += ["BEGIN:VEVENT", f"SUMMARY:{title}", f"DTSTART:{stamp(start)}",
                  f"DTEND:{stamp(start + timedelta(minutes=30))}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    made = 0
    for sub, name, day, text in FILES:
        folder = ROOT / sub
        folder.mkdir(parents=True, exist_ok=True)
        p = folder / name
        if p.exists():
            continue                      # never overwrite notes you have edited
        p.write_text(text, encoding="utf-8")
        set_date(p, day)
        made += 1

    shots = ROOT / "Attachments"
    shots.mkdir(parents=True, exist_ok=True)
    shot = shots / "Screenshot chat.png"
    if not shot.exists():
        make_screenshot(shot)
        set_date(shot, "2026-11-17")
        made += 1

    cal = ROOT / "Calendar"
    cal.mkdir(parents=True, exist_ok=True)
    make_calendar(cal / "calendar.ics")

    print(f"Done. {made} new notes, calendar refreshed, in: {ROOT}")


if __name__ == "__main__":
    main()
