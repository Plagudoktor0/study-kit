import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk

from studykit import deadlines, subjects


class AddDialog(tk.Toplevel):
    """Small form for adding a deadline."""

    def __init__(self, parent, on_saved):
        super().__init__(parent)
        self.on_saved = on_saved
        self.title("Add deadline")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()  # blocks the main window until this one is closed

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

        ttk.Label(self, text="Due (YYYY-MM-DD)").grid(row=2, column=0, sticky="w", **pad)
        self.due_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(self, textvariable=self.due_var, width=30).grid(row=2, column=1, **pad)

        buttons = ttk.Frame(self)
        buttons.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(buttons, text="Save", command=self.save).pack(side="left", padx=5)
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        title_entry.focus()
        self.bind("<Return>", lambda event: self.save())
        self.bind("<Escape>", lambda event: self.destroy())

    def save(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showerror("Missing title", "Please enter a title.", parent=self)
            return
        try:
            due = datetime.strptime(self.due_var.get().strip(), "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror(
                "Wrong date", "Use the format YYYY-MM-DD, e.g. 2026-12-01.", parent=self
            )
            return
                
        subject = self.subject_var.get().strip()
        deadlines.add_deadline(title, subject, due)
        subjects.add_subject(subject)
        self.on_saved()
        self.destroy()


class App(tk.Tk):
    """Main window: the list of unfinished deadlines."""

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
        self.tree.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=10)
        ttk.Button(bar, text="Add deadline", command=self.open_add).pack(side="left")
        ttk.Button(bar, text="Done", command=self.mark_selected_done).pack(side="left", padx=5)
        ttk.Button(bar, text="Delete", command=self.delete_selected).pack(side="left")

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