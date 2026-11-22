# 🐟 Goldfish
 
**Perfect recall of your notes. No memory of its own.**

Goldfish is a private assistant for managers with scattered notes. It reads the notes
on your own Mac, helps you in the moment, then forgets everything. Nothing leaves the
device and nothing is kept.
 
---
 
## Contents
 
1. [The Challenge](#the-challenge)
2. [Our Solution](#our-solution)
3. [Features](#features)
4. [Tech Stack](#tech-stack)
5. [Getting Started](#getting-started)
6. [Privacy](#privacy)
7. [Future enhancements](#future-enhancements)
8. [The team](#the-team)
---
 
## The Challenge
 
A manager's notes are scattered: meeting notes, action items, saved links, screenshots, reminders and half-written updates, spread across their own device. They are also some of the most sensitive information in a company, so **the value and the risk come from the same place.**
 
Goldfish is a prototype assistant that helps a manager use what they already know, under **one rule: your knowledge stays yours**.
 
- **On device:** nothing the assistant reads leaves the device.
- **No copies:** the assistant keeps no copy of its own. When it has finished helping, the knowledge is exactly where it was.
Where notes let managers down today:
 
| Moment | What goes wrong |
|---|---|
| **Capture** | Notes are jotted wherever is closest and rarely looked at again |
| **Find** | You know you wrote it down, but not where, when, or in what words |
| **Connect** | A decision in one meeting and its context in another never meet |
| **Trust** | The more an assistant sees, the less comfortable it feels |
 
---

## The 30-second version

- **The problem:** you are about to walk into a 1:1. What you know about that person is
  spread across meeting notes, a to-do list, a chat screenshot and your calendar. You
  forget what you promised, and you can't tell how long ago you promised it.
- **What Goldfish does:** it finds the right note by meaning, joins notes written weeks
  apart, spots when a newer note overrules an older one, and tells you where every line
  came from.
- **Why it is safe:** it runs on local AI models only. It never saves a copy, and you
  can check that yourself on screen.

---

## Our Solution
 
Goldfish turns the manager's existing files into a short, **sourced brief** for the next meeting. 
 
1. **Reads in place.** The manager picks which folders Goldfish may read (e.g. `1-1s`, `Meetings`, `Inbox`). Sensitive folders such as `HR-private` are off by default.
2. **Starts from the calendar.** The day's meetings come from a local calendar file, so the manager recognises their next meeting instead of having to ask.
3. **Builds a brief.** Open commitments, decisions and questions are pulled out of the notes. Every line carries a **source chip** showing the exact quote it came from.
4. **Is honest about doubt.** Each item is labelled **Clear**, **Check this** or **Not found**, with a one-line reason. Old notes are flagged as stale, and notes that disagree are flagged as conflicts.
5. **Keeps the manager in control.** Toggle a folder and the brief updates immediately. Leave a source out, or wipe the session. Nothing is saved without explicit confirmation.
6. **Keeps nothing.** The assistant works from memory for one session. A live receipt shows what was read and what was kept.
### Principles
 
- **The user's files are the source of truth. The assistant is stateless.** Everything it knows lives in RAM for one session.
- **Extract, don't interpret.** Goldfish structures what is written. It does not infer intent, sentiment or performance, and it does not invent.
- **Neutral wording.** We say *"No note shows you told her yet"*, not *"You haven't told her"*, because the absence of a note isn't proof. We say *"Two notes mention 9 Dec"*, not *"may clash"*, because the code detects the overlap and shows both sources, and the judgement stays with the manager.
---

## Key Features

| Tab | What it does |
|---|---|
| **Live** | Listens while you talk. When you mention something your notes cover, the exact line appears with how long ago you wrote it, plus a one-sentence insight. No typing. |
| **Prepare for a 1:1** | Type a name and get a short brief: Start here, Loose ends, What has changed, Dates coming up. Includes Meeting mode (a tick-list) and Read it to me (your Mac speaks it). |
| **Find by meaning** | Describe what you want. A search for "development goals" finds a note that says "keen on design stuff". |

Other things worth knowing:

- Works on a plain folder or an **Obsidian vault**, and can open any source note in Obsidian.
- Reads notes, to-dos, **screenshots** and **calendar** files.
- Can read the Mac's Calendar app live (off by default; you tick it on).
- Says so when it cannot find something, and does not guess.

---
 
## Features
 
**Status key:** ✅ working · 🟡 UI built on mock data, backend in progress · 🚧 Roadmap
 
### MVP (P0)
 
| Feature | Why it matters | Status |
|---|---|---|
| Folder toggles with live effect (turn off `HR-private` and its items disappear) | Knowledge Stays Yours: the user chooses what the assistant sees and can change their mind | ✅ |
| Day calendar from a local `.ics` file, with meeting picker | The calendar is the trigger for the brief | ✅ |
| Brief for a meeting, with **source chips** and the exact quote on hover or focus | Trust and traceability | ✅ |
| **Clear / Check this / Not found** states, each with a one-line reason | Honest uncertainty, without made-up percentages | 🟡 |
| Stale and conflict flags | Messy, out-of-date notes are normal | ✅ |
| Honest "not found" when asked about something the notes don't cover | Resists guessing | 🟡 |
| Receipt: files read, bytes sent off device, items kept | A claim the user can check, not just read | 🟡 UI · 🚧 measured by backend |
| "Wipe session now" | User control | ✅ |
| Works with several note types: markdown, calendar (`.ics`), email (`.eml`) | Bonus criterion: more than one kind of notes | ✅ |
| Works with Wi-Fi off | Proof for "on device" | ✅ |
 
### Should-have (P1)
 
| Feature | Status |
|---|---|
| Capture by typing, then editable extracted fields, then explicit confirm, then append to the user's own file | ✅ |
| Screenshot text recognition (OCR), with low-confidence text marked "Check this" | 🚧 |
| Open the source note or reveal it in its folder (a click, never on hover) | ✅ |
| Local voice capture (offline speech-to-text) with a visible microphone state | ✅ |
| "Leave this source out" and "Wrong person?" corrections | 🚧 |
 
### Nice-to-have (P2 / roadmap)
 
Transcript (`.vtt`) support · "Same as last time" taken from the previous 1:1 note · voice-guided mode with play and pause · simple onboarding animation · light/dark and calm themes · OS-calendar adapter · multilingual notes.
 
### Deliberately out of scope
 
Task breaking, day rescheduling and audio recaps. They are well covered by existing productivity tools and pull away from the *scattered notes* moment.
 
---
 
## Tech Stack
 
| Layer | Choice | Why |
|---|---|---|
| Frontend | React, Vite, TypeScript, Tailwind CSS | Fast to build, typed, and suits a single-page app |
| Backend | FastAPI (Python)| Python has the parsers, speech-to-text and OCR libraries |
| Storage | **None.** In-memory only | Any on-disk database is a copy |
| Speech (P1) | faster-whisper, running locally | Browser speech APIs are often cloud-backed, so we avoid them |
| Testing | pytest with a JSONL evaluation set | Accuracy is measured, not asserted |

### The models

| Job | Hugging Face task | Model |
|---|---|---|
| Find notes by meaning | Sentence Similarity | `sentence-transformers/all-MiniLM-L6-v2` |
| Write the brief, read screenshots | Image-Text-to-Text | `mlx-community/Qwen3.5-4B-MLX-4bit` (run by LM Studio) |
| Turn speech into words | Automatic Speech Recognition | `mlx-community/whisper-small-mlx` |
 
---
 
## Getting Started
 
### Prerequisites
- Git
- A Mac with an Apple chip (M1 or newer). The Live tab needs this.
- About 6 GB of free disk space for the models.
- Python 3.10 or newer (most Macs already have it).
-  [LM Studio](https://lmstudio.ai) (free).
-  Optional: [Obsidian](https://obsidian.md) (free), to browse the demo notes.

You need Wi-Fi for the setup. After that, Goldfish runs with Wi-Fi off.

## Set up (about 20 minutes, mostly waiting for downloads)

Do the levels in order. Each one ends with a **What you should see** check.

### Level 1: Get the writing model

- [ ] Install and open **LM Studio**.
- [ ] Search for `Qwen3.5-4B` and download the **MLX 4bit** version.
- [ ] Open **Terminal** (press Cmd + Space, type "Terminal", press Enter) and paste:

```bash
~/.lmstudio/bin/lms server start
```

> **What you should see:** "Success! Server is now running on port 1234" (or 1235).

### Level 2: Get the code

- [ ] In Terminal, paste these lines one at a time. Replace `REPO-LINK` with this repo's link.

```bash
cd ~/Desktop
git clone REPO-LINK goldfish
cd goldfish
```

> **What you should see:** a new `goldfish` folder on your Desktop containing `app.py`.

No git? Click the green **Code** button on GitHub, choose **Download ZIP**, unzip it, and
rename the folder to `goldfish` on your Desktop.

### Level 3: Install the Python parts

```bash
cd ~/Desktop/goldfish
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> **What you should see:** `(venv)` at the start of the Terminal line, and a final line
> starting "Successfully installed".

### Level 4: Download the two small models (one time only)

```bash
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); print('SEARCH MODEL READY')"
python3 -c "from huggingface_hub import snapshot_download; snapshot_download('mlx-community/whisper-small-mlx'); print('LISTENING MODEL READY')"
```

> **What you should see:** `SEARCH MODEL READY`, then `LISTENING MODEL READY`.

### Level 5: Create the demo notes

```bash
python3 make_vault.py
```

> **What you should see:** "Done. 12 new notes, calendar refreshed".

This creates `GoldfishVault`, a folder of **invented** manager notes. Never use real notes
for a demo.

### Level 6: Start Goldfish

```bash
streamlit run app.py --browser.gatherUsageStats false --client.toolbarMode minimal
```

- [ ] If it asks for an email address, leave it blank and press Enter.

> **What you should see:** a browser page titled Goldfish, a blue pill saying
> **Model: qwen…**, and "Next on your calendar: 1:1 Priya".

- [ ] Now turn Wi-Fi **off**. Everything below works without it.

---

## Starting it again another day

You only do the set-up once. After that it is five lines:

```bash
~/.lmstudio/bin/lms server start
cd ~/Desktop/goldfish
source venv/bin/activate
python3 make_vault.py
streamlit run app.py --browser.gatherUsageStats false --client.toolbarMode minimal
```

`make_vault.py` refreshes the fake calendar so the next meeting is always 15 minutes away.
It never overwrites notes you have edited.

---

## Try it: a five-minute tour

- [ ] **Live, by typing.** On the Live tab, untick **Use the microphone**, click
      **Start listening**, type `so where are we with the vendor review`, click **Say it**.

> **What you should see:** a card quoting a line from the notes, then a bold sentence above it.

- [ ] **Live, by voice.** Click **Stop listening**, tick **Use the microphone**, click
      **Start listening**. Click **Allow** if the Mac asks about the microphone. Say:
      "Priya wants to shadow the UX team."

> **What you should see:** a green bar that moves as you speak, then the "keen on design
> stuff" line after you pause.

- [ ] **The brief.** Open **Prepare for a 1:1** and click **Build my brief**.

> **What you should see:** a green Start here card, Loose ends, What has changed, and Dates
> coming up. "What has changed" says Priya is no longer leading the vendor review.

- [ ] **Check a source.** Open a row under **Where this came from**.

> **What you should see:** the original note text.

- [ ] **Honesty.** Change the name to `Zebedee` and build again.

> **What you should see:** a yellow box saying nothing was found and no brief was written.

- [ ] **Control.** Build for Priya again, then untick **People** on the left.

> **What you should see:** the number of fish in the bowl drops.

- [ ] **Forget.** Click **Forget everything**.

> **What you should see:** an empty bowl and a green box saying the folder is identical.

---

## How it works

1. **You choose** which folders Goldfish may see, with tick boxes.
2. **It reads** those files into memory only. A local vision model reads screenshots.
3. **It matches by meaning.** Every note line is turned into a list of numbers that
   captures its meaning. What you say or type gets the same treatment, and the closest
   lines surface. No text is being written at this step, which is why it is fast.
4. **A local model writes one sentence** (Live) or a short brief (1:1 tab), using only
   those lines, and trusting the newest note when two disagree.
5. **Forget** wipes everything from memory and re-checks that your folder is untouched.

---

## Privacy
 
| Claim | How Goldfish shows it |
|---|---|
| **Nothing leaves the device** | Works with Wi-Fi off. Goldfish also blocks any connection that is not to this computer, and counts the attempts on screen. |
| **Nothing is kept** | A fingerprint of your notes folder is taken before and after. If they match, nothing was added, changed or copied. |
| **You choose what it sees** | Tick boxes per folder. Untick one and those notes are dropped from memory straight away. |
| **Speech is not recorded** | Sound is turned into words in memory and then dropped. |
| **It never writes to your notes** | Follow-ups are given to you to copy and paste yourself. |
| **Wipe session now** | Clears everything the assistant held in memory. |

 
**Safeguards by design:**

- Only folders the user enabled are ever opened, and this is enforced by the backend, not just the interface.
- No database, no vector store and no logs of note content. "Save" means appending to the user's own file, after explicit confirmation.
- Emails and notes are treated as **untrusted text** (to resist prompt injection). The model can't take actions and its output is schema-locked.
- Saved links are never fetched, because fetching would send data off the device.
 
---
## Mapping to the Criteria

| Criterion | What Goldfish does |
|---|---|
| Insight & problem understanding | One real moment: a manager in or just before a 1:1 who cannot remember what they promised or what has changed. |
| Creative use of AI & design | The Live tab has no prompt. It handles initials ("P" for Priya), undated notes, and newer notes that overrule older ones. |
| Working end to end | Runs on a laptop with invented notes. Four kinds of content: notes, to-dos, a screenshot and a calendar. |
| Trust & explainability | Loose ends are word-for-word quotes. Every line names its note. It says when it cannot find something. |
| Knowledge stays yours | Wi-Fi off, connection blocker, folder tick boxes, fingerprint check, Forget. |

---

## Known limits

- The Live tab and Read it to me need a Mac with an Apple chip.
- Screenshots are re-read on every fresh start, which takes a few seconds. Caching them
  would mean keeping a copy, so Goldfish does not.
- Exported calendar files show repeating events once. The live Calendar app connection
  handles repeats.
- Answers come from a small local model. It is told to use only your notes and to name
  its source, but always open the source note for anything important.

---
 
## Future Enhancements
- Optional, encrypted, user-owned cache, off by default, with retention limits
- Calendar adapters for operating-system calendars
- Transcript and meeting-recording support
- "Same as last time" templates derived from the user's own previous notes
- Personalised categories stored in a plain file the user owns
- Voice-guided mode and onboarding animations
- Safety-event sign-posting configured with an organisation's own process
- Larger evaluation sets, and testing with real managers
---
 
## The Team
 
University of Bristol · AI Studio × Newpage hackathon, 2026
 
| Name |
|---|
| **Zakiya** | 
| **Kawther** |  
| **Emma** | 
| **Sophie** | 
 
---
 
## Acknowledgements
 Challenge set by **Pfizer's OSS AI Studio** and **Newpage Solutions**.
 


