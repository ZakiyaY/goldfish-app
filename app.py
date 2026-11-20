"""
Goldfish - perfect recall of your notes, no memory of its own.

Run:  streamlit run app.py --browser.gatherUsageStats false

Needs LM Studio running on this Mac with its local server switched on.
"""
# ---------------------------------------------------------------------------
# 1. PRIVACY GUARD. This runs before anything else.
#    It blocks every network connection that is not to this same computer,
#    and counts the attempts so the screen can show the number.
# ---------------------------------------------------------------------------
import os
import socket

os.environ["HF_HUB_OFFLINE"] = "1"          # search model: use the local copy only
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

LOCAL_ONLY = {"127.0.0.1", "localhost", "::1"}

if not hasattr(socket, "_goldfish_blocked"):
    socket._goldfish_blocked = []            # list of blocked addresses
    _real_connect = socket.socket.connect
    _real_connect_ex = socket.socket.connect_ex

    def _is_local(address):
        # Internet addresses look like ("host", port). Anything else is on-device.
        return not isinstance(address, tuple) or str(address[0]) in LOCAL_ONLY

    def _guarded_connect(self, address):
        if not _is_local(address):
            socket._goldfish_blocked.append(str(address[0]))
            raise ConnectionRefusedError(f"Goldfish blocked a connection to {address[0]}")
        return _real_connect(self, address)

    def _guarded_connect_ex(self, address):
        if not _is_local(address):
            socket._goldfish_blocked.append(str(address[0]))
            return 61                         # "connection refused"
        return _real_connect_ex(self, address)

    socket.socket.connect = _guarded_connect
    socket.socket.connect_ex = _guarded_connect_ex

# ---------------------------------------------------------------------------
import base64
import hashlib
import json
import queue
import re
import threading
import time
from collections import deque
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import streamlit as st

WHISPER = "mlx-community/whisper-small-mlx"   # the listening model (speech -> text)
PREFERRED_MODEL = "qwen"  # part of the model's name in LM Studio
LM_PORTS = (1234, 1235)   # LM Studio's usual port, and the one it picks if that is busy
HERE = Path(__file__).parent
MAC_CAL = "Mac Calendar app"   # read live from the Calendar app, if the user ticks it
IS_MAC = sys.platform == "darwin"
LOOSE = "Loose notes"     # files sitting at the top of the folder, not in a subfolder


def default_folder():
    vault = HERE / "GoldfishVault"
    return str(vault if vault.exists() else HERE / "manager_stuff")


def folder():
    """The notes folder (or Obsidian vault) the user pointed Goldfish at."""
    return Path(st.session_state.get("folder") or default_folder()).expanduser()


def hidden(p, root):
    """True for hidden files and anything inside a hidden folder such as .obsidian."""
    return any(part.startswith(".") for part in p.relative_to(root).parts)
TEXT_TYPES = {".md", ".txt", ".ics"}
IMAGE_TYPES = {".png", ".jpg", ".jpeg"}
WEAK_MATCH = 0.25      # below this similarity, Goldfish says "not sure"


# ---------------------------------------------------------------------------
# 2. THE TWO LOCAL MODELS
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading the search model (first time only)...")
def search_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def embed(texts):
    return np.asarray(search_model().encode(list(texts), normalize_embeddings=True))


def lm_base():
    """Find LM Studio on this Mac. Remembers the port once found."""
    ss = st.session_state
    if ss.get("lm_port") and time.time() - ss.get("lm_checked", 0) < 20:
        return f"http://localhost:{ss['lm_port']}/v1"          # checked a moment ago
    ports = ([ss["lm_port"]] if ss.get("lm_port") else []) + list(LM_PORTS)
    for port in ports:
        try:
            with urllib.request.urlopen(f"http://localhost:{port}/v1/models", timeout=3) as r:
                names = [m["id"] for m in json.load(r)["data"]]
            names = [n for n in names if "embed" not in n.lower()]
            # LM Studio lists every model it has. Pick the one Goldfish needs.
            names.sort(key=lambda n: PREFERRED_MODEL not in n.lower())
            if names:
                ss["lm_port"], ss["lm_model"], ss["lm_checked"] = port, names[0], time.time()
                return f"http://localhost:{port}/v1"
        except Exception:
            continue
    ss.pop("lm_port", None)
    raise ConnectionError("LM Studio is not answering")


def _post(path, payload):
    req = urllib.request.Request(lm_base() + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def local_model_name():
    lm_base()
    return st.session_state["lm_model"]


def ask_raw(base, model, prompt, image_path=None, max_tokens=900):
    """Ask the local model. Uses nothing from the screen, so it is safe in the background."""
    content = [{"type": "text", "text": prompt}]
    if image_path:
        kind = "jpeg" if image_path.suffix.lower() in {".jpg", ".jpeg"} else "png"
        b64 = base64.b64encode(image_path.read_bytes()).decode()
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:image/{kind};base64,{b64}"}})
    req = urllib.request.Request(base + "/chat/completions", data=json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        out = json.load(r)
    text = out["choices"][0]["message"]["content"] or ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    return "" if "<think>" in text else text.strip()


def ask_stream(base, model, prompt, max_tokens=900, on_text=None):
    """Like ask_raw, but hands over the text as it is written so the screen can show it."""
    req = urllib.request.Request(base + "/chat/completions", data=json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "stream": True,
    }).encode(), headers={"Content-Type": "application/json"})
    text, last = "", 0.0
    with urllib.request.urlopen(req, timeout=600) as r:
        for raw in r:
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                piece = json.loads(data)["choices"][0].get("delta", {}).get("content") or ""
            except (ValueError, KeyError, IndexError):
                continue
            text += piece
            if on_text and time.time() - last > 0.12:
                last = time.time()
                shown = re.sub(r"<think>.*?(</think>|$)", "", text, flags=re.S).strip()
                on_text(shown)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    return "" if "<think>" in text else text.strip()


@st.cache_resource
def warm_up(base, model):
    """Wake the model once, in the background, so the first real answer is not slow.
    The wake-up message contains none of your notes."""
    def ping():
        try:
            ask_raw(base, model, "Reply with the word OK.", max_tokens=2)
        except Exception:
            pass
    threading.Thread(target=ping, daemon=True).start()
    return True


def ask_model(prompt, image_path=None, max_tokens=900):
    base = lm_base()
    return ask_raw(base, st.session_state["lm_model"], prompt, image_path, max_tokens)


# ---------------------------------------------------------------------------
# 3. READING NOTES (read-only, into memory, nothing written anywhere)
# ---------------------------------------------------------------------------
def fingerprint(folder):
    """One short code that changes if any file is added, removed or edited."""
    h, count = hashlib.sha256(), 0
    for p in sorted(folder.rglob("*")):
        if p.is_file() and not hidden(p, folder):
            h.update(str(p.relative_to(folder)).encode())
            h.update(p.read_bytes())
            count += 1
    return h.hexdigest()[:16], count


def readable(p):
    return p.is_file() and p.suffix.lower() in TEXT_TYPES | IMAGE_TYPES


def sources():
    root = folder()
    if not root.is_dir():
        return []
    found = sorted(d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith("."))
    if any(readable(p) and not p.name.startswith(".") for p in root.iterdir()):
        found.append(LOOSE)
    if IS_MAC:
        found.append(MAC_CAL)
    return found


def files_in(source):
    root = folder()
    if source == MAC_CAL:
        return []                       # not a folder: it is read from the Calendar app
    if source == LOOSE:
        return sorted(p for p in root.iterdir() if readable(p) and not p.name.startswith("."))
    return sorted(p for p in (root / source).rglob("*") if readable(p) and not hidden(p, root))


def is_obsidian_vault():
    return (folder() / ".obsidian").is_dir()


def open_in_obsidian(path):
    """Ask this Mac to open the note in the Obsidian app. Nothing leaves the device."""
    subprocess.run(["open", "obsidian://open?path=" + urllib.parse.quote(path)], check=False)


def plain_name(item):
    where = ("at the top of your notes folder" if item["source"] == LOOSE
             else "from the Calendar app on this Mac" if item["source"] == MAC_CAL
             else f"in your {item['source']} folder")
    return f"“{item['title']}” {where} (last edited {item['edited']}, {ago(item['when'])})"


def parse_ics(text):
    """Read a calendar file (.ics) into a list of {title, start, all_day}."""
    events, cur = [], None
    lines = text.replace("\r\n", "\n").replace("\n ", "").replace("\n\t", "").split("\n")
    for line in lines:
        line = line.strip()
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT":
            if cur and "start" in cur:
                cur.setdefault("title", "(no title)")
                events.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            key, value = line.split(":", 1)
            field = key.split(";")[0].upper()
            if field == "SUMMARY":
                cur["title"] = value.replace("\\,", ",").replace("\\n", " ").strip()
            elif field == "DTSTART":
                try:
                    if len(value) == 8:
                        cur["start"], cur["all_day"] = datetime.strptime(value, "%Y%m%d"), True
                    else:
                        when = datetime.strptime(value[:15], "%Y%m%dT%H%M%S")
                        if value.endswith("Z"):
                            when = (when.replace(tzinfo=timezone.utc).astimezone()
                                    .replace(tzinfo=None))
                        cur["start"], cur["all_day"] = when, False
                except ValueError:
                    pass
    return sorted(events, key=lambda e: e["start"])


def calendar_text(events):
    """A calendar as plain lines, so it can be searched like any other note."""
    return "\n".join(e["start"].strftime("%a %d %b" if e["all_day"] else "%a %d %b %H:%M")
                     + " - " + e["title"] for e in events)


@st.cache_resource
def _event_store():
    import EventKit
    return EventKit.EKEventStore.alloc().init()


def mac_calendar_events(days=7):
    """Ask macOS for the next week of events. Read-only, and it never leaves this Mac.
    The first time, macOS shows its own permission box."""
    import EventKit
    import Foundation
    store = _event_store()
    answered, result = threading.Event(), {}

    def done(granted, error):
        result["ok"] = bool(granted)
        answered.set()

    if hasattr(store, "requestFullAccessToEventsWithCompletion_"):      # macOS 14 and later
        store.requestFullAccessToEventsWithCompletion_(done)
    else:
        store.requestAccessToEntityType_completion_(EventKit.EKEntityTypeEvent, done)
    answered.wait(90)
    if not result.get("ok"):
        raise PermissionError("calendar access was not allowed")

    start = Foundation.NSCalendar.currentCalendar().startOfDayForDate_(Foundation.NSDate.date())
    end = start.dateByAddingTimeInterval_(days * 86400.0)
    wanted = store.predicateForEventsWithStartDate_endDate_calendars_(start, end, None)
    events = []
    for e in store.eventsMatchingPredicate_(wanted) or []:
        events.append({"title": str(e.title() or "(no title)"),
                       "start": datetime.fromtimestamp(e.startDate().timeIntervalSince1970()),
                       "all_day": bool(e.isAllDay())})
    return sorted(events, key=lambda e: e["start"])


def mac_calendar(allowed):
    """The Mac's calendar, only if the user ticked it. Held in memory for a minute at a time."""
    ss = st.session_state
    if MAC_CAL not in allowed:
        ss.pop("mac_cal", None)
        ss.pop("cal_error", None)
        return []
    cached = ss.get("mac_cal")
    if cached and time.time() - cached[0] < 60:
        return cached[1]
    events, ss["cal_error"] = [], None
    try:
        with st.spinner("Asking this Mac for your calendar. If a box pops up, click Allow."):
            events = mac_calendar_events()
    except ImportError:
        ss["cal_error"] = ("One more install is needed. In Terminal run:  "
                           "pip install pyobjc-framework-EventKit   then restart Goldfish.")
    except PermissionError:
        ss["cal_error"] = ("Your Mac has not allowed calendar access. Open System Settings > "
                           "Privacy & Security > Calendars, switch Terminal on, then restart "
                           "Goldfish.")
    except Exception as e:
        ss["cal_error"] = f"I could not read the Calendar app ({type(e).__name__})."
    ss["mac_cal"] = (time.time(), events)
    return events


def todays_events(allowed):
    """Events from calendar files in the sources the user ticked, plus the Mac's
    own calendar if that is ticked."""
    events = list(mac_calendar(allowed))
    for source in allowed:
        for p in files_in(source):
            if p.suffix.lower() == ".ics":
                events += parse_ics(p.read_text(encoding="utf-8", errors="ignore"))
    return sorted(events, key=lambda e: e["start"])


def load_into_memory(allowed):
    """Fill st.session_state.memory with the allowed sources. Lives in RAM only."""
    memory = st.session_state.memory
    for key in [k for k, v in memory.items() if v["source"] not in allowed]:
        del memory[key]                       # user changed their mind: drop it now

    memory.pop("mac-calendar", None)
    if MAC_CAL in allowed:
        events = mac_calendar(allowed)
        if events:
            memory["mac-calendar"] = {
                "source": MAC_CAL, "path": "", "title": "My calendar", "kind": "text",
                "edited": datetime.now().strftime("%d %b %Y"), "when": time.time(),
                "text": calendar_text(events), "links": [],
            }

    for source in allowed:
        for p in files_in(source):
            key = str(p)
            ext = p.suffix.lower()
            if key in memory:
                continue
            if ext == ".ics":
                text = calendar_text(parse_ics(p.read_text(encoding="utf-8", errors="ignore")))
            elif ext in TEXT_TYPES:
                text = p.read_text(encoding="utf-8", errors="ignore")
            elif ext in IMAGE_TYPES:
                text = ask_model("Copy out all the text in this image exactly as "
                                 "written, including who said each line. "
                                 "Do not add anything.", image_path=p, max_tokens=400)
            else:
                continue
            memory[key] = {
                "source": source,
                "path": key,
                "title": p.stem,
                "kind": "screenshot" if ext in IMAGE_TYPES else "text",
                "edited": datetime.fromtimestamp(p.stat().st_mtime).strftime("%d %b %Y"),
                "when": p.stat().st_mtime,
                "text": text.strip(),
                # Obsidian links like [[misc thurs]] or ![[picture.png]]
                "links": [] if ext in IMAGE_TYPES else
                         [l.strip().lower() for l in re.findall(r"\[\[([^\]|#]+)", text)],
            }
    if memory:
        items = list(memory.values())
        vectors = embed(f"{i['title']}\n{i['text']}" for i in items)
        for item, v in zip(items, vectors):
            item["vector"] = v


def search(query, top=4):
    items = list(st.session_state.memory.values())
    if not items:
        return []
    q = embed([query])[0]
    scored = [(float(i["vector"] @ q), i) for i in items]
    return sorted(scored, key=lambda s: -s[0])[:top]


# ---------------------------------------------------------------------------
# 4. THE BRIEF
# ---------------------------------------------------------------------------
BRIEF_PROMPT = """You are preparing a manager for a 1:1 meeting with {name}.
Use ONLY the notes below. They are messy and may be about other people too.
"P" or initials may refer to {name}.

Today is {today}.

Rules:
- Never invent anything. If the notes do not say it, do not say it.
- When you mention a promise or a decision, say how long ago it was written,
  using the ages given with each note (for example "6 weeks ago").
- After every bullet, name the note it came from like this: (from: note title).
- When two notes disagree, trust the one edited most recently and say so.
- Keep every bullet short.

Write exactly these six sections, with these headings:

### Start here
(ONE sentence: the single most important thing to raise first in this meeting,
and why. Choose the thing {name} most needs to hear, especially any bad news
they have not been told yet.)
### What you promised {name}
### What {name} told you (goals and interests)
### What has changed (older notes that are now out of date)
### Dates coming up
### What I could not find
(In the last section list useful things the notes do NOT contain, for example
missing dates or whether a promise was kept. If nothing is missing, say so.)

NOTES (oldest first):
{notes}
"""


def ago(when):
    """Turn a timestamp into plain words, because '8 Oct' means little at a glance."""
    days = (datetime.now() - datetime.fromtimestamp(when)).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 14:
        return f"{days} days ago"
    if days < 70:
        return f"{round(days / 7)} weeks ago"
    return f"{round(days / 30)} months ago"


def aliases_for(name):
    """Short names from the person's own note, e.g. Obsidian's  aliases: [P]"""
    found = []
    for i in st.session_state.memory.values():
        if i["title"].lower() == name.lower():
            m = re.search(r"aliases:\s*\[([^\]]*)\]", i["text"])
            if m:
                found += [a.strip().strip("\"'") for a in m.group(1).split(",") if a.strip()]
    return found


def refers_to(text, name, aliases):
    if name.lower() in text.lower():
        return True
    return any(re.search(rf"(?<![A-Za-z]){re.escape(a)}(?![A-Za-z])", text) for a in aliases)


PROMISE_WORDS = re.compile(
    r"need to tell|told (her|him|them) i|i said i|look into|follow up|chase|"
    r"get back to|remind (her|him|them)|still to|\(did i\?\)", re.I)


def open_loops(name, used):
    """Things left hanging, quoted word for word from the notes. No model involved,
    so nothing here can be invented."""
    aliases = aliases_for(name)
    loops = []
    for item in used:
        if item["kind"] != "text":
            continue
        first_line = next((l for l in item["text"].splitlines() if l.strip()), "")
        about_them = refers_to(item["title"] + " " + first_line, name, aliases)
        for line in item["text"].splitlines():
            clean = line.strip()
            task = re.match(r"^(?:[-*]\s*)?\[ \]\s*(.+)", clean)
            if task and refers_to(clean, name, aliases):
                loops.append({"kind": "task", "text": task.group(1).strip(), "item": item})
            elif (not re.match(r"^(?:[-*]\s*)?\[.\]", clean) and PROMISE_WORDS.search(clean)
                  and (refers_to(clean, name, aliases) or about_them)):
                loops.append({"kind": "said", "text": clean.lstrip("-* ").strip(), "item": item})
    loops.sort(key=lambda l: l["item"]["when"])          # longest-waiting first
    return loops[:6]


def build_brief(name, on_text=None):
    probes = [
        f"{name} development goals and career interests",
        f"things I promised {name}, action items for {name}",
        f"decisions and changes affecting {name}",
        f"{name} dates deadlines reminders",
    ]
    memory = st.session_state.memory
    aliases = aliases_for(name)
    person_notes = [i for i in memory.values() if i["title"].lower() == name.lower()]
    linked = {l for i in person_notes for l in i["links"]}
    linked |= {l.rsplit(".", 1)[0] for l in linked}          # "pic.png" -> "pic"

    found = {}
    for probe in probes:
        for rank, (score, item) in enumerate(search(probe)):
            key = (item["source"], item["title"])
            names_them = (refers_to(item["title"] + item["text"], name, aliases)
                          or item["title"].lower() in linked)
            # Keep the two best matches per question; the rest must be a decent
            # match or mention the person by name.
            if rank >= 2 and score < WEAK_MATCH and not names_them:
                continue
            if key not in found or score > found[key][0]:
                found[key] = (score, item)

    # Notes the person's own note links to are always included (score -1 = "linked").
    for item in memory.values():
        key = (item["source"], item["title"])
        if item["title"].lower() in linked and key not in found:
            found[key] = (-1.0, item)

    mentions = [i for i in memory.values()
                if refers_to(i["title"] + i["text"], name, aliases)]
    # Notes that name the person are included too, newest first (score -2 = "by name").
    for item in sorted(mentions, key=lambda i: -i["when"]):
        key = (item["source"], item["title"])
        if key not in found and len(found) < 12:
            found[key] = (-2.0, item)
    best = max((s for s, _ in found.values()), default=0.0)

    # Honest when unsure: no mention and only weak matches -> do not ask the model at all.
    if not mentions and best < WEAK_MATCH + 0.15:
        closest = max(found.values(), key=lambda s: s[0], default=None)
        return None, closest, []

    used = sorted((i for _, i in found.values()), key=lambda i: i["when"])
    notes = "\n\n".join(
        f"--- note title: {i['title']} | where: {i['source']} | type: {i['kind']} "
        f"| last edited: {i['edited']} ({ago(i['when'])})\n{i['text']}" for i in used)
    today = datetime.now().strftime("%A %d %B %Y")
    prompt = BRIEF_PROMPT.format(name=name, notes=notes, today=today)
    try:
        text = ask_stream(lm_base(), st.session_state["lm_model"], prompt, 1100, on_text)
    except Exception:
        text = ""
    if not text:                                   # streaming not supported: ask the plain way
        text = ask_model(prompt, max_tokens=1100)
    return text, sorted(found.values(), key=lambda s: -s[0]), open_loops(name, used)


# ---------------------------------------------------------------------------
# 4b. GOLDFISH LIVE: it listens, and the right note surfaces by itself
# ---------------------------------------------------------------------------
INSIGHT_PROMPT = """A manager is in a meeting right now. They just said:
"{heard}"

These lines are from the manager's own notes (newest first):
{notes}

In ONE short sentence of at most 25 words, tell the manager the most useful thing
these notes say about what was just said. If the notes disagree with each other or
with what was said, trust the newest note and say so plainly.
Never invent anything. If the notes are not really about what was said, reply with
the single word NOTHING."""


class Live:
    """Holds everything for live listening. All of it lives in memory only."""

    def __init__(self):
        self.lock = threading.Lock()
        self.stop_flag = threading.Event()
        self.threshold = 0.38
        self.clear()

    def clear(self):
        self.running = False
        self.mic = False
        self.error = None
        self.level = 0.0
        self.status = "Off"
        self.heard = deque(maxlen=3)
        self.cards = deque(maxlen=5)
        self.chunks, self.matrix, self.boost = [], None, None
        self.shown = {}
        self.count = 0

    # ---- notes -----------------------------------------------------------
    def set_notes(self, chunks, matrix, boost):
        with self.lock:
            self.chunks, self.matrix, self.boost = chunks, matrix, boost
            keep = {c["path"] for c in chunks}
            self.cards = deque((c for c in self.cards
                                if all(n["path"] in keep for n in c["notes"])), maxlen=5)

    # ---- start / stop ----------------------------------------------------
    def start(self, model, llm, hints, use_mic):
        self.stop_flag = threading.Event()
        self.model, self.llm, self.hints = model, llm, hints
        self.utterances = queue.Queue(maxsize=4)
        self.insights = queue.Queue(maxsize=2)
        self.running, self.mic, self.error = True, use_mic, None
        self.status = "Getting ready..." if use_mic else "Ready (typing only)"
        threading.Thread(target=self._insight_loop, args=(self.stop_flag,), daemon=True).start()
        if use_mic:
            threading.Thread(target=self._transcribe_loop, args=(self.stop_flag,),
                             daemon=True).start()
            threading.Thread(target=self._listen_loop, args=(self.stop_flag,),
                             daemon=True).start()

    def stop(self, forget=False):
        self.stop_flag.set()
        self.running, self.mic, self.level, self.status = False, False, 0.0, "Off"
        with self.lock:
            self.heard.clear()                 # what was said is never kept
            if forget:
                self.cards.clear()
                self.chunks, self.matrix, self.boost = [], None, None
                self.shown = {}

    # ---- the core: something was said -> surface the matching notes -------
    def hear(self, text):
        text = " ".join(text.split())
        if len(text.split()) < 3 or self.matrix is None or not len(self.chunks):
            return
        vec = self.model.encode([text], normalize_embeddings=True)[0]
        with self.lock:
            self.heard.appendleft(text)
            scores = self.matrix @ vec + self.boost
            best = {}
            for idx in np.argsort(-scores)[:25]:
                chunk = self.chunks[idx]
                if chunk["path"] not in best:
                    best[chunk["path"]] = (float(scores[idx]), chunk)
            top = [(sc, ch) for sc, ch in best.values() if sc >= self.threshold][:3]
            if not top:
                return
            top = [t for t in top if t[0] >= top[0][0] - 0.08]   # only close runners-up
            key = (top[0][1]["path"], top[0][1]["line"])
            if time.time() - self.shown.get(key, 0) < 25:
                return                          # same thing was shown a moment ago
            self.shown[key] = time.time()
            notes = sorted((dict(ch, score=sc) for sc, ch in top), key=lambda n: -n["when"])
            self.count += 1
            card = {"id": self.count, "heard": text, "at": time.time(), "notes": notes,
                    "insight": None}
            self.cards.appendleft(card)
        try:
            self.insights.put_nowait(card)
        except queue.Full:
            card["insight"] = ""

    def _insight_loop(self, stop):
        while not stop.is_set():
            try:
                card = self.insights.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                notes = "\n".join(f'- "{n["line"]}" (note: {n["title"]}, written {ago(n["when"])})'
                                  for n in card["notes"])
                out = self.llm(INSIGHT_PROMPT.format(heard=card["heard"], notes=notes))
                out = out.strip().strip('"')
                card["insight"] = "" if out.upper().startswith("NOTHING") else out
            except Exception:
                card["insight"] = ""

    # ---- microphone -> speech chunks ---------------------------------------
    def _listen_loop(self, stop):
        try:
            import sounddevice as sd
        except Exception:
            self.error = ("The microphone library is missing. In Terminal run:  "
                          "pip install sounddevice mlx-whisper")
            self.mic = False
            return
        try:
            with sd.InputStream(samplerate=16000, channels=1, dtype="float32",
                                blocksize=1600) as stream:
                first, buf, pre = [], [], deque(maxlen=3)
                limit, quiet, speech = 0.012, 0, 0
                while not stop.is_set():
                    block, _ = stream.read(1600)            # a tenth of a second
                    block = block[:, 0].copy()
                    rms = float(np.sqrt(np.mean(block ** 2)))
                    self.level = rms
                    if len(first) < 5:                       # learn how loud the room is
                        first.append(rms)
                        limit = max(0.012, 3.5 * float(np.mean(first)))
                        continue
                    if rms > limit:
                        if not buf:
                            buf.extend(pre)
                        buf.append(block)
                        speech, quiet = speech + 1, 0
                    elif buf:
                        buf.append(block)
                        quiet += 1
                    else:
                        pre.append(block)
                    if buf and (quiet >= 5 or len(buf) >= 90):   # a pause, or 9 seconds
                        if speech >= 4:
                            try:
                                self.utterances.put_nowait(np.concatenate(buf))
                            except queue.Full:
                                pass
                        buf, quiet, speech = [], 0, 0           # the sound is dropped here
        except Exception as e:
            self.error = ("I could not open the microphone. Check System Settings > Privacy & "
                          f"Security > Microphone allows Terminal. ({type(e).__name__})")
            self.mic = False

    def _transcribe_loop(self, stop):
        try:
            import mlx_whisper
            mlx_whisper.transcribe(np.zeros(16000, dtype=np.float32), path_or_hf_repo=WHISPER,
                                   language="en")           # loads the model once
        except Exception as e:
            self.error = ("The listening model is not ready. With Wi-Fi on, run the download "
                          f"line from the setup steps. ({type(e).__name__})")
            self.mic = False
            return
        self.status = "Listening"
        while not stop.is_set():
            try:
                audio = self.utterances.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                out = mlx_whisper.transcribe(audio, path_or_hf_repo=WHISPER, language="en",
                                             initial_prompt=self.hints,
                                             condition_on_previous_text=False)
                segs = out.get("segments") or []
                if segs and all(s.get("no_speech_prob", 0) > 0.6 for s in segs):
                    continue                                # that was not speech
                if not stop.is_set():
                    self.hear(out.get("text", ""))
            except Exception as e:
                self.error = f"Listening hit a problem ({type(e).__name__}). Stop and start again."


@st.cache_resource
def live():
    return Live()


def live_notes(focus):
    """Cut the notes in memory into single lines so the exact line can surface."""
    chunks = []
    aliases = aliases_for(focus) if focus else []
    for item in st.session_state.memory.values():
        about = bool(focus) and refers_to(item["title"] + " " + item["text"], focus, aliases)
        lines = [l.strip(" -*#>\t") for l in item["text"].splitlines()]
        lines = [l for l in lines if len(l.split()) >= 3 and not l.startswith(("---", "aliases:"))]
        for line in lines or [item["title"]]:
            chunks.append({"path": item["path"], "title": item["title"], "source": item["source"],
                           "kind": item["kind"], "when": item["when"], "line": line,
                           "about": about})
    if not chunks:
        return [], None, None
    matrix = embed(f'{c["title"]}: {c["line"]}' for c in chunks)
    boost = np.array([0.05 if c["about"] else 0.0 for c in chunks])
    return chunks, matrix, boost


def next_meeting(events):
    """The meeting happening now or next today, and how far away it is."""
    now = datetime.now()
    coming = [e for e in events if not e["all_day"]
              and e["start"].date() == now.date()
              and (e["start"] - now).total_seconds() > -20 * 60]
    if not coming:
        return None, ""
    e = coming[0]
    mins = round((e["start"] - now).total_seconds() / 60)
    gap = ("now" if -1 <= mins <= 1 else f"started {-mins} min ago" if mins < 0
           else f"in {mins} min" if mins < 90 else f"in {round(mins / 60)} hours")
    return e, gap


def person_in(title, memory):
    """If a meeting title contains the title of one of your notes (e.g. Priya), that is who."""
    names = sorted({i["title"] for i in memory.values() if len(i["title"].split()) <= 2
                    and len(i["title"]) >= 3}, key=len, reverse=True)
    for n in names:
        if re.search(rf"(?<![A-Za-z]){re.escape(n)}(?![A-Za-z])", title, re.I):
            return n
    return ""


# ---------------------------------------------------------------------------
# 5. HOW IT LOOKS
# ---------------------------------------------------------------------------
import html

CSS = """
<style>
.block-container {padding-top: 2.2rem; max-width: 1100px;}
[data-stale="true"] {opacity: 1 !important; transition: none !important;}
[data-testid="stStatusWidget"] {visibility: hidden;}
.gf-hero {display:flex; align-items:center; gap:16px; margin-bottom:4px;}
.gf-hero .fish {font-size:3.2rem; line-height:1;}
.gf-hero h1 {margin:0; padding:0; font-size:2.6rem; letter-spacing:-1px;}
.gf-tag {opacity:.75; font-size:1.05rem; margin:0 0 10px 0;}
.gf-pill {display:inline-block; font-size:.8rem; padding:3px 12px; border-radius:999px;
  margin:0 6px 6px 0; border:1px solid rgba(34,197,94,.55); background:rgba(34,197,94,.14);}
.gf-pill.blue {border-color:rgba(56,189,248,.55); background:rgba(56,189,248,.14);}
.gf-card {border:1px solid rgba(128,128,128,.28); border-left:5px solid #38bdf8;
  border-radius:14px; padding:14px 20px 10px 20px; margin-bottom:14px;
  background:rgba(128,128,128,.07);}
.gf-card h4 {margin:0 0 8px 0; padding:0; font-size:1.08rem;}
.gf-card ul {margin:0 0 6px 0; padding-left:1.2rem;}
.gf-card li, .gf-card p {margin:0 0 6px 0; line-height:1.5;}
.gf-card.start {border-left-color:#22c55e; background:rgba(34,197,94,.13);
  padding:18px 22px 14px 22px;}
.gf-card.start p, .gf-card.start li {font-size:1.25rem; line-height:1.45; font-weight:600;}
.gf-card.loops {border-left-color:#f97316;}
.gf-when {display:inline-block; font-size:.74rem; padding:1px 9px; border-radius:999px;
  margin-left:6px; white-space:nowrap; border:1px solid rgba(249,115,22,.6);
  background:rgba(249,115,22,.16);}
.gf-when.past {border-color:rgba(163,163,163,.6); background:rgba(163,163,163,.16);}
.gf-quote {font-style:italic;}
.gf-next {display:flex; gap:14px; align-items:baseline; flex-wrap:wrap; padding:12px 18px;
  border-radius:14px; border:1px solid rgba(128,128,128,.28); background:rgba(128,128,128,.07);
  margin-bottom:12px;}
.gf-next .t {font-size:1.25rem; font-weight:700;}
.gf-next .g {font-size:.95rem; padding:2px 12px; border-radius:999px;
  background:rgba(249,115,22,.18); border:1px solid rgba(249,115,22,.6);}
.gf-next .o {opacity:.65; font-size:.85rem;}
.gf-live {border-radius:18px; padding:22px 26px 16px 26px; margin:10px 0 14px 0;
  border:1px solid rgba(56,189,248,.5); background:rgba(56,189,248,.08);}
.gf-live.conflict {border-color:#f59e0b; background:rgba(245,158,11,.12);}
.gf-live.old {opacity:.55; padding:12px 18px 8px 18px;}
.gf-live .say {font-size:1.7rem; font-weight:700; line-height:1.3; margin:0 0 12px 0;}
.gf-live.old .say {font-size:1.05rem; margin-bottom:6px;}
.gf-live .wait {font-size:1rem; opacity:.6; margin:0 0 10px 0;}
.gf-live .line {font-size:1.05rem; margin:0 0 7px 0; line-height:1.45;}
.gf-live.old .line {font-size:.9rem;}
.gf-live .heard {font-size:.8rem; opacity:.6; margin-top:8px;}
.gf-new {font-size:.7rem; font-weight:700; padding:1px 8px; border-radius:999px; margin-right:6px;
  background:#f59e0b; color:#111;}
.gf-meter {height:8px; border-radius:99px; background:rgba(128,128,128,.25); overflow:hidden;
  margin:6px 0 2px 0;}
.gf-meter div {height:100%; background:#22c55e; transition:width .2s;}
.gf-card.warn {border-left-color:#f59e0b; background:rgba(245,158,11,.12);}
.gf-card.miss {border-left-color:#a3a3a3; border-style:dashed; border-left-style:solid;}
.gf-chip {display:inline-block; font-size:.74rem; padding:1px 9px; border-radius:999px;
  margin-left:6px; white-space:nowrap; border:1px solid rgba(56,189,248,.55);
  background:rgba(56,189,248,.16);}
.gf-bowl {text-align:center; padding:16px 10px 20px 10px; margin:4px 0 10px 0;
  border:2px solid rgba(56,189,248,.6); border-top:2px dashed rgba(56,189,248,.35);
  border-radius:18px 18px 90px 90px / 18px 18px 70px 70px;
  background:linear-gradient(180deg, rgba(56,189,248,.04), rgba(56,189,248,.20));}
.gf-bowl .n {font-size:2.2rem; font-weight:700; line-height:1.1;}
.gf-bowl .f {font-size:1.25rem; letter-spacing:2px; min-height:1.6rem;}
.gf-bowl .l {font-size:.8rem; opacity:.8;}
.gf-proof {font-size:.84rem; padding:8px 12px; border-radius:10px; margin-bottom:8px;
  border:1px solid rgba(128,128,128,.28); background:rgba(128,128,128,.07);}
.gf-proof b {font-size:1.05rem;}
.gf-proof code {font-size:.78rem;}
.gf-ok {border-color:rgba(34,197,94,.6); background:rgba(34,197,94,.14);}
.gf-bad {border-color:rgba(239,68,68,.6); background:rgba(239,68,68,.14);}
</style>
"""

ICONS = [("start here", "🟢", "start"), ("promised", "🤝", ""), ("told", "🎯", ""), ("changed", "⚠️", "warn"),
         ("coming up", "📅", ""), ("not find", "🔍", "miss")]
def icon_for(item):
    return "🖼️" if item["kind"] == "screenshot" else "📝"


MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
DATE_RE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(MONTHS) + r")[a-z]*\b")


def _countdown(match):
    """Add 'in 8 days' after a date. The model picks the date; code does the sums."""
    try:
        now = datetime.now()
        day = datetime(now.year, MONTHS.index(match.group(2)) + 1, int(match.group(1)))
        if (day.date() - now.date()).days < -180:
            day = day.replace(year=now.year + 1)
        gap = (day.date() - now.date()).days
    except ValueError:
        return match.group(0)
    if gap > 120 or gap < -45:
        return match.group(0)
    words = ("today" if gap == 0 else "tomorrow" if gap == 1 else f"in {gap} days" if gap > 1
             else "yesterday" if gap == -1 else f"{-gap} days ago")
    return f'{match.group(0)}<span class="gf-when{" past" if gap < 0 else ""}">⏳ {words}</span>'


def _inline(text, countdown=False):
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text, chips = re.subn(r"\(from:\s*([^)]+)\)", r'<span class="gf-chip">📄 \1</span>', text)
    if not countdown:
        return text
    head, sep, tail = text.partition('<span class="gf-chip">')
    return DATE_RE.sub(_countdown, head) + sep + tail     # no countdowns inside note titles


SECTION_START = re.compile(
    r"^(start here|what you promised[^:\n]*|what [^:\n]{1,40} told you[^:\n]*|"
    r"what has changed[^:\n]*|dates coming up|what i could not find)\s*[:\-–—]?\s*(.*)$", re.I)


def tidy_headings(text):
    """Small models write headings in different ways: '### Start here', '**Start here**',
    '1. Start here: Tell Priya...'. Turn all of them into one shape."""
    out = []
    for line in text.splitlines():
        bare = line.strip().lstrip("#*_ 0123456789.").rstrip("*_ ")
        m = None if line.lstrip().startswith(("-", "•")) else SECTION_START.match(bare)
        if m:
            out.append("### " + m.group(1).strip().rstrip("*_: "))
            rest = m.group(2).strip().lstrip("*_: ").strip()
            if rest:
                out.append(rest)
        else:
            out.append(line)
    return "\n".join(out)


def sections_of(text):
    """Split the model's answer into (heading, [lines]). Empty list if it has no headings."""
    parts = re.split(r"(?m)^#{1,4}\s*(.+?)\s*$", tidy_headings(text))
    return [(h.strip(), [l.strip() for l in b.strip().splitlines() if l.strip()])
            for h, b in zip(parts[1::2], parts[2::2])]


def plain(line):
    """A bullet as plain words: no bullet mark, no source tag, no bold marks."""
    line = re.sub(r"^[-*•]\s+", "", line)
    line = re.sub(r"\(from:[^)]*\)", "", line)
    return line.replace("**", "").strip()


def card(heading, lines):
    icon, style = "📌", ""
    for key, ic, st_ in ICONS:
        if key in heading.lower():
            icon, style = ic, st_
    cd = "coming up" in heading.lower()      # countdowns only on the dates card
    bullets, out = [], []
    for line in lines:
        if line.startswith("(") and line.endswith(")") and "from:" not in line:
            continue                                   # the model echoing an instruction
        if re.match(r"^[-*•]\s+", line):
            bullets.append("<li>" + _inline(re.sub(r"^[-*•]\s+", "", line), cd) + "</li>")
        else:
            if bullets:
                out.append("<ul>" + "".join(bullets) + "</ul>")
                bullets = []
            out.append("<p>" + _inline(line, cd) + "</p>")
    if bullets:
        out.append("<ul>" + "".join(bullets) + "</ul>")
    return (f'<div class="gf-card {style}"><h4>{icon} {_inline(heading)}</h4>'
            + "".join(out) + "</div>")


def loops_card(loops):
    if not loops:
        return ""
    rows = []
    for l in loops:
        age = ago(l["item"]["when"])
        chip = f'<span class="gf-chip">📄 {html.escape(l["item"]["title"])}</span>'
        when = f'<span class="gf-when past">⏳ written {age}</span>'
        if l["kind"] == "task":
            rows.append(f"<li>☐ {html.escape(l['text'])}{when}{chip}</li>")
        else:
            rows.append(f'<li>You wrote: <span class="gf-quote">“{html.escape(l["text"])}”</span>'
                        f"{when}{chip}</li>")
    return ('<div class="gf-card loops"><h4>🧶 Loose ends (your own words, longest-waiting '
            "first)</h4><ul>" + "".join(rows) + "</ul></div>")


def speak(text):
    """Read aloud with the Mac's built-in voice. Runs on this Mac only."""
    subprocess.run(["killall", "say"], check=False, capture_output=True)
    if text:
        subprocess.Popen(["say", "-r", "185", text])


# ---------------------------------------------------------------------------
# 6. THE SCREEN
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Goldfish", page_icon="🐠", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
ss = st.session_state
ss.setdefault("memory", {})
ss.setdefault("before", None)
ss.setdefault("after", None)
ss.setdefault("brief", None)
ss.setdefault("found", None)
ss.setdefault("folder", default_folder())


def forget():
    ss.memory.clear()
    ss.brief = None
    ss.found = None
    for key in [k for k in ss.keys() if str(k).startswith(("tick_", "extra_"))]:
        del ss[key]                                   # meeting ticks are forgotten too
    live().stop(forget=True)                          # and so is everything it heard
    ss.pop("mac_cal", None)                           # and the calendar it read


if live().running and not ss.memory:                  # a fresh page: start clean
    live().stop(forget=True)

try:
    model_name = local_model_name()
except Exception:
    model_name = None

st.markdown('<div class="gf-hero"><div class="fish">🐠</div><h1>Goldfish</h1></div>'
            '<p class="gf-tag">Perfect recall of your notes. No memory of its own.</p>',
            unsafe_allow_html=True)
if model_name:
    st.markdown('<span class="gf-pill">● Runs only on this Mac</span>'
                '<span class="gf-pill">● Works with Wi-Fi off</span>'
                f'<span class="gf-pill blue">Model: {html.escape(model_name)}</span>',
                unsafe_allow_html=True)
else:
    st.error("LM Studio is not answering. Open LM Studio, load the model and start its "
             "server. In Terminal:  ~/.lmstudio/bin/lms server start")
    st.stop()

def folder_changed():
    forget()
    ss.before = ss.after = None


with st.sidebar:
    st.subheader("Where your notes live")
    st.text_input("Notes folder or Obsidian vault", key="folder", on_change=folder_changed,
                  help="Paste the full path of any folder on this Mac.")
    if not folder().is_dir():
        st.error("That folder does not exist on this Mac.")
    elif is_obsidian_vault():
        st.caption("🟣 Obsidian vault detected. Goldfish only reads it, and never writes to it.")
    else:
        st.caption("📁 Plain folder. Goldfish only reads it, and never writes to it.")

    st.subheader("What Goldfish may see")
    allowed = []
    for s_ in sources():
        if s_ == MAC_CAL:
            ticked = st.checkbox("📅 Calendar app on this Mac", value=False, key=f"src_{s_}",
                                 help="Reads your real calendar live. Read-only, never copied, "
                                      "never sent anywhere. Leave off when demoing with fake data.")
        else:
            ticked = st.checkbox(f"📁 {s_}", value=True, key=f"src_{s_}")
        if ticked:
            allowed.append(s_)
    st.caption("Untick a box at any time. Goldfish drops those notes straight away.")
    mac_calendar(allowed)                 # asks macOS only if that box is ticked
    if ss.get("cal_error"):
        st.warning(ss["cal_error"])

    # Un-sharing takes effect immediately, even before the next question.
    dropped = [k for k, v in ss.memory.items() if v["source"] not in allowed]
    if dropped:
        for k in dropped:
            del ss.memory[k]
        ss.brief = None
        ss.found = None
        if live().chunks:
            live().set_notes(*live_notes(ss.get("focus", "")))
        st.toast(f"Dropped {len(dropped)} notes you un-shared.")

    st.subheader("In the bowl right now")
    n = len(ss.memory)
    fish = "🐟" * min(n, 12) if n else "&nbsp;"
    label = "notes held in memory" if n else "Empty. Nothing remembered."
    st.markdown(f'<div class="gf-bowl"><div class="f">{fish}</div><div class="n">{n}</div>'
                f'<div class="l">{label}</div></div>', unsafe_allow_html=True)

    st.subheader("Check it yourself")
    blocked = socket._goldfish_blocked
    extra = f" Blocked attempts: {len(blocked)}." if blocked else ""
    st.markdown('<div class="gf-proof"><b>0</b> connections leaving this Mac<br>'
                f'<span style="opacity:.75">Goldfish blocks anything that is not this '
                f'computer.{extra}</span></div>', unsafe_allow_html=True)
    if ss.before:
        st.markdown(f'<div class="gf-proof">Folder fingerprint <b>before</b><br>'
                    f'<code>{ss.before[0]}</code> · {ss.before[1]} files</div>',
                    unsafe_allow_html=True)
    if ss.after:
        same = ss.after == ss.before
        verdict = ("✅ Identical. Nothing added, changed or copied." if same
                   else "❌ The folder changed while Goldfish was running.")
        st.markdown(f'<div class="gf-proof {"gf-ok" if same else "gf-bad"}">Folder fingerprint '
                    f'<b>after</b><br><code>{ss.after[0]}</code> · {ss.after[1]} files<br>'
                    f'{verdict}</div>', unsafe_allow_html=True)

if not folder().is_dir():
    st.error("I can't find your notes folder. Check the path on the left, or run:  "
             "python3 make_vault.py")
    st.stop()

search_model()                                        # loaded once, then instant
warm_up(lm_base(), ss["lm_model"])

tab_live, tab_brief, tab_find = st.tabs(["Live", "Prepare for a 1:1", "Find by meaning"])


def start_session(status=None):
    if ss.before is None or ss.after is not None:   # first run, or a new run after Forget
        ss.before = fingerprint(folder())
        ss.after = None
    if status:
        status.write("📂 Reading only the sources you ticked (pictures are read by the local model)...")
    load_into_memory(allowed)


def show_note(item, where):
    if item["kind"] == "screenshot" and Path(item["path"]).exists():
        left, right = st.columns(2)
        left.image(item["path"], caption="The picture on your Mac")
        right.caption("What Goldfish read from it")
        right.code(item["text"])
    else:
        st.code(item["text"])
    if is_obsidian_vault() and IS_MAC and item["path"]:
        st.button("🟣 Open in Obsidian", key=f"open_{where}_{item['path']}",
                  on_click=open_in_obsidian, args=(item["path"],))


def live_card(c, old=False):
    rows = []
    for n_, note in enumerate(c["notes"]):
        badge = '<span class="gf-new">NEWEST</span>' if len(c["notes"]) > 1 and n_ == 0 else ""
        rows.append(f'<p class="line">{badge}“{html.escape(note["line"])}”'
                    f'<span class="gf-when past">⏳ written {ago(note["when"])}</span>'
                    f'<span class="gf-chip">📄 {html.escape(note["title"])}</span></p>')
    if c["insight"]:
        top = f'<p class="say">{html.escape(c["insight"])}</p>'
    elif c["insight"] is None and not old:
        top = '<p class="wait">From your notes:</p>'
    else:
        top = ""
    style = "old" if old else ""
    return (f'<div class="gf-live {style}">{top}{"".join(rows)}'
            f'<p class="heard">You said: “{html.escape(c["heard"])}”</p></div>')


def live_view():
    L = live()
    if L.error:
        st.error(L.error)
    if L.running:
        if L.mic:
            width = min(100, int(L.level * 1500))
            st.markdown(f'<div class="gf-meter"><div style="width:{width}%"></div></div>',
                        unsafe_allow_html=True)
            st.caption(f"● {L.status} on this Mac. Sound is turned into words in memory and "
                       "then dropped. Nothing is recorded.")
        else:
            st.caption("● " + L.status)
    cards = list(L.cards)
    if not cards:
        if L.running:
            st.markdown('<div class="gf-live old"><p class="line">Just talk. When you mention '
                        "something your notes know about, it appears here.</p></div>",
                        unsafe_allow_html=True)
        return
    st.markdown(live_card(cards[0]), unsafe_allow_html=True)
    if is_obsidian_vault() and IS_MAC:
        cols = st.columns(len(cards[0]["notes"]) + 2)
        for n_, note in enumerate(n for n in cards[0]["notes"] if n["path"]):
            cols[n_].button(f"Open “{note['title'][:18]}”", key=f"lo_{cards[0]['id']}_{n_}",
                            on_click=open_in_obsidian, args=(note["path"],))
    if len(cards) > 1:
        st.markdown("".join(live_card(c, old=True) for c in cards[1:4]), unsafe_allow_html=True)


with tab_live:
    L = live()
    L.threshold = ss.get("sens", 0.38)
    events = todays_events(allowed)
    meeting_now, gap = next_meeting(events)
    if meeting_now:
        today_rest = [e for e in events if e["start"].date() == datetime.now().date()
                      and e is not meeting_now and not e["all_day"]]
        rest = " · ".join(e["start"].strftime("%H:%M") + " " + html.escape(e["title"])
                          for e in today_rest[:4])
        st.markdown(f'<div class="gf-next"><span class="o">Next on your calendar</span>'
                    f'<span class="t">{html.escape(meeting_now["title"])}</span>'
                    f'<span class="g">{meeting_now["start"].strftime("%H:%M")} · {gap}</span>'
                    f'<span class="o">{("Also today: " + rest) if rest else ""}</span></div>',
                    unsafe_allow_html=True)
    elif events:
        st.caption("Nothing else on your calendar today.")

    b1, b2, b3 = st.columns([2, 2, 3], vertical_alignment="center")
    use_mic = b3.checkbox("Use the microphone", value=True, disabled=L.running,
                          help="Switch off to type what was said instead.")
    if not L.running:
        if b1.button("Start listening", type="primary", disabled=not allowed,
                     use_container_width=True):
            with st.status("Getting ready on this Mac...", expanded=True) as status:
                start_session(status)
                ss.focus = person_in(meeting_now["title"], ss.memory) if meeting_now else ""
                status.write("Preparing your notes so the right line can surface...")
                L.set_notes(*live_notes(ss.focus))
                base, model_id = lm_base(), ss["lm_model"]
                names = sorted({i["title"] for i in ss.memory.values()
                                if len(i["title"].split()) <= 2})[:30]
                L.start(search_model(),
                        lambda p: ask_raw(base, model_id, p, max_tokens=300),
                        "Names you may hear: " + ", ".join(names) + ".", use_mic)
                status.update(label="Ready", state="complete", expanded=False)
            st.rerun()
    else:
        if b1.button("Stop listening", use_container_width=True):
            L.stop()
            st.rerun()
        if ss.get("focus"):
            b2.caption(f"Tuned to your meeting with {ss.focus}")

    if not allowed:
        st.info("Goldfish can't see anything. Tick at least one source on the left.")

    # Refresh every second only while listening or waiting for an insight.
    waiting = any(c["insight"] is None for c in L.cards)
    st.fragment(live_view, run_every=1.0 if (L.running or waiting) else None)()

    if L.running:
        with st.expander("No microphone? Type what was said", expanded=not L.mic):
            with st.form("typed", clear_on_submit=True, border=False):
                t1, t2 = st.columns([5, 1], vertical_alignment="bottom")
                typed = t1.text_input("What was said", label_visibility="collapsed",
                                      placeholder="e.g. so where are we with the vendor review")
                if t2.form_submit_button("Say it", use_container_width=True) and typed.strip():
                    L.hear(typed)
                    st.rerun()
        with st.expander("Tuning"):
            st.slider("How easily notes surface (lower = more often)", 0.20, 0.60, 0.38, 0.02,
                      key="sens")

with tab_brief:
    col_name, col_go = st.columns([3, 1], vertical_alignment="bottom")
    name = col_name.text_input("Who are you meeting?", "Priya")
    go = col_go.button("Build my brief", type="primary", disabled=not allowed,
                       use_container_width=True)
    if go:
        forget_ticks = [k for k in ss.keys() if str(k).startswith(("tick_", "extra_"))]
        for key in forget_ticks:
            del ss[key]
        with st.status("Working on this Mac...", expanded=True) as status:
            start_session(status)
            status.write(f"🔎 Searching {len(ss.memory)} notes by meaning...")
            status.write("✍️ Writing the brief with the local model...")
            draft = st.empty()
            ss.brief = (name, *build_brief(name.strip(),
                                           on_text=lambda t: draft.markdown(tidy_headings(t))))
            draft.empty()
            status.update(label="Done", state="complete", expanded=False)
        st.rerun()

    if not allowed:
        st.info("Goldfish can't see anything. Tick at least one source on the left.")

    if ss.brief:
        who, text, extra, loops = ss.brief
        if text is None:
            st.warning(f"I could not find anything about “{who}” in the notes you shared. "
                       "I have not written a brief, because I would be guessing.")
            if extra:
                score, item = extra
                st.write(f"The closest thing I have is {plain_name(item)}. It is a weak match.")
                show_note(item, "closest")
        else:
            secs = sections_of(text)
            start = [(h, l) for h, l in secs if "start here" in h.lower()]
            rest = [(h, l) for h, l in secs if "start here" not in h.lower()]
            start_words = " ".join(plain(l) for _, ls in start for l in ls
                                   if not (l.startswith("(") and "from:" not in l))
            if not start_words:        # the model skipped it: fall back to the notes themselves
                changed = [plain(l) for h, ls in rest if "changed" in h.lower() for l in ls
                           if plain(l) and not l.startswith("(")]
                start_words = changed[0] if changed else (loops[-1]["text"] if loops else "")
                if start_words:
                    start = [("Start here", [start_words])]

            head, c1, c2, c3 = st.columns([4, 2, 2, 2], vertical_alignment="center")
            head.markdown(f"### Your 1:1 with {html.escape(who)}")
            focus = c1.toggle("Focus view", value=True,
                              help="Shows only what matters most. Switch off to see everything.")
            meeting = c2.toggle("Meeting mode",
                                help="A tick-list to use during the meeting, then follow-ups to copy.")
            if IS_MAC:
                if c3.button("🔊 Read it to me", use_container_width=True):
                    said = ("Start here. " + start_words) if start_words else \
                        "Your notes do not give one clear place to start."
                    if loops:
                        said += f" You have {len(loops)} loose ends. " + ". ".join(
                            l["text"] for l in loops[:3])
                    speak(said)

            if not secs:
                st.markdown(text)
            elif meeting:
                # ---- one list to tick through, nothing else on screen ----
                points = []
                for h, ls in start + [x for x in rest if "promised" in x[0].lower()
                                      or "changed" in x[0].lower()]:
                    points += [plain(l) for l in ls if plain(l) and not l.startswith("(")]
                points += [l["text"] for l in loops if l["kind"] == "task"]
                points = list(dict.fromkeys(points))            # drop exact repeats
                done = 0
                st.caption("Tick each one as you cover it. Ticks live in memory only.")
                for n_, point in enumerate(points):
                    if st.checkbox(point, key=f"tick_{n_}"):
                        done += 1
                st.progress(done / len(points) if points else 0.0,
                            text=f"{done} of {len(points)} covered")
                new = st.text_area("Anything new you just agreed? One per line.", key="extra_new",
                                   height=90)
                left = [p for n_, p in enumerate(points) if not ss.get(f"tick_{n_}")]
                left += [l.strip() for l in new.splitlines() if l.strip()]
                if left:
                    st.markdown("**Follow-ups to paste into your notes**")
                    st.caption("Goldfish never writes to your notes. Copy this and paste it "
                               "yourself, so you stay in charge of what is kept.")
                    today = datetime.now().strftime("%d %b %Y")
                    st.code(f"## Follow-ups: 1:1 with {who}, {today}\n"
                            + "\n".join(f"- [ ] {p}" for p in left), language="markdown")
                elif points:
                    st.success("Everything covered. Nothing to carry over.")
            else:
                top = "".join(card(h, l) for h, l in start) + loops_card(loops)
                key = lambda h: "coming up" in h.lower() or "changed" in h.lower()
                top += "".join(card(h, l) for h, l in rest if key(h))
                others = "".join(card(h, l) for h, l in rest if not key(h))
                st.markdown(top or others, unsafe_allow_html=True)
                if top and others:
                    if focus:
                        with st.expander("Show the full picture"):
                            st.markdown(others, unsafe_allow_html=True)
                    else:
                        st.markdown(others, unsafe_allow_html=True)

            missing = [s_ for s_ in sources() if s_ not in allowed]
            if missing:
                st.info("Not used, because you switched them off: " + ", ".join(missing))
            if not meeting:
                st.markdown("#### Where this came from")
                st.caption("Every line above names its note. Open any note to check it yourself.")
                for score, item in extra:
                    strength = ("mentions " + who + " by name" if score <= -2 else
                                "linked from the note about " + who if score < 0 else
                                "strong match" if score > 0.45 else
                                "medium match" if score > WEAK_MATCH else "weak match")
                    with st.expander(f"{icon_for(item)} {plain_name(item)} · {strength}"):
                        show_note(item, "brief")

with tab_find:
    col_q, col_f = st.columns([3, 1], vertical_alignment="bottom")
    q = col_q.text_input("Describe what you are looking for", "development goals")
    if col_f.button("Find", disabled=not allowed, use_container_width=True):
        with st.status("Working on this Mac...", expanded=False) as status:
            start_session(status)
            status.update(label="Done", state="complete")
        ss.found = search(q, top=3)
    if ss.found is not None:
        hits = ss.found
        if not hits or hits[0][0] < WEAK_MATCH:
            st.warning("Nothing in your notes clearly matches that.")
            if hits:
                st.write(f"Closest match: {plain_name(hits[0][1])}")
                show_note(hits[0][1], "findclosest")
        else:
            st.caption("Matched by meaning, not by the words you typed.")
            for score, item in hits:
                if score >= WEAK_MATCH:
                    st.markdown(f"**{icon_for(item)} {plain_name(item)}** · match {score:.2f}")
                    show_note(item, "find")

st.divider()
col_a, col_b = st.columns([1, 3], vertical_alignment="center")
if col_a.button("🐠 Forget everything", use_container_width=True):
    forget()
    if ss.before:
        ss.after = fingerprint(folder())
    st.rerun()
if ss.after and not ss.memory:
    col_b.success("Bowl emptied. Your notes are exactly where they were, and nowhere else. "
                  "Compare the two fingerprints on the left.")
else:
    col_b.caption("Empties the bowl and re-checks that your notes folder is untouched.")
