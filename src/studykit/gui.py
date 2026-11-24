import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from tkcalendar import Calendar

from studykit import deadlines, subjects



class DatePicker(ttk.Frame):
    """A read-only date field with a button that opens a calendar popup."""

    def __init__(self, parent):
        super().__init__(parent)
        self.date = date.today()
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
    """Small form for adding a deadline."""

    def __init__(self, parent, on_saved):
        super().__init__(parent)
        self.on_saved = on_saved
        self.title("Add deadline")
        self.resizable(False, False)
        self.transient(parent)
        # open near the top-left corner of the main window
        self.geometry(f"+{parent.winfo_x() + 20}+{parent.winfo_y() + 20}")

        pad = {"padx": 10, "pady": 5}

        ttk.Label(self, text="Title").grid(row=0, column=0, sticky="w", **pad)
        self.title_var = tk.StringVar()
        title_entry = ttk.Entry(self, textvariable=self.title_var, width=30)
        title_entry.grid(row=0, column=1, **pad)

        ttk.Label(self, text="Subject").grid(row=1, column=0, sticky="w", **pad)
        self.subject_var = tk.StringVar()
        ttk.Combobox(
            self, textvariable=self.subject_var, values=subjects.list_subjects(), width=27
        ).grid(row=1, column=1, **pad)

        ttk.Label(self, text="Due date").grid(row=2, column=0, sticky="w", **pad)
        self.due_picker = DatePicker(self)
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
        deadlines.add_deadline(title, subject, self.due_picker.date)
        subjects.add_subject(subject)
        self.on_saved()
        self.destroy()



class App(tk.Tk):
    """Main window: active deadlines, or the archive of finished ones."""

    def __init__(self):
        super().__init__()
        self.title("study-kit")
        self.geometry("620x360")

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

        self.refresh()

    def open_add(self):
        AddDialog(self, on_saved=self.refresh)

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