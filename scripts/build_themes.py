"""Build the four Quarterlight theme files from scripts/palettes.json.

Run:  python scripts/build_themes.py

Every color is checked against its background first. Theme files are only
written when all of them land inside the eye-comfort targets below.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PALETTES = ROOT / "scripts" / "palettes.json"
THEMES = ROOT / "themes"

# Eye-comfort contrast targets as APCA Lc ranges (absolute value).
TARGETS = {"text": (78, 88), "syntax": (64, 74), "comment": (48, 58), "status": (56, 70)}
SYNTAX_ROLES = ("keyword", "function", "string", "type", "number", "constant")


# ---------- color math ----------
def rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def to_hex(channels):
    return "#" + "".join(f"{round(min(255, max(0, c))):02X}" for c in channels)


def mix(a, b, t):
    """Blend color a toward color b by t (0..1)."""
    return to_hex(x + (y - x) * t for x, y in zip(rgb(a), rgb(b)))


def apca(text, bg):
    """APCA lightness contrast (Lc) of text on bg, as an absolute value."""
    def luminance(h):
        r, g, b = ((c / 255) ** 2.4 for c in rgb(h))
        y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
        return y if y > 0.022 else y + (0.022 - y) ** 1.414

    yt, yb = luminance(text), luminance(bg)
    if yb > yt:
        s = (yb ** 0.56 - yt ** 0.57) * 1.14
    else:
        s = (yb ** 0.65 - yt ** 0.62) * 1.14
    return 0 if abs(s) < 0.1 else (abs(s) - 0.027) * 100


def _linear(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gamma(x):
    x = min(1.0, max(0.0, x))
    return 255 * (12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055)


def to_oklab(h):
    r, g, b = (_linear(c) for c in rgb(h))
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def from_oklab(L, a, b):
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return to_hex(_gamma(c) for c in (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s))


def fit(h, bg, target):
    """Keep the hue, and find the lightness where the color reaches the target contrast."""
    _, a, b = to_oklab(h)
    lo, hi = 0.3, 0.99
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if apca(from_oklab(mid, a, b), bg) < target else (lo, mid)
    return from_oklab(hi, a, b)


# ---------- theme ----------
def build(name, palette):
    """Return (theme, contrast checks) for one season."""
    bg, fg = palette["bg"], palette["fg"]
    text, muted, accent = fg["text"], fg["comment"], fg["keyword"]
    keyword, function, string, type_, number, constant = (fg[r] for r in SYNTAX_ROLES)

    # Status colors: muted hues lifted to readable contrast on this background.
    err, warn, info, ok = (fit(h, bg, 62) for h in ("#C9776E", "#C9A35A", "#7FA3BF", "#8DAF80"))

    chrome = mix(bg, "#000000", 0.14)      # sidebar, panels, title bar
    deep = mix(bg, "#000000", 0.24)        # inputs
    line = mix(bg, text, 0.10)             # borders
    current_line = mix(bg, text, 0.05)
    hover = mix(bg, text, 0.07)
    list_selection = mix(bg, accent, 0.20)
    status_fg = fit(mix(text, muted, 0.5), chrome, 62)
    clear = "#00000000"

    colors = {
        # base
        "foreground": text, "descriptionForeground": muted, "disabledForeground": mix(muted, bg, 0.35),
        "errorForeground": err, "focusBorder": accent + "80", "contrastBorder": clear,
        "icon.foreground": muted, "widget.shadow": "#00000040", "selection.background": accent + "40",
        "textLink.foreground": accent, "textLink.activeForeground": function,
        "textPreformat.foreground": string, "textBlockQuote.background": chrome,
        "textBlockQuote.border": line, "textCodeBlock.background": chrome, "textSeparator.foreground": line,
        "sash.hoverBorder": accent + "80",
        # window chrome
        "titleBar.activeBackground": chrome, "titleBar.activeForeground": status_fg,
        "titleBar.inactiveBackground": chrome, "titleBar.inactiveForeground": muted, "titleBar.border": line,
        "activityBar.background": chrome, "activityBar.foreground": text, "activityBar.inactiveForeground": muted,
        "activityBar.border": line, "activityBar.activeBorder": accent, "activityBarBadge.background": accent,
        "activityBarBadge.foreground": bg,
        "sideBar.background": chrome, "sideBar.foreground": text, "sideBar.border": line,
        "sideBarTitle.foreground": status_fg, "sideBarSectionHeader.background": chrome,
        "sideBarSectionHeader.foreground": text, "sideBarSectionHeader.border": line,
        "statusBar.background": chrome, "statusBar.foreground": status_fg, "statusBar.border": line,
        "statusBar.noFolderBackground": chrome, "statusBar.debuggingBackground": mix(chrome, warn, 0.25),
        "statusBar.debuggingForeground": text, "statusBarItem.hoverBackground": hover,
        "statusBarItem.remoteBackground": mix(chrome, accent, 0.22), "statusBarItem.remoteForeground": text,
        "statusBarItem.errorBackground": mix(chrome, err, 0.3), "statusBarItem.errorForeground": text,
        "statusBarItem.warningBackground": mix(chrome, warn, 0.3), "statusBarItem.warningForeground": text,
        "panel.background": chrome, "panel.border": line, "panelTitle.activeForeground": text,
        "panelTitle.inactiveForeground": muted, "panelTitle.activeBorder": accent,
        # tabs
        "editorGroupHeader.tabsBackground": chrome, "editorGroupHeader.tabsBorder": line,
        "editorGroup.border": line, "tab.activeBackground": bg, "tab.activeForeground": text,
        "tab.activeBorderTop": accent, "tab.inactiveBackground": chrome, "tab.inactiveForeground": muted,
        "tab.border": line, "tab.hoverBackground": hover, "tab.unfocusedActiveForeground": text,
        "breadcrumb.foreground": muted, "breadcrumb.focusForeground": text,
        "breadcrumb.activeSelectionForeground": text, "breadcrumbPicker.background": chrome,
        # lists, inputs, buttons
        "list.activeSelectionBackground": list_selection, "list.activeSelectionForeground": text,
        "list.inactiveSelectionBackground": hover, "list.inactiveSelectionForeground": text,
        "list.hoverBackground": hover, "list.hoverForeground": text, "list.focusOutline": accent + "80",
        "list.highlightForeground": accent, "list.errorForeground": err, "list.warningForeground": warn,
        "tree.indentGuidesStroke": line,
        "input.background": deep, "input.foreground": text, "input.border": line,
        "input.placeholderForeground": muted,
        "inputOption.activeBorder": accent, "inputOption.activeBackground": accent + "30",
        "inputValidation.errorBorder": err, "inputValidation.errorBackground": deep,
        "inputValidation.warningBorder": warn, "inputValidation.warningBackground": deep,
        "inputValidation.infoBorder": info, "inputValidation.infoBackground": deep,
        "dropdown.background": deep, "dropdown.foreground": text, "dropdown.border": line,
        "button.background": accent, "button.foreground": bg, "button.hoverBackground": mix(accent, text, 0.3),
        "button.secondaryBackground": hover, "button.secondaryForeground": text,
        "button.secondaryHoverBackground": mix(bg, text, 0.12), "badge.background": accent, "badge.foreground": bg,
        "checkbox.background": deep, "checkbox.border": line, "checkbox.foreground": text,
        "progressBar.background": accent, "scrollbar.shadow": clear,
        "scrollbarSlider.background": text + "1A", "scrollbarSlider.hoverBackground": text + "2E",
        "scrollbarSlider.activeBackground": text + "40",
        "quickInput.background": chrome, "quickInput.foreground": text, "quickInputTitle.background": chrome,
        "pickerGroup.foreground": accent, "pickerGroup.border": line, "keybindingLabel.foreground": text,
        "keybindingLabel.background": hover, "keybindingLabel.border": line, "keybindingLabel.bottomBorder": line,
        "menu.background": chrome, "menu.foreground": text, "menu.selectionBackground": list_selection,
        "menu.selectionForeground": text, "menu.separatorBackground": line, "menu.border": line,
        "notifications.background": chrome, "notifications.foreground": text, "notifications.border": line,
        "notificationCenterHeader.background": chrome, "notificationLink.foreground": accent,
        "notificationsErrorIcon.foreground": err, "notificationsWarningIcon.foreground": warn,
        "notificationsInfoIcon.foreground": info,
        "editorWidget.background": chrome, "editorWidget.foreground": text, "editorWidget.border": line,
        "editorSuggestWidget.background": chrome, "editorSuggestWidget.border": line,
        "editorSuggestWidget.foreground": text, "editorSuggestWidget.selectedBackground": list_selection,
        "editorSuggestWidget.highlightForeground": accent, "editorHoverWidget.background": chrome,
        "editorHoverWidget.border": line, "peekView.border": accent + "80", "peekViewEditor.background": deep,
        "peekViewResult.background": chrome, "peekViewTitle.background": chrome,
        "peekViewEditor.matchHighlightBackground": function + "33",
        "peekViewResult.matchHighlightBackground": function + "33",
        "peekViewResult.selectionBackground": list_selection,
        # editor
        "editor.background": bg, "editor.foreground": text,
        "editorCursor.foreground": accent, "editorCursor.background": bg,
        "editor.lineHighlightBackground": current_line, "editor.lineHighlightBorder": clear,
        "editor.selectionBackground": accent + "3A", "editor.inactiveSelectionBackground": accent + "22",
        "editor.selectionHighlightBackground": accent + "1C", "editor.selectionHighlightBorder": clear,
        "editor.wordHighlightBackground": text + "14", "editor.wordHighlightStrongBackground": text + "1F",
        "editor.findMatchBackground": function + "55", "editor.findMatchBorder": clear,
        "editor.findMatchHighlightBackground": function + "26", "editor.findMatchHighlightBorder": clear,
        "editor.findRangeHighlightBackground": text + "0D", "editor.rangeHighlightBackground": text + "0D",
        "editor.hoverHighlightBackground": text + "14",
        "editorLineNumber.foreground": fit(muted, bg, 42), "editorLineNumber.activeForeground": text,
        "editorIndentGuide.background1": mix(bg, text, 0.08),
        "editorIndentGuide.activeBackground1": mix(bg, text, 0.2),
        "editorWhitespace.foreground": mix(bg, text, 0.14), "editorRuler.foreground": line,
        "editorCodeLens.foreground": muted, "editorLink.activeForeground": accent,
        "editorBracketMatch.background": accent + "24", "editorBracketMatch.border": clear,
        "editorBracketHighlight.foreground1": text, "editorBracketHighlight.foreground2": function,
        "editorBracketHighlight.foreground3": constant, "editorBracketHighlight.foreground4": string,
        "editorBracketHighlight.foreground5": type_, "editorBracketHighlight.foreground6": number,
        "editorBracketHighlight.unexpectedBracket.foreground": err,
        "editorError.foreground": err, "editorWarning.foreground": warn, "editorInfo.foreground": info,
        "editorHint.foreground": muted, "problemsErrorIcon.foreground": err,
        "problemsWarningIcon.foreground": warn, "problemsInfoIcon.foreground": info,
        "editorGutter.background": bg, "editorGutter.addedBackground": ok,
        "editorGutter.modifiedBackground": info, "editorGutter.deletedBackground": err,
        "editorGutter.foldingControlForeground": muted,
        "editorOverviewRuler.border": clear, "editorOverviewRuler.errorForeground": err + "99",
        "editorOverviewRuler.warningForeground": warn + "99",
        "editorOverviewRuler.findMatchForeground": function + "80",
        "editorOverviewRuler.selectionHighlightForeground": accent + "60",
        "editorInlayHint.background": clear, "editorInlayHint.foreground": muted,
        "editorGhostText.foreground": muted + "B3",
        "editorStickyScroll.background": bg, "editorStickyScrollHover.background": hover,
        "editor.foldBackground": text + "0A", "minimap.background": bg,
        "diffEditor.insertedTextBackground": ok + "22", "diffEditor.removedTextBackground": err + "22",
        "diffEditor.insertedLineBackground": ok + "14", "diffEditor.removedLineBackground": err + "14",
        "merge.currentHeaderBackground": ok + "40", "merge.incomingHeaderBackground": info + "40",
        # git + debug
        "gitDecoration.addedResourceForeground": ok, "gitDecoration.untrackedResourceForeground": ok,
        "gitDecoration.modifiedResourceForeground": info, "gitDecoration.deletedResourceForeground": err,
        "gitDecoration.conflictingResourceForeground": warn,
        "gitDecoration.ignoredResourceForeground": fit(muted, chrome, 38),
        "gitDecoration.renamedResourceForeground": constant,
        "debugToolBar.background": chrome, "debugIcon.breakpointForeground": err,
        # terminal
        "terminal.background": chrome, "terminal.foreground": text, "terminalCursor.foreground": accent,
        "terminal.selectionBackground": accent + "3A", "terminal.border": line,
        "terminal.ansiBlack": mix(bg, "#000000", 0.3), "terminal.ansiBrightBlack": muted,
        "terminal.ansiRed": err, "terminal.ansiBrightRed": fit(err, chrome, 72),
        "terminal.ansiGreen": ok, "terminal.ansiBrightGreen": string,
        "terminal.ansiYellow": warn, "terminal.ansiBrightYellow": function,
        "terminal.ansiBlue": info, "terminal.ansiBrightBlue": fit(info, chrome, 72),
        "terminal.ansiMagenta": constant, "terminal.ansiBrightMagenta": fit(constant, chrome, 72),
        "terminal.ansiCyan": type_, "terminal.ansiBrightCyan": fit(type_, chrome, 72),
        "terminal.ansiWhite": text, "terminal.ansiBrightWhite": fit(text, chrome, 86),
        # chat / welcome
        "welcomePage.background": bg, "walkThrough.embeddedEditorBackground": chrome,
        "chat.requestBackground": current_line, "chat.slashCommandForeground": accent,
        "interactive.activeCodeBorder": line,
    }

    scopes = [
        (["comment", "punctuation.definition.comment", "string.comment"], muted),
        (["keyword", "storage.type", "storage.modifier", "keyword.control", "variable.language",
          "entity.name.tag", "support.type.property-name", "markup.heading", "entity.name.section"], keyword),
        (["keyword.operator", "punctuation", "meta.brace", "variable", "variable.parameter",
          "variable.other", "meta.object-literal.key"], text),
        (["keyword.operator.new", "keyword.operator.expression", "keyword.operator.logical.python",
          "keyword.operator.word"], keyword),
        (["entity.name.function", "support.function", "meta.function-call entity.name.function",
          "entity.name.function.decorator", "meta.decorator", "punctuation.decorator",
          "entity.other.attribute-name", "support.function.magic"], function),
        (["string", "punctuation.definition.string", "markup.inline.raw", "markup.fenced_code",
          "string.quoted.docstring"], string),
        (["entity.name.type", "entity.name.class", "entity.name.namespace", "support.class", "support.type",
          "entity.other.inherited-class", "storage.type.primitive", "entity.name.type.class",
          "markup.underline.link", "string.other.link"], type_),
        (["constant.numeric", "constant.other.color", "keyword.other.unit"], number),
        (["constant.language", "constant.other", "support.constant", "variable.other.constant",
          "variable.other.enummember", "constant.character", "constant.character.escape", "string.regexp",
          "variable.other.readwrite.alias"], constant),
        (["invalid", "invalid.illegal"], err),
        (["markup.deleted"], err), (["markup.inserted"], ok), (["markup.changed"], info),
    ]
    token_colors = [{"scope": s, "settings": {"foreground": c}} for s, c in scopes] + [
        {"scope": ["markup.bold", "markup.heading"], "settings": {"fontStyle": "bold"}},
        {"scope": "markup.italic", "settings": {"fontStyle": "italic"}},
    ]
    semantic = {
        "class": type_, "interface": type_, "enum": type_, "struct": type_,
        "type": type_, "typeParameter": type_, "namespace": type_,
        "function": function, "method": function, "decorator": function,
        "macro": constant, "enumMember": constant, "variable.readonly": constant,
        "variable.defaultLibrary": constant, "parameter": text, "property": text, "variable": text,
        "keyword": keyword, "comment": muted, "string": string, "number": number,
        "selfParameter": keyword, "builtinConstant": constant,
    }
    theme = {
        "$schema": "vscode://schemas/color-theme",
        "name": f"Quarterlight {name}",
        "type": "dark",
        "semanticHighlighting": True,
        "colors": colors,
        "tokenColors": token_colors,
        "semanticTokenColors": semantic,
    }

    checks = [("text", text, bg, "text"), ("comment", muted, bg, "comment"),
              ("status bar", status_fg, chrome, "status")]
    checks += [(role, fg[role], bg, "syntax") for role in SYNTAX_ROLES]
    checks += [(label, c, bg, "status") for label, c in
               (("error", err), ("warning", warn), ("info", info), ("added", ok))]
    checks.append(("button text", bg, accent, "syntax"))
    return theme, checks


def main():
    palettes = json.loads(PALETTES.read_text(encoding="utf-8"))
    themes, problems = {}, []
    for name, palette in palettes.items():
        print(f"\n{name}")
        themes[name], checks = build(name, palette)
        for label, fg, back, kind in checks:
            lc = apca(fg, back)
            lo, hi = TARGETS[kind]
            inside = lo <= lc <= hi
            if not inside:
                problems.append(f"{name} {label}")
            print(f"  {label:12} {fg} on {back}  Lc {lc:5.1f}{'' if inside else '  <-- outside target'}")

    if problems:
        raise SystemExit("\nNo files written. Contrast outside target: " + ", ".join(problems))

    THEMES.mkdir(exist_ok=True)
    for name, theme in themes.items():
        (THEMES / f"quarterlight-{name.lower()}.json").write_text(
            json.dumps(theme, indent=2) + "\n", encoding="utf-8")
    print(f"\nAll {len(themes)} themes built; every color is inside its contrast target.")


if __name__ == "__main__":
    main()
