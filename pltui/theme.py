from textual.theme import Theme


PULUMI_SOFT_THEME = Theme(
    name="pulumi-soft",
    primary="#8A3391",
    secondary="#F78C6B",
    warning="#F78C6B",
    error="#C7323F",
    success="#8DCCED",
    accent="#FEAE43",
    foreground="#D7E2F0",
    background="#111827",
    surface="#202C3E",
    panel="#1A2433",
    boost="#0F1725",
    dark=True,
    luminosity_spread=0.12,
    text_alpha=0.95,
    variables={
        "pl_bg": "#111827",
        "pl_panel": "#1A2433",
        "pl_surface": "#202C3E",
        "pl_border": "#3A5678",
        "pl_accent": "#4C92C8",
        "pl_accent_soft": "#6F8FBD",
        "pl_text": "#D7E2F0",
        "pl_muted": "#8EA3BC",
        "pl_violet": "#8A3391",
        "pl_magenta": "#C7323F",
        "pl_orange": "#F78C6B",
        "pl_gold": "#F2D058",
    },
)
