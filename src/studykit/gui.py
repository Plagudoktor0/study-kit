import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from tkcalendar import Calendar

from studykit import autostart, deadlines, notifier, reminders, subjects



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
        ttk.Button(buttons, text="Save", command=self.save).pack(side="left", padx=5)
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



class App(tk.Tk):
    """Main window: active deadlines, or the archive of finished ones."""

    def __init__(self):
        super().__init__()
        self.title("study-kit")
        self.geometry("760x360")

        columns = ("id", "due", "left", "subject", "title")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        for name, text, width in [
            ("id", "ID", 40),
            ("due", "Due", 90),
            ("left", "Left", 90),
            ("subject", "Subject", 110),
            ("title", "Title", 250),
        ]:
            self.tree.heading(name, text=text)
            self.tree.column(name, width=width, anchor="w")
        self.tree.tag_configure("overdue", foreground="#c0392b")
        self.tree.tag_configure("soon", foreground="#d68910")
        self.tree.tag_configure("finished", foreground="#7f8c8d")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        self.tree.bind("<Double-1>", self.open_edit)

        self.show_archive = tk.BooleanVar(value=False)

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=10)
        ttk.Button(bar, text="Add deadline", command=self.open_add).pack(side="left")
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

        self.refresh()
        self.after(2000, self.check_reminders)  # first reminder check shortly after start

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
            return

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


def main():
    App().mainloop()


if __name__ == "__main__":
    main()