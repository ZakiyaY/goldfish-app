# 🐠 Goldfish

**Perfect recall of your notes. No memory of its own.**

Goldfish is a private assistant for managers with scattered notes. It reads the notes
on your own Mac, helps you in the moment, then forgets everything. Nothing leaves the
device and nothing is kept.

Built for the Pfizer AI Studio x Newpage hackathon, "Second Brain for Managers".

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

## What it can do

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

## What you need

- [ ] A Mac with an Apple chip (M1 or newer). The Live tab needs this.
- [ ] About 6 GB of free disk space for the models.
- [ ] Python 3.10 or newer (most Macs already have it).
- [ ] [LM Studio](https://lmstudio.ai) (free).
- [ ] Optional: [Obsidian](https://obsidian.md) (free), to browse the demo notes.

You need Wi-Fi for the setup. After that, Goldfish runs with Wi-Fi off.

---

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

### The models

| Job | Hugging Face task | Model |
|---|---|---|
| Find notes by meaning | Sentence Similarity | `sentence-transformers/all-MiniLM-L6-v2` |
| Write the brief, read screenshots | Image-Text-to-Text | `mlx-community/Qwen3.5-4B-MLX-4bit` (run by LM Studio) |
| Turn speech into words | Automatic Speech Recognition | `mlx-community/whisper-small-mlx` |

---

## Privacy: how you can check it yourself

| Promise | How Goldfish shows it |
|---|---|
| **Nothing leaves the Mac** | Works with Wi-Fi off. Goldfish also blocks any connection that is not to this computer, and counts the attempts on screen. |
| **Nothing is kept** | A fingerprint of your notes folder is taken before and after. If they match, nothing was added, changed or copied. |
| **You choose what it sees** | Tick boxes per folder. Untick one and those notes are dropped from memory straight away. |
| **Speech is not recorded** | Sound is turned into words in memory and then dropped. |
| **It never writes to your notes** | Follow-ups are given to you to copy and paste yourself. |

One more check, for LM Studio. After using Goldfish, run:

```bash
grep -ril "priya" ~/.lmstudio
```

> **What you should see:** nothing printed. That means LM Studio kept no copy of the notes.
> If it lists files, turn off prompt logging in LM Studio's server settings and delete them.

**The fish bowl** on the left makes this visible. Fish are the notes held in memory right
now. Forget everything empties the bowl.

---

## How it meets the judging criteria

| Criterion | What Goldfish does |
|---|---|
| Insight & problem understanding | One real moment: a manager in or just before a 1:1 who cannot remember what they promised or what has changed. |
| Creative use of AI & design | The Live tab has no prompt. It handles initials ("P" for Priya), undated notes, and newer notes that overrule older ones. |
| Working end to end | Runs on a laptop with invented notes. Four kinds of content: notes, to-dos, a screenshot and a calendar. |
| Trust & explainability | Loose ends are word-for-word quotes. Every line names its note. It says when it cannot find something. |
| Knowledge stays yours | Wi-Fi off, connection blocker, folder tick boxes, fingerprint check, Forget. |

---

## If something goes wrong

| What you see | What to do |
|---|---|
| `zsh: command not found: streamlit` | That Terminal tab is missing the toolbox. Run `cd ~/Desktop/goldfish` then `source venv/bin/activate`, and try again. |
| Red box: "LM Studio is not answering" | Run `~/.lmstudio/bin/lms server start` in another Terminal tab, then refresh the page. |
| The blue pill names a model that is not Qwen | Load Qwen3.5 4B in LM Studio, then refresh the page. |
| "We couldn't connect to huggingface.co" | A model from Level 4 did not finish downloading. Turn Wi-Fi on, run Level 4 again, turn Wi-Fi off. |
| The page looks like an old version | Press Ctrl + C in the Terminal tab running Goldfish, start it again, then press Cmd + Shift + R in the browser. |
| Live shows "I could not open the microphone" | Open System Settings > Privacy & Security > Microphone and switch Terminal on. |
| Live never surfaces anything, or surfaces too much | Open **Tuning** on the Live tab and move the slider. |
| The address bar says `localhost:8502` | An older copy is still running. Press Ctrl + C in the other Terminal tabs. |

---

## What is in this repo

| File | What it is |
|---|---|
| `app.py` | The whole app. |
| `make_vault.py` | Creates the demo Obsidian vault and a fake calendar for today. |
| `make_notes.py` | Creates a simpler plain-folder version of the demo notes (optional). |
| `requirements.txt` | The Python packages to install. |

Not in the repo, on purpose: the `venv` folder, the generated `GoldfishVault` folder, and
any real notes.

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

## Team

Add your names here.
