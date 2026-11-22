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
6. [Repository Structure](#repository-structure)
7. [Privacy](#privacy)
8. [Future enhancements](#future-enhancements)
9. [The team](#the-team)
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
 
**Status key:** ✅ working · 🟡 UI built on mock data, backend in progress · 🚧 planned for this hackathon · ⏳ roadmap
 
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
| Works with several note types: markdown, calendar (`.ics`), email (`.eml`) | Bonus criterion: more than one kind of notes | 🚧 |
| Works with Wi-Fi off | Proof for "on device" | 🚧 |
 
### Should-have (P1)
 
| Feature | Status |
|---|---|
| Capture by typing, then editable extracted fields, then explicit confirm, then append to the user's own file | 🚧 |
| Screenshot text recognition (OCR), with low-confidence text marked "Check this" | 🚧 |
| Open the source note or reveal it in its folder (a click, never on hover) | 🚧 |
| Local voice capture (offline speech-to-text) with a visible microphone state | 🚧 if stable |
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
 
**Agentic Pipeline**
1. **Scan and parse:** each document gets an ID, folder, type, text and a date (taken from the content first, then the filename, then the file's modified time).
2. **Find:** match people by alias and email, then rank notes by keyword and recency.
3. **Extract:** turn each note into schema-constrained JSON, where every item carries a **verbatim quote**.
4. **Verify:** the quote must exist in the source. Relative dates ("Tuesday") are resolved against the *note's* date.
5. **Assemble:** deduplicate, detect conflicts, compute staleness, and set "no later note shows this done".
The human is the final step: review, edit, accept or decline.
 
---
 
## Getting Started
 
### Prerequisites
 
- [Node.js](https://nodejs.org/) 20 or later, and npm
- Git
- A Mac with an Apple chip (M1 or newer). The Live tab needs this.
- About 6 GB of free disk space for the models.
- Python 3.10 or newer (most Macs already have it).
-  [LM Studio](https://lmstudio.ai) (free).
-  Optional: [Obsidian](https://obsidian.md) (free), to browse the demo notes.

You need Wi-Fi for the setup. After that, Goldfish runs with Wi-Fi off.
### Run the frontend (mock mode)
 
```bash
# 1. Clone
git clone https://github.com/ZakiyaY/goldfish-app.git
cd goldfish-app
 
# 2. Install and run the frontend
cd frontend
npm install
npm run dev
```
 
Open the local address printed in the terminal (Vite's default is `http://localhost:5173`, but check the output).

### Run the model

### Python Installation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

### Download the two small models (one time only)

```bash
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); print('SEARCH MODEL READY')"
python3 -c "from huggingface_hub import snapshot_download; snapshot_download('mlx-community/whisper-small-mlx'); print('LISTENING MODEL READY')"
```

> **What you should see:** `SEARCH MODEL READY`, then `LISTENING MODEL READY`.
### Demo Notes Creation
```bash
python3 make_vault.py
```

> **What you should see:** "Done. 12 new notes, calendar refreshed".

This creates `GoldfishVault`, a folder of **invented** manager notes. Never use real notes
for a demo.

 
## Repository Structure
 
_Current structure; it will evolve._
 
```
goldfish-app/
├── README.md          # you are here
├── AGENTS.md          # rules for AI coding assistants used on this project
├── frontend/          # React + Vite + TypeScript UI
│   └── src/
│       ├── api/       # typed client, mock client, HTTP client
│       ├── components/
│       ├── hooks/
│       └── ...
├── backend/           # FastAPI service and the pipeline (scan, find, extract, verify, assemble)
├── sample-notes/      # fictional manager data used for development and the demo
├── eval/              # test cases with known answers, and the evaluation runner
└── docs/              # architecture notes, privacy claims, decisions, demo script
```
 
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
 
### AI Usage
 
- **While building:** AI-assisted development tools (including Lovable for the initial interface) helped scaffold code. All sample data is fictional, and we reviewed the logic that touches files, network and extraction by hand.
- **While running:** only **local open-source models**. No cloud AI service sees any note.
---
 
## Future Enhancements
 
_To be detailed at the end of project review. Candidate ideas:_
 
- Approved connectors for OneNote, Outlook and Teams, synced to the device so the on-device rule still holds
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
 
| Name | Contact |
|---|---|
| **Zakiya** | Zakiyaa01@hotmail.com |
| **Kawther** |  |
| **Emma** | |
| **Sophie** | |
 
---
 
## Acknowledgements
 Challenge set by **Pfizer's OSS AI Studio** and **Newpage Solutions**.
 


