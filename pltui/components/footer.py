from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Footer, Static


class AppFooter(Footer):
    """Extends Footer to display application status"""

    status: reactive[str] = reactive("Ready", recompose=True)

    DEFAULT_CSS = """
    AppFooter > #status-label {
        width: 1fr;
        height: 1;
        text-align: right;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield from super().compose()
        # Footer recomposes on binding changes, so initialize every new label.
        yield Static(f"Status: {self.status}", id="status-label", markup=False)

    def set_status(self, status: str) -> None:
        """Update the footer status text"""
        self.status = status
