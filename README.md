# study-kit

A small desktop app for student life: track deadlines, plan exams, and handle PDFs (merge, split, rotate, extract text, even from scans). It opens as a simple window, so you can do everything with a few clicks, with no terminal needed. There is also a command-line tool for the same features.

Works on **Windows** and **macOS** (Apple Silicon).

![Deadlines with summary cards, dark theme](docs/screenshot-1.jpg)

![Archive view, light theme](docs/screenshot-4.jpg)

![Archive view, dark theme](docs/screenshot-2.jpg)

![Exam study plan, light theme](docs/screenshot-3.jpg)

![PDF tools tab](docs/screenshot-5.jpg)

## Features

**Deadlines**

- Add deadlines with a title, a subject, and a calendar date picker
- Subjects are remembered and offered in a dropdown
- Search by text and filter by subject
- Summary cards show how many deadlines are overdue, due in the next 7 days, and finished
- Colors show urgency: red when overdue, orange when due within 3 days
- Edit any deadline by double-clicking it
- Mark deadlines as done, then view them in the archive or restore them

**Exam planner**

- Add an exam with its date and a list of topics
- Get a day-by-day study plan that spreads the topics evenly over the days left

**PDF tools**

- **Merge** several PDFs into one, and change their order before saving
- **Split**: keep only the pages you choose, for example `1-3, 5`
- **Rotate** all pages, or only some, by 90, 180, or 270 degrees
- **Extract text** into a `.txt` file. For scans and slides saved as images, tick **OCR** to read the text inside pictures (English, Korean, Russian). See [OCR](#ocr-for-scanned-pdfs)
- Clear error messages for missing files, bad page ranges, and password-protected PDFs

**Backup and calendar**

- **File > Export backup / Import backup**: save all deadlines and exams to a file and load them back. You can merge with your current data or replace it (a copy of the old data is kept)
- **File > Export calendar (.ics)**: open your deadlines and exams in Google Calendar, Outlook, or Apple Calendar

**App**

- Light, dark, or follow-the-system theme
- Rounded buttons, and a window that opens large enough to show every button
- Sharp on high-DPI screens, and the window resizes to fit
- Daily pop-up reminder for deadlines that are overdue, due today, or due tomorrow (can be turned off)
- "Start with Windows" checkbox to open the app at login (Windows only for now)

## Download

Go to the [Releases page](https://github.com/Plagudoktor0/study-kit/releases) and download the file for your system.

### Windows

1. Download the Windows `.zip` file and unzip it.
2. Double-click `study-kit.exe`.
3. Windows may show **"Windows protected your PC"**. Click **More info**, then **Run anyway**. This happens because the app isn't code-signed. The full source code is in this repository.

Your data is stored only on your computer, in `C:\Users\<your name>\.studykit\data.json`.

**To uninstall:** untick **Start with Windows** in the app, then delete `study-kit.exe` (or the unzipped folder) and the `.studykit` folder.

### macOS (experimental)

The macOS app is built automatically by GitHub Actions and has not been tested on many Macs yet. If something doesn't work, please [open an issue](https://github.com/Plagudoktor0/study-kit/issues).

1. Download `study-kit-macos.zip` and unzip it.
2. Drag `study-kit.app` into your **Applications** folder.
3. The first time, **right-click** the app, choose **Open**, then click **Open** again. This is needed because the app isn't signed by Apple.
4. If macOS says the app is "damaged", open Terminal and run:
   ```
   xattr -dr com.apple.quarantine /Applications/study-kit.app
   ```

The macOS build is for Apple Silicon Macs (M1 or newer). Your data is stored in `~/.studykit/data.json`. Reminders appear as macOS notifications (you may need to allow notifications for "Script Editor" in System Settings).

PDF files are never uploaded anywhere. Everything runs locally.

### OCR for scanned PDFs

OCR is included in the downloads. On the PDF tab, tick **OCR** when you extract text from a scan or from slides saved as images. It runs on your computer. The first time you use each language (English, Korean, or Russian), the app downloads a small model (about 8 to 30 MB), so that first use needs an internet connection. After that it works offline.

## Run from source

Requires Python 3.10 or newer.

Windows:

```
git clone https://github.com/Plagudoktor0/study-kit.git
cd study-kit
python -m venv .venv
.venv\Scripts\activate
pip install -e .
python -m studykit.gui
```

macOS / Linux (tkinter must be installed; with Homebrew Python run `brew install python-tk` first):

```
git clone https://github.com/Plagudoktor0/study-kit.git
cd study-kit
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m studykit.gui
```

To use OCR when running from source, install the OCR extra instead of `pip install -e .`:

```
pip install -e ".[ocr]"
```

## Command-line tool

Deadlines:

```
studykit add "OS assignment" --due 2026-12-01 --subject OS
studykit list
studykit list --all
studykit next
studykit done 1
studykit restore 1
studykit delete 1
```

Backup and calendar:

```
studykit export backup.json
studykit import backup.json
studykit import backup.json --replace
studykit ics study.ics
studykit ics study.ics --all --no-exams
```

`import` merges with your current data by default. `--replace` replaces everything and keeps a copy of the old data file.

Exams:

```
studykit exam add "Networks" --date 2026-12-10 --topics "TCP, UDP, DNS, HTTP"
studykit exam list
studykit exam plan 1
studykit exam delete 1
```

PDF tools:

```
studykit pdf merge a.pdf b.pdf -o merged.pdf
studykit pdf split merged.pdf --pages "1-3, 5" -o part.pdf
studykit pdf rotate part.pdf --angle 90 --pages "1"
studykit pdf text part.pdf -o part.txt
```

Run `studykit --help` or `studykit pdf --help` to see every option.

## Project structure

```
src/studykit/
  gui.py         window, tabs, File menu, and dialogs
  widgets.py     rounded buttons and the table row highlight
  pdf_panel.py   the PDF tools tab
  pdf_tools.py   PDF logic: merge, split, rotate, extract text
  ocr.py         OCR for scanned PDFs
  deadlines.py   deadline logic: add, edit, done, archive, summary
  timeleft.py    how "days left" is calculated and shown
  exams.py       exam logic and the study-plan algorithm
  subjects.py    saved subjects
  backup.py      export and import of all data
  ics.py         calendar (.ics) export
  reminders.py   which deadlines need a reminder (once per day)
  notifier.py    desktop notifications (Windows and macOS)
  autostart.py   "Start with Windows" setting
  theme.py       light/dark themes and high-DPI scaling
  storage.py     JSON data file
  cli.py         command-line tool
tests/           pytest tests for the logic and the command line
.github/workflows/
  ci.yml           runs the tests on Windows and macOS
  build-macos.yml  builds the macOS app and attaches it to a draft release
```

## Tests

```
pip install pytest
pytest
```

The tests also run automatically on Windows and macOS for every push.

## Build the app

Use a clean virtual environment, so the app does not bundle packages it does not need. The OCR extra is installed so that OCR ends up inside the app.

Windows (`.exe`):

```
python -m venv .venv-build
.venv-build\Scripts\activate
pip install -e ".[ocr]"
pip install pyinstaller
pyinstaller --onefile --windowed --name study-kit --paths src --hidden-import babel.numbers --hidden-import winotify --collect-all rapidocr launcher.py
```

The exe appears in the `dist` folder. Zip it and upload the zip to the release. The `--hidden-import` options are needed because the calendar and notification libraries load some modules in a way PyInstaller can't detect, and `--collect-all rapidocr` bundles the OCR engine.

macOS (`.app`): PyInstaller must run on a Mac, so the repository builds it with GitHub Actions (`build-macos.yml`) on every version tag, and attaches the zip to a draft release. To build it yourself on a Mac:

```
pip install -e ".[ocr]"
pip install pyinstaller
pyinstaller --windowed --name study-kit --paths src --hidden-import babel.numbers --collect-all rapidocr launcher.py
```

## Roadmap

- [x] Edit a deadline by double-clicking it
- [x] Windows notifications for deadlines that are due soon
- [x] Exam planner
- [x] Dark mode
- [x] PDF toolkit (merge, split, rotate, extract text)
- [x] Search and subject filter
- [x] Backup export and import
- [x] Calendar (.ics) export
- [x] OCR for scanned PDFs
- [x] macOS support (experimental)
- [x] GitHub Actions: tests on every push
- [ ] "Start at login" on macOS
- [ ] Intel Mac build

## License

MIT