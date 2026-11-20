"""
make_notes.py - creates a folder of fake, messy manager notes for the Goldfish demo.

Run once:   python3 make_notes.py
It creates: manager_stuff/notes, manager_stuff/todos, manager_stuff/screenshots

Everything here is invented. Never use real notes.
"""
import os
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent / "manager_stuff"

# (subfolder, filename, last-edited date, text)
FILES = [
    ("notes", "1-1 priya sept.md", "2026-09-15",
     "Priya 1:1\n\n- wants promo to senior analyst by spring\n"
     "- I said realistic IF she leads the Q4 vendor review\n"
     "- workload ok, a bit bored\n- on leave w/c 14 Dec??\n"),

    ("notes", "misc thurs.md", "2026-10-08",
     "P 1:1 quick one\n\nkeen on design stuff - maybe shadow the UX lot?\n"
     "said she's fed up of only doing reporting dashboards\n"
     "told her id look into it. (did i?)\n"),

    ("notes", "team mtg notes.md", "2026-10-20",
     "team mtg\n\nDECIDED: Priya leads vendor review, due 30 Nov. Tom supports.\n"
     "budget - finance still to confirm\nnew starter in Jan\n"),

    ("notes", "untitled 3.md", "2026-11-10",
     "call w/ finance\n\nbudget freeze. vendor review pushed to Jan.\n"
     "Priya NOT leading it now - Tom picking it up as he's around in Jan\n"
     "NEED TO TELL P!! she won't be happy (promo)\n"),

    ("notes", "half update for director.md", "2026-11-12",
     "Team update (DRAFT - not sent)\n\nHighlights:\n"
     "- Priya's onboarding deck went down really well, client asked to reuse it\n"
     "- vendor review\n- \n"),

    ("notes", "tom.md", "2026-11-03",
     "Tom 1:1\n\nasked about compressed hours. laptop is dying, raise with IT.\n"
     "happy to take on more supplier work.\n"),

    ("notes", "random.md", "2026-10-29",
     "car MOT friday\nbiscuits for thursday\nask facilities about the heating AGAIN\n"),

    ("todos", "todo.txt", "2026-11-16",
     "[ ] ask Sam (UX lead) about shadowing for P\n"
     "[ ] sign off Priya training budget - figma course, 400 quid\n"
     "[x] book room for thurs\n[ ] Tom laptop -> IT\n[ ] expenses\n"),

    ("todos", "reminders.ics", "2026-11-17",
     "BEGIN:VCALENDAR\nVERSION:2.0\n"
     "BEGIN:VEVENT\nSUMMARY:1:1 Priya\nDTSTART:20261119T100000\nEND:VEVENT\n"
     "BEGIN:VEVENT\nSUMMARY:Reminder - Priya course booking closes\n"
     "DTSTART:20261127T090000\nEND:VEVENT\n"
     "END:VCALENDAR\n"),
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


def main():
    for sub, name, day, text in FILES:
        folder = ROOT / sub
        folder.mkdir(parents=True, exist_ok=True)
        p = folder / name
        p.write_text(text, encoding="utf-8")
        set_date(p, day)

    shots = ROOT / "screenshots"
    shots.mkdir(parents=True, exist_ok=True)
    shot = shots / "Screenshot chat.png"
    make_screenshot(shot)
    set_date(shot, "2026-11-17")

    print(f"Done. Created {len(FILES) + 1} files in: {ROOT}")


if __name__ == "__main__":
    main()
