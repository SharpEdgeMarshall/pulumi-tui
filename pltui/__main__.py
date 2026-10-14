import click

from pltui.app import PulumiTUI
from pltui.components.header import APP_VERSION


@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Pulumi Textual User Interface.",
)
@click.option(
    "-C",
    "--cwd",
    "project_dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    default=".",
    show_default="current directory",
    help="Run as if started in this Pulumi project directory.",
)
@click.version_option(APP_VERSION, "-V", "--version", prog_name="pltui")
def main(project_dir: str) -> None:
    PulumiTUI(project_dir=project_dir).run()


if __name__ == "__main__":
    main()
