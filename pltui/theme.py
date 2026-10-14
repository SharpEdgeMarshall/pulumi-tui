from textual.theme import Theme


PULUMI_THEME = Theme(
    name="pulumi",
    primary="#8A3391",
    secondary="#F26E7E",
    warning="#F7BF2A",
    error="#F26E7E",
    success="#F7BF2A",
    accent="#F7BF2A",
    foreground="#EDE9F7",
    background="#14101F",
    surface="#221A36",
    panel="#1B1529",
    boost="#100C19",
    dark=True,
    luminosity_spread=0.12,
    text_alpha=1.0,
)

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
)
