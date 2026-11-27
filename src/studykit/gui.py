import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from tkcalendar import Calendar

from studykit import autostart, deadlines, exams, notifier, reminders, subjects, theme


class DatePicker(ttk.Frame):
    """A read-only date field with a button that opens a calendar popup."""

    def __init__(self, parent, initial=None):
        super().__init__(parent)
        self.date = initial or date.today()
        self.text = tk.StringVar(value=self.date.isoformat())
        ttk.Entry(self, textvariable=self.text, width=22, state="readonly").pack(side="left")
        ttk.Button(self, text="Pick...", width=7, command=self.open_popup).pack(
            side="left", padx=(5, 0)
        )

    def open_popup(self):
        top = tk.Toplevel(self)
        top.title("Pick a date")
        top.resizable(False, False)
        top.transient(self.winfo_toplevel())
        top.geometry(f"+{self.winfo_rootx()}+{self.winfo_rooty() + self.winfo_height()}")

        p = theme.palette()
        cal = Calendar(
            top,
            selectmode="day",
            date_pattern="yyyy-mm-dd",
            firstweekday="monday",
            showweeknumbers=False,
            showothermonthdays=False,
            year=self.date.year,
            month=self.date.month,
            day=self.date.day,
            background=p["button"],
            foreground=p["fg"],
            headersbackground=p["button"],
            headersforeground=p["fg"],
            normalbackground=p["field"],
            normalforeground=p["fg"],
            weekendbackground=p["field"],
            weekendforeground=p["fg"],
            selectbackground=p["select"],
            selectforeground=p["select_fg"],
            bordercolor=p["border"],
        )
        cal.pack(padx=10, pady=10)

        def choose():
            chosen = cal.selection_get()
            if chosen is not None:
                self.date = chosen
                self.text.set(chosen.isoformat())
            top.destroy()

        ttk.Button(top, text="OK", command=choose).pack(pady=(0, 10))


class AddDialog(tk.Toplevel):
    """Form for adding a deadline, or for editing one when `item` is given."""

    def __init__(self, parent, on_saved, item=None):
        super().__init__(parent)
        self.on_saved = on_saved
        self.item = item
        self.title("Edit deadline" if item else "Add deadline")
        self.resizable(False, False)
        self.transient(parent)
        # open near the top-left corner of the main window
        self.geometry(f"+{parent.winfo_x() + 20}+{parent.winfo_y() + 20}")

        pad = {"padx": 10, "pady": 5}

        ttk.Label(self, text="Title").grid(row=0, column=0, sticky="w", **pad)
        self.title_var = tk.StringVar(value=item["title"] if item else "")
        title_entry = ttk.Entry(self, textvariable=self.title_var, width=30)
        title_entry.grid(row=0, column=1, **pad)

        ttk.Label(self, text="Subject").grid(row=1, column=0, sticky="w", **pad)
        self.subject_var = tk.StringVar(value=item["subject"] if item else "")
        ttk.Combobox(
            self, textvariable=self.subject_var, values=subjects.list_subjects(), width=27
        ).grid(row=1, column=1, **pad)

        ttk.Label(self, text="Due date").grid(row=2, column=0, sticky="w", **pad)
        initial = date.fromisoformat(item["due"]) if item else None
        self.due_picker = DatePicker(self, initial)
        self.due_picker.grid(row=2, column=1, sticky="w", **pad)

        buttons = ttk.Frame(self)
        buttons.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(buttons, text="Save", style="Accent.TButton", command=self.save).pack(
            side="left", padx=5
        )
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        title_entry.focus()
        self.bind("<Escape>", lambda event: self.destroy())

    def save(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showerror("Missing title", "Please enter a title.", parent=self)
            return
        subject = self.subject_var.get().strip()
        if self.item:
            deadlines.update_deadline(self.item["id"], title, subject, self.due_picker.date)
        else:
            deadlines.add_deadline(title, subject, self.due_picker.date)
        subjects.add_subject(subject)
        self.on_saved()
        self.destroy()


class ExamDialog(tk.Toplevel):
    """Form for adding an exam with its list of topics."""

    def __init__(self, parent, on_saved):
        super().__init__(parent)
        self.on_saved = on_saved
        self.title("Add exam")
        self.resizable(False, False)
        self.transient(parent)
        self.geometry(f"+{parent.winfo_x() + 20}+{parent.winfo_y() + 20}")

        pad = {"padx": 10, "pady": 5}

        ttk.Label(self, text="Subject").grid(row=0, column=0, sticky="w", **pad)
        self.subject_var = tk.StringVar()
        subject_box = ttk.Combobox(
            self, textvariable=self.subject_var, values=subjects.list_subjects(), width=27
        )
        subject_box.grid(row=0, column=1, **pad)

        ttk.Label(self, text="Exam date").grid(row=1, column=0, sticky="w", **pad)
        self.date_picker = DatePicker(self)
        self.date_picker.grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(self, text="Topics").grid(row=2, column=0, sticky="nw", **pad)
        self.topics_text = tk.Text(self, width=30, height=7, wrap="word")
        self.topics_text.grid(row=2, column=1, **pad)
        ttk.Label(self, text="One topic per line, or separated by commas").grid(
            row=3, column=1, sticky="w", padx=10
        )

        buttons = ttk.Frame(self)
        buttons.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(buttons, text="Save", style="Accent.TButton", command=self.save).pack(
            side="left", padx=5
        )
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        subject_box.focus()
        self.bind("<Escape>", lambda event: self.destroy())

    def save(self):
        subject = self.subject_var.get().strip()
        if not subject:
            messagebox.showerror("Missing subject", "Please enter a subject.", parent=self)
            return
        topics = exams.parse_topics(self.topics_text.get("1.0", "end"))
        if not topics:
            messagebox.showerror("No topics", "Add at least one topic.", parent=self)
            return
        exams.add_exam(subject, self.date_picker.date, topics)
        subjects.add_subject(subject)
        self.on_saved()
        self.destroy()


class App(tk.Tk):
    """Main window with two tabs: Deadlines and Exams."""

    def __init__(self):

        super().__init__()
        self.title("study-kit")

        self.theme_mode = theme.get_mode()
        self.theme_name = theme.apply(self, self.theme_mode)

        # window size scales with the screen, but never exceeds it
        width = min(theme.px(900), int(self.winfo_screenwidth() * 0.9))
        height = min(theme.px(560), int(self.winfo_screenheight() * 0.85))
        self.geometry(f"{width}x{height}")
        self.minsize(min(theme.px(820), width), min(theme.px(440), height))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        self.deadlines_tab = ttk.Frame(self.notebook)
        self.exams_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.deadlines_tab, text="Deadlines")
        self.notebook.add(self.exams_tab, text="Exams")

        self.build_deadlines_tab()
        self.build_exams_tab()
        self.build_footer()
        self.apply_theme_colors()

        self.refresh()
        self.refresh_exams()
        self.after(2000, self.check_reminders)  # first reminder check shortly after start
        self.after(5000, self.poll_theme)  # follow the Windows theme

    def build_footer(self):
        footer = ttk.Frame(self)
        footer.pack(fill="x", padx=10, pady=(0, 8))
        self.theme_var = tk.StringVar(value=self.theme_mode.capitalize())
        box = ttk.Combobox(
            footer,
            textvariable=self.theme_var,
            values=["System", "Light", "Dark"],
            state="readonly",
            width=8,
        )
        box.pack(side="right")
        ttk.Label(footer, text="Theme:").pack(side="right", padx=(0, 5))
        box.bind("<<ComboboxSelected>>", self.change_theme)

    def change_theme(self, event=None):
        self.theme_mode = self.theme_var.get().lower()
        theme.set_mode(self.theme_mode)
        self.reapply_theme()

    def reapply_theme(self):
        self.theme_name = theme.apply(self, self.theme_mode)
        self.apply_theme_colors()

    def apply_theme_colors(self):
        """Colors that ttk styles can't set: row tags, cards, and the plan text box."""
        p = theme.palette()
        for tree in (self.tree, self.exam_tree):
            tree.tag_configure("overdue", foreground=p["overdue"])
            tree.tag_configure("soon", foreground=p["soon"])
            tree.tag_configure("finished", foreground=p["finished"])
        for card in self.cards:
            card.configure(
                bg=p["field"], highlightbackground=p["border"], highlightcolor=p["border"]
            )
        self.plan_text.configure(
            bg=p["field"],
            fg=p["fg"],
            insertbackground=p["fg"],
            selectbackground=p["select"],
            selectforeground=p["select_fg"],
        )

    def poll_theme(self):
        """In System mode, check the Windows setting again every few seconds."""
        if self.theme_mode == "system":
            if theme.resolve_name("system", theme.system_is_dark()) != self.theme_name:
                self.reapply_theme()
        self.after(5000, self.poll_theme)

    def setup_columns(self, tree, columns):
        """columns: (name, heading, width at 96 DPI, stretches with the window)."""
        for name, text, width, stretch in columns:
            tree.heading(name, text=text)
            tree.column(
                name, width=theme.px(width), minwidth=theme.px(40), anchor="w", stretch=stretch
            )

    # ---------- Deadlines tab ----------

    def build_deadlines_tab(self):
        # summary cards
        summary = ttk.Frame(self.deadlines_tab)
        summary.pack(fill="x", padx=10, pady=(10, 0))
        self.cards = []
        self.card_values = {}
        card_specs = [
            ("overdue", "Overdue", "Danger.CardValue.TLabel"),
            ("week", "Due in the next 7 days", "Warn.CardValue.TLabel"),
            ("finished", "Finished", "Quiet.CardValue.TLabel"),
        ]
        for column, (key, caption, value_style) in enumerate(card_specs):
            summary.columnconfigure(column, weight=1, uniform="cards")
            card = tk.Frame(summary, highlightthickness=1)
            right_gap = theme.px(10) if column < len(card_specs) - 1 else 0
            card.grid(row=0, column=column, sticky="ew", padx=(0, right_gap))
            value = ttk.Label(card, text="0", style=value_style)
            value.pack(anchor="w", padx=theme.px(14), pady=(theme.px(8), 0))
            ttk.Label(card, text=caption, style="CardCaption.TLabel").pack(
                anchor="w", padx=theme.px(14), pady=(0, theme.px(8))
            )
            self.cards.append(card)
            self.card_values[key] = value

        # deadlines table
        columns = ("id", "due", "left", "subject", "title")
        self.tree = ttk.Treeview(
            self.deadlines_tab, columns=columns, show="headings", selectmode="browse"
        )
        self.setup_columns(
            self.tree,
            [
                ("id", "ID", 40, False),
                ("due", "Due", 100, False),
                ("left", "Left", 100, False),
                ("subject", "Subject", 140, True),
                ("title", "Title", 280, True),
            ],
        )
        self.tree.pack(fill="both", expand=True, padx=10, pady=(theme.px(10), 0))
        self.tree.bind("<Double-1>", self.open_edit)
        self.empty_label = ttk.Label(self.tree, style="Empty.TLabel", justify="center")

        self.show_archive = tk.BooleanVar(value=False)

        bar = ttk.Frame(self.deadlines_tab)
        bar.pack(fill="x", padx=10, pady=10)
        ttk.Button(bar, text="Add deadline", style="Accent.TButton", command=self.open_add).pack(
            side="left"
        )
        ttk.Button(bar, text="Done", command=self.mark_selected_done).pack(side="left", padx=5)
        ttk.Button(bar, text="Restore", command=self.restore_selected).pack(side="left")
        ttk.Button(bar, text="Delete", command=self.delete_selected).pack(side="left", padx=5)
        ttk.Checkbutton(
            bar, text="Show archive", variable=self.show_archive, command=self.refresh
        ).pack(side="right")
        if autostart.supported():
            self.autostart_var = tk.BooleanVar(value=autostart.is_enabled())
            ttk.Checkbutton(
                bar,
                text="Start with Windows",
                variable=self.autostart_var,
                command=self.toggle_autostart,
            ).pack(side="right", padx=10)
        self.notify_var = tk.BooleanVar(value=reminders.is_enabled())
        ttk.Checkbutton(
            bar, text="Notify", variable=self.notify_var, command=self.toggle_notify
        ).pack(side="right")

    def open_add(self):
        AddDialog(self, on_saved=self.refresh)

    def open_edit(self, event):
        row = self.tree.identify_row(event.y)
        if not row:
            return  # double-click on the header or on empty space
        deadline_id = int(self.tree.item(row, "values")[0])
        for item in deadlines.list_deadlines(include_done=True):
            if item["id"] == deadline_id:
                AddDialog(self, on_saved=self.refresh, item=item)
                return

    def toggle_notify(self):
        reminders.set_enabled(self.notify_var.get())

    def check_reminders(self):
        reminders.check_and_notify(notifier.send)
        self.after(3_600_000, self.check_reminders)  # check again in one hour

    def toggle_autostart(self):
        wanted = self.autostart_var.get()
        try:
            if wanted:
                autostart.enable()
            else:
                autostart.disable()
        except OSError as error:
            self.autostart_var.set(not wanted)  # put the checkbox back
            messagebox.showerror("Auto-start", f"Could not change the setting:\n{error}")

    def selected_id(self):
        """ID of the highlighted row, or None (with a hint) if nothing is selected."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Nothing selected", "Click a row first.")
            return None
        return int(self.tree.item(selection[0], "values")[0])

    def mark_selected_done(self):
        deadline_id = self.selected_id()
        if deadline_id is None:
            return
        deadlines.mark_done(deadline_id)
        self.refresh()

    def restore_selected(self):
        deadline_id = self.selected_id()
        if deadline_id is None:
            return
        deadlines.restore_deadline(deadline_id)
        self.refresh()

    def delete_selected(self):
        deadline_id = self.selected_id()
        if deadline_id is None:
            return
        if messagebox.askyesno("Delete", "Delete this deadline permanently?"):
            deadlines.delete_deadline(deadline_id)
            self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        if self.show_archive.get():
            self.title("study-kit - archive")
            for item in deadlines.list_finished():
                self.tree.insert(
                    "",
                    "end",
                    values=(item["id"], item["due"], "finished", item["subject"], item["title"]),
                    tags=("finished",),
                )
            empty_text = "The archive is empty.\nFinished deadlines appear here."
        else:
            self.title("study-kit")
            for item in deadlines.list_deadlines():
                days = deadlines.days_left(item)
                if days < 0:
                    left, tags = f"overdue {-days} d", ("overdue",)
                elif days == 0:
                    left, tags = "today", ("soon",)
                elif days <= 3:
                    left, tags = f"in {days} d", ("soon",)
                else:
                    left, tags = f"in {days} d", ()
                self.tree.insert(
                    "",
                    "end",
                    values=(item["id"], item["due"], left, item["subject"], item["title"]),
                    tags=tags,
                )
            empty_text = "No deadlines yet.\nClick Add deadline to create your first one."

        if self.tree.get_children():
            self.empty_label.place_forget()
        else:
            self.empty_label.configure(text=empty_text)
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")

        counts = deadlines.summary()
        for key, label in self.card_values.items():
            label.configure(text=str(counts[key]))

    # ---------- Exams tab ----------

    def build_exams_tab(self):
        top = ttk.Frame(self.exams_tab)
        top.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        columns = ("id", "date", "left", "subject", "topics")
        self.exam_tree = ttk.Treeview(
            top, columns=columns, show="headings", selectmode="browse", height=6
        )
        self.setup_columns(
            self.exam_tree,
            [
                ("id", "ID", 40, False),
                ("date", "Exam date", 110, False),
                ("left", "Left", 100, False),
                ("subject", "Subject", 260, True),
                ("topics", "Topics", 80, False),
            ],
        )
        self.exam_tree.pack(fill="x")
        self.exam_tree.bind("<<TreeviewSelect>>", self.show_plan)
        self.exam_empty_label = ttk.Label(
            self.exam_tree,
            text="No exams yet.\nClick Add exam to plan your first one.",
            style="Empty.TLabel",
            justify="center",
        )

        ttk.Label(top, text="Study plan", style="Heading.TLabel").pack(anchor="w", pady=(10, 2))
        self.plan_text = tk.Text(top, height=8, state="disabled", wrap="word")
        self.plan_text.pack(fill="both", expand=True)

        bar = ttk.Frame(self.exams_tab)
        bar.pack(fill="x", padx=10, pady=10)
        ttk.Button(bar, text="Add exam", style="Accent.TButton", command=self.open_add_exam).pack(
            side="left"
        )
        ttk.Button(bar, text="Delete exam", command=self.delete_selected_exam).pack(
            side="left", padx=5
        )

    def open_add_exam(self):
        ExamDialog(self, on_saved=self.refresh_exams)

    def selected_exam_id(self):
        selection = self.exam_tree.selection()
        if not selection:
            return None
        return int(self.exam_tree.item(selection[0], "values")[0])

    def delete_selected_exam(self):
        exam_id = self.selected_exam_id()
        if exam_id is None:
            messagebox.showinfo("Nothing selected", "Click an exam first.")
            return
        if messagebox.askyesno("Delete", "Delete this exam permanently?"):
            exams.delete_exam(exam_id)
            self.refresh_exams()

    def refresh_exams(self):
        for row in self.exam_tree.get_children():
            self.exam_tree.delete(row)
        today = date.today()
        for exam in exams.list_exams():
            days = (date.fromisoformat(exam["date"]) - today).days
            if days < 0:
                left, tags = "passed", ("finished",)
            elif days == 0:
                left, tags = "today", ("soon",)
            elif days <= 3:
                left, tags = f"in {days} d", ("soon",)
            else:
                left, tags = f"in {days} d", ()
            self.exam_tree.insert(
                "",
                "end",
                values=(exam["id"], exam["date"], left, exam["subject"], len(exam["topics"])),
                tags=tags,
            )
        if self.exam_tree.get_children():
            self.exam_empty_label.place_forget()
        else:
            self.exam_empty_label.place(relx=0.5, rely=0.5, anchor="center")
        self.show_plan()

    def set_plan_text(self, text):
        self.plan_text.configure(state="normal")
        self.plan_text.delete("1.0", "end")
        self.plan_text.insert("1.0", text)
        self.plan_text.configure(state="disabled")

    def show_plan(self, event=None):
        exam_id = self.selected_exam_id()
        if exam_id is None:
            self.set_plan_text("Select an exam to see its study plan.")
            return
        for exam in exams.list_exams():
            if exam["id"] == exam_id:
                exam_date = date.fromisoformat(exam["date"])
                plan = exams.make_plan(exam["topics"], exam_date)
                if not plan:
                    self.set_plan_text("No plan: the exam is today or has passed.")
                    return
                lines = [
                    f"{day.strftime('%a %d %b')}:  {', '.join(day_topics)}"
                    for day, day_topics in plan
                ]
                lines.append(f"{exam_date.strftime('%a %d %b')}:  EXAM")
                self.set_plan_text("\n".join(lines))
                return


def main():
    theme.enable_high_dpi()  # must come before the window is created
    App().mainloop()


if __name__ == "__main__":
    main()
