"""The 'PDF tools' tab of the window: merge, split, rotate, extract text (with optional OCR)."""

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from studykit import ocr, pdf_tools

PDF_TYPES = [("PDF files", "*.pdf"), ("All files", "*.*")]
TEXT_TYPES = [("Text files", "*.txt"), ("All files", "*.*")]


def ask_save(default_name: str, extension: str = ".pdf", types=PDF_TYPES) -> Path | None:
    """Ask where to save. Returns None if the user cancels."""
    chosen = filedialog.asksaveasfilename(
        title="Save as", initialfile=default_name, defaultextension=extension, filetypes=types
    )
    return Path(chosen) if chosen else None


def page_count_text(path: Path) -> str:
    """'12 pages', or the reason the file can't be opened."""
    try:
        count = len(pdf_tools.open_pdf(path).pages)
    except pdf_tools.PdfToolError as error:
        return str(error)
    return f"{count} page{'s' if count != 1 else ''}"


class FilePicker(ttk.Frame):
    """A read-only path field with a Browse button."""

    def __init__(self, parent, on_change=None):
        super().__init__(parent)
        self.path: Path | None = None
        self.on_change = on_change
        self.text = tk.StringVar()
        ttk.Entry(self, textvariable=self.text, width=48, state="readonly").pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(self, text="Browse...", command=self.browse).pack(side="left", padx=(5, 0))

    def browse(self):
        chosen = filedialog.askopenfilename(title="Choose a PDF", filetypes=PDF_TYPES)
        if not chosen:
            return
        self.path = Path(chosen)
        self.text.set(str(self.path))
        if self.on_change:
            self.on_change(self.path)

    def require(self) -> Path | None:
        """The chosen file, or None (with a hint) if nothing is chosen yet."""
        if self.path is None:
            messagebox.showinfo("No file", "Choose a PDF file first.")
        return self.path


class MergeTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.paths: list[Path] = []

        ttk.Label(self, text="Files are joined from top to bottom.").pack(
            anchor="w", padx=10, pady=(10, 5)
        )
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=10)
        self.tree = ttk.Treeview(
            body, columns=("file",), show="headings", selectmode="browse", height=6
        )
        self.tree.heading("file", text="File")
        self.tree.column("file", anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)

        side = ttk.Frame(body)
        side.pack(side="left", fill="y", padx=(10, 0))
        for text, command in (
            ("Add files...", self.add_files),
            ("Remove", self.remove),
            ("Move up", lambda: self.move(-1)),
            ("Move down", lambda: self.move(1)),
        ):
            ttk.Button(side, text=text, command=command).pack(fill="x", pady=2)

        ttk.Button(self, text="Merge...", style="Accent.TButton", command=self.merge).pack(
            anchor="w", padx=10, pady=10
        )

    def refresh(self, select: int | None = None):
        self.tree.delete(*self.tree.get_children())
        for path in self.paths:
            self.tree.insert("", "end", values=(str(path),))
        if select is not None:
            self.tree.selection_set(self.tree.get_children()[select])

    def selected_index(self) -> int | None:
        selection = self.tree.selection()
        return self.tree.index(selection[0]) if selection else None

    def add_files(self):
        chosen = filedialog.askopenfilenames(title="Choose PDFs", filetypes=PDF_TYPES)
        self.paths.extend(Path(name) for name in chosen)
        self.refresh()

    def remove(self):
        index = self.selected_index()
        if index is None:
            return
        self.paths.pop(index)
        self.refresh()

    def move(self, step: int):
        index = self.selected_index()
        if index is None:
            return
        target = index + step
        if not 0 <= target < len(self.paths):
            return
        self.paths[index], self.paths[target] = self.paths[target], self.paths[index]
        self.refresh(select=target)

    def merge(self):
        if len(self.paths) < 2:
            messagebox.showinfo("Merge", "Add at least two PDF files.")
            return
        output = ask_save("merged.pdf")
        if output is None:
            return
        try:
            pdf_tools.merge_pdfs(self.paths, output)
        except pdf_tools.PdfToolError as error:
            messagebox.showerror("Merge", str(error))
            return
        messagebox.showinfo("Merge", f"Saved {output.name}")


class SplitTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        pad = {"padx": 10, "pady": 5}
        self.columnconfigure(1, weight=1)

        ttk.Label(self, text="PDF file").grid(row=0, column=0, sticky="w", **pad)
        self.picker = FilePicker(self, on_change=self.show_pages)
        self.picker.grid(row=0, column=1, sticky="ew", **pad)
        self.info = ttk.Label(self, text="")
        self.info.grid(row=1, column=1, sticky="w", padx=10)

        ttk.Label(self, text="Pages to keep").grid(row=2, column=0, sticky="w", **pad)
        self.pages_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.pages_var, width=20).grid(
            row=2, column=1, sticky="w", **pad
        )
        ttk.Label(self, text="Example: 1-3, 5").grid(row=3, column=1, sticky="w", padx=10)
        ttk.Button(self, text="Save pages...", style="Accent.TButton", command=self.split).grid(
            row=4, column=1, sticky="w", **pad
        )

    def show_pages(self, path: Path):
        self.info.configure(text=page_count_text(path))

    def split(self):
        source = self.picker.require()
        if source is None:
            return
        output = ask_save(f"{source.stem}_pages.pdf")
        if output is None:
            return
        try:
            pdf_tools.split_pdf(source, self.pages_var.get(), output)
        except pdf_tools.PdfToolError as error:
            messagebox.showerror("Split", str(error))
            return
        messagebox.showinfo("Split", f"Saved {output.name}")


class RotateTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        pad = {"padx": 10, "pady": 5}
        self.columnconfigure(1, weight=1)

        ttk.Label(self, text="PDF file").grid(row=0, column=0, sticky="w", **pad)
        self.picker = FilePicker(self, on_change=self.show_pages)
        self.picker.grid(row=0, column=1, sticky="ew", **pad)
        self.info = ttk.Label(self, text="")
        self.info.grid(row=1, column=1, sticky="w", padx=10)

        ttk.Label(self, text="Rotate clockwise").grid(row=2, column=0, sticky="w", **pad)
        self.angle_var = tk.StringVar(value="90")
        ttk.Combobox(
            self,
            textvariable=self.angle_var,
            values=["90", "180", "270"],
            state="readonly",
            width=8,
        ).grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(self, text="Pages").grid(row=3, column=0, sticky="w", **pad)
        self.pages_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.pages_var, width=20).grid(
            row=3, column=1, sticky="w", **pad
        )
        ttk.Label(self, text="Leave empty to rotate every page. Example: 1-3, 5").grid(
            row=4, column=1, sticky="w", padx=10
        )
        ttk.Button(self, text="Rotate...", style="Accent.TButton", command=self.rotate).grid(
            row=5, column=1, sticky="w", **pad
        )

    def show_pages(self, path: Path):
        self.info.configure(text=page_count_text(path))

    def rotate(self):
        source = self.picker.require()
        if source is None:
            return
        output = ask_save(f"{source.stem}_rotated.pdf")
        if output is None:
            return
        try:
            pdf_tools.rotate_pdf(source, output, int(self.angle_var.get()), self.pages_var.get())
        except pdf_tools.PdfToolError as error:
            messagebox.showerror("Rotate", str(error))
            return
        messagebox.showinfo("Rotate", f"Saved {output.name}")


class TextTab(ttk.Frame):
    """Extract text. With OCR switched on, text inside pictures is read too."""

    LANGUAGE_NAMES = {name: code for code, name in ocr.LANGUAGES.items()}

    def __init__(self, parent):
        super().__init__(parent)
        pad = {"padx": 10, "pady": 5}
        self.columnconfigure(1, weight=1)
        self.worker: threading.Thread | None = None
        self.cancel_event = threading.Event()
        self.state: dict = {}

        ttk.Label(self, text="PDF file").grid(row=0, column=0, sticky="w", **pad)
        self.picker = FilePicker(self, on_change=self.show_pages)
        self.picker.grid(row=0, column=1, sticky="ew", **pad)
        self.info = ttk.Label(self, text="")
        self.info.grid(row=1, column=1, sticky="w", padx=10)

        self.use_ocr = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self,
            text="Read text inside pictures (OCR), for scans and slides saved as images",
            variable=self.use_ocr,
            command=self.update_options,
        ).grid(row=2, column=1, sticky="w", **pad)

        self.options = ttk.Frame(self)
        self.options.grid(row=3, column=1, sticky="w", padx=10)
        ttk.Label(self.options, text="Language of the text").grid(row=0, column=0, sticky="w")
        self.language = tk.StringVar(value="English")
        self.language_box = ttk.Combobox(
            self.options,
            textvariable=self.language,
            values=list(self.LANGUAGE_NAMES),
            state="readonly",
            width=12,
        )
        self.language_box.grid(row=0, column=1, sticky="w", padx=(8, 0), pady=2)
        self.all_pages = tk.BooleanVar(value=False)
        self.all_pages_check = ttk.Checkbutton(
            self.options,
            text="Read every page as a picture (slower; also finds pictures next to normal text)",
            variable=self.all_pages,
        )
        self.all_pages_check.grid(row=1, column=0, columnspan=2, sticky="w", pady=2)
        self.hint = ttk.Label(
            self.options,
            text="Pick the language of the slides. Korean and Russian also read English.\n"
            "The first use of a language downloads a small model (internet needed).",
            justify="left",
        )
        self.hint.grid(row=2, column=0, columnspan=2, sticky="w", pady=(2, 0))

        buttons = ttk.Frame(self)
        buttons.grid(row=4, column=1, sticky="w", **pad)
        self.extract_button = ttk.Button(
            buttons, text="Extract text...", style="Accent.TButton", command=self.extract
        )
        self.extract_button.pack(side="left")
        self.cancel_button = ttk.Button(buttons, text="Cancel", command=self.cancel)
        self.cancel_button.pack(side="left", padx=(8, 0))
        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.grid(row=5, column=1, sticky="ew", **pad)
        self.status = ttk.Label(self, text="")
        self.status.grid(row=6, column=1, sticky="w", padx=10)

        self.update_options()
        self.set_busy(False)

    def update_options(self):
        """Show the OCR settings only while OCR is switched on."""
        if self.use_ocr.get():
            self.options.grid()
        else:
            self.options.grid_remove()

    def set_busy(self, busy: bool):
        self.extract_button.configure(state="disabled" if busy else "normal")
        self.cancel_button.configure(state="normal" if busy else "disabled")
        if not busy:
            self.progress.stop()
            self.progress.configure(mode="determinate", value=0)

    def show_pages(self, path: Path):
        self.info.configure(text=page_count_text(path))

    def extract(self):
        source = self.picker.require()
        if source is None:
            return
        output = ask_save(f"{source.stem}.txt", ".txt", TEXT_TYPES)
        if output is None:
            return
        if self.use_ocr.get():
            self.start_ocr(source, output)
        else:
            self.extract_plain(source, output)

    def extract_plain(self, source: Path, output: Path):
        try:
            count = pdf_tools.extract_text(source, output)
        except pdf_tools.PdfToolError as error:
            messagebox.showerror("Extract text", str(error))
            return
        if count == 0:
            messagebox.showwarning(
                "Extract text",
                f"Saved {output.name}, but no text was found.\n"
                "This PDF may be a scan. Tick 'Read text inside pictures (OCR)' and try again.",
            )
        else:
            messagebox.showinfo("Extract text", f"Saved {output.name} ({count} characters)")

    # ---------- OCR runs in a background thread so the window stays responsive ----------

    def start_ocr(self, source: Path, output: Path):
        if not ocr.is_available():
            messagebox.showerror(
                "OCR is not installed",
                'Install it with:\n\npip install "study-kit[ocr]"\n\nthen start the app again.',
            )
            return
        lang = self.LANGUAGE_NAMES[self.language.get()]
        force = self.all_pages.get()
        self.cancel_event = threading.Event()
        self.state = {"done": 0, "total": 0, "result": None, "error": None, "cancelled": False}
        state, cancel_event = self.state, self.cancel_event

        def on_progress(done: int, total: int):
            state["done"], state["total"] = done, total

        def work():
            try:
                state["result"] = ocr.extract_text_ocr(
                    source, output, lang, force, progress=on_progress, cancel=cancel_event
                )
            except ocr.OcrCancelled:
                state["cancelled"] = True
            except pdf_tools.PdfToolError as error:
                state["error"] = str(error)
            except Exception as error:  # a background crash must be shown, not lost
                state["error"] = f"Unexpected problem: {error}"

        self.worker = threading.Thread(target=work, daemon=True)
        self.set_busy(True)
        self.progress.configure(mode="indeterminate")
        self.progress.start(15)
        self.status.configure(text="Starting... (the first use downloads the language model)")
        self.worker.start()
        self.after(150, lambda: self.poll_ocr(output))

    def cancel(self):
        self.cancel_event.set()
        self.status.configure(text="Stopping after this page...")

    def poll_ocr(self, output: Path):
        state = self.state
        if state["total"] and state["done"]:
            if str(self.progress.cget("mode")) != "determinate":
                self.progress.stop()
                self.progress.configure(mode="determinate")
            self.progress.configure(maximum=state["total"], value=state["done"])
            self.status.configure(text=f"Read {state['done']} of {state['total']} pages...")
        if self.worker is not None and self.worker.is_alive():
            self.after(150, lambda: self.poll_ocr(output))
            return
        self.set_busy(False)
        self.status.configure(text="")
        if state["cancelled"]:
            messagebox.showinfo("Extract text", "Stopped. No file was saved.")
        elif state["error"]:
            messagebox.showerror("Extract text", state["error"])
        else:
            result = state["result"]
            if result["characters"] == 0:
                messagebox.showwarning(
                    "Extract text", f"Saved {output.name}, but no text was found, even with OCR."
                )
            else:
                messagebox.showinfo(
                    "Extract text",
                    f"Saved {output.name}\n{result['characters']} characters. "
                    f"{result['ocr_pages']} of {result['pages']} pages were read with OCR.",
                )


class PdfPanel(ttk.Frame):
    """Everything on the PDF tab: four small tools in their own sub-tabs."""

    def __init__(self, parent):
        super().__init__(parent)
        tools = ttk.Notebook(self)
        tools.pack(fill="both", expand=True, padx=10, pady=10)
        tools.add(MergeTab(tools), text="Merge")
        tools.add(SplitTab(tools), text="Split")
        tools.add(RotateTab(tools), text="Rotate")
        tools.add(TextTab(tools), text="Extract text")
