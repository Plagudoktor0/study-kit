from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table

from studykit import deadlines

app = typer.Typer(help="study-kit: small tools for student life.")
console = Console()


@app.command()
def add(
    title: str = typer.Argument(..., help="What needs to be done"),
    due: datetime = typer.Option(
        ..., "--due", "-d", formats=["%Y-%m-%d"], help="Due date, e.g. 2026-12-01"
    ),
    subject: str = typer.Option("", "--subject", "-s", help="Course name"),
):
    """Add a new deadline."""
    item = deadlines.add_deadline(title, subject, due.date())
    console.print(f"[green]Added #{item['id']}:[/green] {item['title']} (due {item['due']})")


@app.command("list")
def list_cmd(
    all: bool = typer.Option(False, "--all", "-a", help="Include finished deadlines"),
):
    """Show deadlines, closest first."""
    items = deadlines.list_deadlines(include_done=all)
    if not items:
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
        console.print(f"[red]No deadline with ID {deadline_id}.[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]Done:[/green] {item['title']}")


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


if __name__ == "__main__":
    app()
