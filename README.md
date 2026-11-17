# 🐟 Goldfish
 
**Helpful without remembering.** Goldfish gets a manager ready for their day from the notes already on their laptop. It shows where every line came from, says "not found" instead of guessing, and keeps nothing.
 
> Built for the **Pfizer OSS AI Studio × Newpage Solutions** hackathon challenge (University of Bristol, November 2026).
> All data in this repository is **fictional**. No real notes, people or calendars are used.
 
---
 
## Contents
 
1. [The challenge](#the-challenge)
2. [Our solution](#our-solution)
3. [Features](#features)
4. [Tech stack and architecture](#tech-stack-and-architecture)
5. [Getting started](#getting-started)
6. [Repository structure](#repository-structure)
7. [Privacy: what we claim and how you can check](#privacy-what-we-claim-and-how-you-can-check)
8. [Design principles and evidence](#design-principles-and-evidence)
9. [Future enhancements](#future-enhancements)
10. [The team](#the-team)
---
 
## The challenge
 
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
 
## Our solution
 
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
 
## Features
 
**Status key:** ✅ working · 🟡 UI built on mock data, backend in progress · 🚧 planned for this hackathon · ⏳ roadmap
 
### MVP (P0)
 
| Feature | Why it matters | Status |
|---|---|---|
| Folder toggles with live effect (turn off `HR-private` and its items disappear) | Knowledge Stays Yours: the user chooses what the assistant sees and can change their mind | 🟡 |
| Day calendar from a local `.ics` file, with meeting picker | The calendar is the trigger for the brief | 🟡 |
| Brief for a meeting, with **source chips** and the exact quote on hover or focus | Trust and traceability | 🟡 |
| **Clear / Check this / Not found** states, each with a one-line reason | Honest uncertainty, without made-up percentages | 🟡 |
| Stale and conflict flags | Messy, out-of-date notes are normal | 🟡 |
| Honest "not found" when asked about something the notes don't cover | Resists guessing | 🟡 |
| Receipt: files read, bytes sent off device, items kept | A claim the user can check, not just read | 🟡 UI · 🚧 measured by backend |
| "Wipe session now" | User control | 🟡 |
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
 
## Tech stack and architecture
 
| Layer | Choice | Why |
|---|---|---|
| Frontend | React, Vite, TypeScript, Tailwind CSS | Fast to build, typed, and suits a single-page app |
| Backend | FastAPI (Python), bound to `127.0.0.1` only | Python has the parsers, speech-to-text and OCR libraries |
| Language model | Small open model run locally through Ollama | Nothing leaves the laptop, and no API keys are needed (the sponsors couldn't provide tokens, so we use open-source models) |
| Retrieval | Aliases + keyword search, built **in memory** per session | A persistent index would be a copy |
| Storage | **None.** In-memory only | Any on-disk database is a copy |
| Speech (P1) | faster-whisper, running locally | Browser speech APIs are often cloud-backed, so we avoid them |
| OCR (P1) | Tesseract or similar, local | Screenshots to text on device |
| Testing | pytest with a JSONL evaluation set | Accuracy is measured, not asserted |
 
** Agentic Pipeline**
1. **Scan and parse:** each document gets an ID, folder, type, text and a date (taken from the content first, then the filename, then the file's modified time).
2. **Find:** match people by alias and email, then rank notes by keyword and recency.
3. **Extract:** turn each note into schema-constrained JSON, where every item carries a **verbatim quote**.
4. **Verify:** the quote must exist in the source. Relative dates ("Tuesday") are resolved against the *note's* date.
5. **Assemble:** deduplicate, detect conflicts, compute staleness, and set "no later note shows this done".
The human is the final step: review, edit, accept or decline.
 
---
 
## Getting started
 
### Prerequisites
 
- [Node.js](https://nodejs.org/) 20 or later, and npm
- Git
- _Backend (when enabled):_ Python 3.11 or later and [Ollama](https://ollama.com/)
### Run the frontend (mock mode)
 
```bash
# 1. Clone
git clone <https://github.com/ZakiyaY/goldfish-app.git>
cd goldfish-app
 
# 2. Install and run the frontend
cd frontend
npm install
npm run dev
```
 
Open the local address printed in the terminal (Vite's default is `http://localhost:5173`, but check the output).
 
### Sample data
 
`sample-notes/` is our fictional manager's laptop: notes, a calendar export, emails and screenshots, with **deliberate traps** (a stale note, two notes that disagree, an ambiguous name, a fact that exists only in `HR-private`, and a question the notes cannot answer) so we can test honesty.
 
---
 
## Repository structure
 
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
 
## Privacy: what we claim and how you can check
 
**Our claim:** while Goldfish is running, the notes it reads stay on the device, and the assistant keeps no copy of them of its own.
 
**How a user can check for themselves:**
 
| Check | What to look for |
|---|---|
| **Wi-Fi off** | The app still works end to end |
| **Folder toggle** | Turn off a folder. Its content disappears from the brief, and the receipt shows the change |
| **Receipt** | "Read N files. Left this device: 0 bytes. Kept: nothing." These are **counted by the backend**, not typed in by hand |
| **Remembers: nothing** | There is no memory store to inspect |
| **Wipe session now** | Clears everything the assistant held in memory |
 
**Safeguards by design:**

- Only folders the user enabled are ever opened, and this is enforced by the backend, not just the interface.
- No database, no vector store and no logs of note content. "Save" means appending to the user's own file, after explicit confirmation.
- Emails and notes are treated as **untrusted text** (to resist prompt injection). The model can't take actions and its output is schema-locked.
- Saved links are never fetched, because fetching would send data off the device.
 
---
 
### How we used AI
 
- **While building:** AI-assisted development tools (including Lovable for the initial interface and coding assistants) helped scaffold code. All sample data is fictional, and we reviewed the logic that touches files, network and extraction by hand.
- **While running:** only **local open-source models**. No cloud AI service sees any note.
---
 
## Future enhancements
 
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
 
## The team
 
University of Bristol · AI Studio × Newpage hackathon, 2026
 
| Name | Focus |
|---|---|
| **Zakiya** | |
| **Kawther** | |
| **Emma** | |
| **Sophie** | |
 
---
 
## Acknowledgements
 Challenge set by **Pfizer's OSS AI Studio** and **Newpage Solutions**.
 
