from datetime import date, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from studykit import deadlines, exams, pdf_tools, timeleft

app = typer.Typer(help="study-kit: small tools for student life.")
exam_app = typer.Typer(help="Add exams and get a day-by-day study plan.")
pdf_app = typer.Typer(help="Merge, split, rotate PDFs and extract their text.")
app.add_typer(exam_app, name="exam")
app.add_typer(pdf_app, name="pdf")
console = Console()

DATE_FORMATS = ["%Y-%m-%d"]


def fail(message: str) -> None:
    """Print a red error and stop with a non-zero exit code."""
    console.print(f"[red]{message}[/red]")
    raise typer.Exit(code=1)


# ---------- Deadlines ----------


@app.command()
def add(
    title: str = typer.Argument(..., help="What needs to be done"),
    due: datetime = typer.Option(
        ..., "--due", "-d", formats=DATE_FORMATS, help="Due date, e.g. 2026-12-01"
    ),
    subject: str = typer.Option("", "--subject", "-s", help="Course name"),
):
    """Add a new deadline."""
    item = deadlines.add_deadline(title, subject, due.date())
    console.print(f"[green]Added #{item['id']}:[/green] {item['title']} (due {item['due']})")


@app.command("list")
def list_cmd(
    include_all: bool = typer.Option(False, "--all", "-a", help="Include finished deadlines"),
    subject: str = typer.Option("", "--subject", "-s", help="Only this subject"),
    search: str = typer.Option("", "--search", "-q", help="Only titles or subjects with this text"),
):
    """Show deadlines, closest first."""
    items = deadlines.list_deadlines(include_done=include_all)
    filtering = bool(subject.strip() or search.strip())
    items = deadlines.filter_items(items, search, subject)
    if not items:
        if filtering:
            console.print("No deadlines match this filter.")
        else:
            console.print("No deadlines yet. Add one with: studykit add")
        return

    table = Table(title="Deadlines")
    table.add_column("ID", justify="right")
    table.add_column("Due")
    table.add_column("Subject")
    table.add_column("Title")
    table.add_column("Done")
    for d in items:
        table.add_row(
            str(d["id"]), d["due"], d["subject"], d["title"], "yes" if d["done"] else "no"
        )
    console.print(table)


@app.command()
def done(deadline_id: int = typer.Argument(..., help="ID from 'studykit list'")):
    """Mark a deadline as finished."""
    item = deadlines.mark_done(deadline_id)
    if item is None:
        fail(f"No deadline with ID {deadline_id}.")
    console.print(f"[green]Done:[/green] {item['title']}")


@app.command()
def restore(deadline_id: int = typer.Argument(..., help="ID from 'studykit list --all'")):
    """Move a finished deadline back to the active list."""
    item = deadlines.restore_deadline(deadline_id)
    if item is None:
        fail(f"No deadline with ID {deadline_id}.")
    console.print(f"[green]Restored:[/green] {item['title']}")


@app.command()
def delete(deadline_id: int = typer.Argument(..., help="ID from 'studykit list --all'")):
    """Delete a deadline permanently."""
    if not deadlines.delete_deadline(deadline_id):
        fail(f"No deadline with ID {deadline_id}.")
    console.print(f"[green]Deleted deadline #{deadline_id}.[/green]")


@app.command("next")
def next_cmd():
    """Show the closest unfinished deadline."""
    item = deadlines.next_deadline()
    if item is None:
        console.print("Nothing due. Enjoy the free time!")
        return
    days = deadlines.days_left(item)
    if days < 0:
        when = f"[red]overdue by {-days} day(s)[/red]"
    elif days == 0:
        when = "[yellow]due today[/yellow]"
    else:
        when = f"in {days} day(s)"
    subject = item["subject"] or "no subject"
    console.print(f"[bold]{item['title']}[/bold] ({subject}), due {item['due']}, {when}")


# ---------- Exams ----------


def find_exam(exam_id: int) -> dict:
    for exam in exams.list_exams():
        if exam["id"] == exam_id:
            return exam
    fail(f"No exam with ID {exam_id}.")


@exam_app.command("add")
def exam_add(
    subject: str = typer.Argument(..., help="Course name"),
    exam_date: datetime = typer.Option(
        ..., "--date", "-d", formats=DATE_FORMATS, help="Exam date, e.g. 2026-12-08"
    ),
    topics: str = typer.Option(
        ..., "--topics", "-t", help='Comma-separated, e.g. "RISC-V, datapath, caches"'
    ),
):
    """Add an exam with its topics."""
    topic_list = exams.parse_topics(topics)
    if not topic_list:
        fail("Add at least one topic.")
    item = exams.add_exam(subject, exam_date.date(), topic_list)
    console.print(
        f"[green]Added exam #{item['id']}:[/green] {item['subject']} "
        f"({len(topic_list)} topics, on {item['date']})"
    )


@exam_app.command("list")
def exam_list():
    """Show exams, closest first."""
    items = exams.list_exams()
    if not items:
        console.print("No exams yet. Add one with: studykit exam add")
        return
    table = Table(title="Exams")
    table.add_column("ID", justify="right")
    table.add_column("Date")
    table.add_column("Left")
    table.add_column("Subject")
    table.add_column("Topics", justify="right")
    today = date.today()
    for e in items:
        left, _ = timeleft.exam_label(timeleft.days_until(e["date"], today))
        table.add_row(str(e["id"]), e["date"], left, e["subject"], str(len(e["topics"])))
    console.print(table)


@exam_app.command("plan")
def exam_plan(exam_id: int = typer.Argument(..., help="ID from 'studykit exam list'")):
    """Print the day-by-day study plan for one exam."""
    exam = find_exam(exam_id)
    exam_date = date.fromisoformat(exam["date"])
    plan = exams.make_plan(exam["topics"], exam_date)
    if not plan:
        fail("No plan: the exam is today or has passed.")
    console.print(f"[bold]{exam['subject']}[/bold]")
    for day, day_topics in plan:
        console.print(f"{day.strftime('%a %d %b')}:  {', '.join(day_topics)}")
    console.print(f"[bold]{exam_date.strftime('%a %d %b')}:  EXAM[/bold]")


@exam_app.command("delete")
def exam_delete(exam_id: int = typer.Argument(..., help="ID from 'studykit exam list'")):
    """Delete an exam permanently."""
    if not exams.delete_exam(exam_id):
        fail(f"No exam with ID {exam_id}.")
    console.print(f"[green]Deleted exam #{exam_id}.[/green]")


# ---------- PDF tools ----------


def pdf_run(action):
    """Run a pdf_tools call and turn PdfToolError into a clean red message."""
    try:
        return action()
    except pdf_tools.PdfToolError as error:
        fail(str(error))


@pdf_app.command("merge")
def pdf_merge(
    files: list[Path] = typer.Argument(..., help="PDFs to join, in order"),
    output: Path = typer.Option(..., "--output", "-o", help="Name of the merged PDF"),
):
    """Join several PDFs into one."""
    pdf_run(lambda: pdf_tools.merge_pdfs(files, output))
    console.print(f"[green]Saved:[/green] {output}")


@pdf_app.command("split")
def pdf_split(
    source: Path = typer.Argument(..., help="PDF to take pages from"),
    pages: str = typer.Option(..., "--pages", "-p", help='Pages to keep, e.g. "1-3, 5"'),
    output: Path = typer.Option(None, "--output", "-o", help="Default: <name>_pages.pdf"),
):
    """Save only some pages of a PDF as a new file."""
    output = output or source.with_name(f"{source.stem}_pages.pdf")
    pdf_run(lambda: pdf_tools.split_pdf(source, pages, output))
    console.print(f"[green]Saved:[/green] {output}")


@pdf_app.command("rotate")
def pdf_rotate(
    source: Path = typer.Argument(..., help="PDF to rotate"),
    angle: int = typer.Option(90, "--angle", "-a", help="Clockwise: 90, 180 or 270"),
    pages: str = typer.Option("", "--pages", "-p", help="Pages to rotate (default: all)"),
    output: Path = typer.Option(None, "--output", "-o", help="Default: <name>_rotated.pdf"),
):
    """Rotate pages of a PDF clockwise."""
    output = output or source.with_name(f"{source.stem}_rotated.pdf")
    pdf_run(lambda: pdf_tools.rotate_pdf(source, output, angle, pages))
    console.print(f"[green]Saved:[/green] {output}")


@pdf_app.command("text")
def pdf_text(
    source: Path = typer.Argument(..., help="PDF to read"),
    output: Path = typer.Option(None, "--output", "-o", help="Default: <name>.txt"),
):
    """Extract the text of a PDF into a .txt file."""
    output = output or source.with_suffix(".txt")
    count = pdf_run(lambda: pdf_tools.extract_text(source, output))
    if count == 0:
        console.print("[yellow]No text found. This PDF may be a scan (it needs OCR).[/yellow]")
    console.print(f"[green]Saved:[/green] {output} ({count} characters)")


if __name__ == "__main__":
    app()
