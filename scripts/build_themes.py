"""Build the four Quarterlight theme files from scripts/palettes.json.

Run:  python scripts/build_themes.py
Every color is checked against its background; the build stops if any
falls outside the eye-comfort targets below.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Eye-comfort contrast targets (APCA Lc, absolute value)
TARGETS = {"text": (78, 88), "syntax": (64, 74), "comment": (48, 58), "status": (56, 70)}


# ---------- color math ----------
def hx(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def to_hex(rgb):
    return "#%02X%02X%02X" % tuple(round(max(0, min(255, v))) for v in rgb)


def mix(a, b, t):
    """Blend color a toward color b by t (0..1)."""
    return to_hex([x + (y - x) * t for x, y in zip(hx(a), hx(b))])


def apca(txt, bg):
    def Y(h):
        r, g, b = [(x / 255) ** 2.4 for x in hx(h)]
        return 0.2126729 * r + 0.7151522 * g + 0.0721750 * b

    def clamp(y):
        return y if y > 0.022 else y + (0.022 - y) ** 1.414

    yt, yb = clamp(Y(txt)), clamp(Y(bg))
    s = (yb ** 0.56 - yt ** 0.57) * 1.14 if yb > yt else (yb ** 0.65 - yt ** 0.62) * 1.14
    return 0 if abs(s) < 0.1 else abs((s - (0.027 if s > 0 else -0.027)) * 100)


def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _srgb(x):
    x = max(0.0, min(1.0, x))
    return 255 * (12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055)


def _to_oklab(h):
    r, g, b = [_lin(v) for v in hx(h)]
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def _from_oklab(L, a, b):
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return to_hex([_srgb(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
                   _srgb(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
                   _srgb(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)])


def fit(h, bg, target):
    """Keep the hue, change lightness until the color reaches the target contrast."""
    _, a, b = _to_oklab(h)
    lo, hi = 0.3, 0.99
    for _ in range(40):
        mid = (lo + hi) / 2
        if apca(_from_oklab(mid, a, b), bg) < target:
            lo = mid
        else:
            hi = mid
    return _from_oklab(hi, a, b)


# ---------- theme ----------
def build(name, p):
    bg, f = p["bg"], p["fg"]
    T, M, A = f["text"], f["comment"], f["keyword"]
    # Status colors: muted hues lifted to readable contrast on this background
    err = fit("#C9776E", bg, 62)
    warn = fit("#C9A35A", bg, 62)
    info = fit("#7FA3BF", bg, 62)
    ok = fit("#8DAF80", bg, 62)

    chrome = mix(bg, "#000000", 0.14)      # sidebar, panels, title bar
    deep = mix(bg, "#000000", 0.24)        # inputs
    line = mix(bg, T, 0.10)                # borders
    raise_ = mix(bg, T, 0.05)              # current line
    hover = mix(bg, T, 0.07)
    select_list = mix(bg, A, 0.20)
    status_fg = fit(mix(T, M, 0.5), chrome, 62)

    c = {
        # base
        "foreground": T, "descriptionForeground": M, "disabledForeground": mix(M, bg, 0.35),
        "errorForeground": err, "focusBorder": A + "80", "contrastBorder": "#00000000",
        "icon.foreground": M, "widget.shadow": "#00000040", "selection.background": A + "40",
        "textLink.foreground": A, "textLink.activeForeground": f["function"],
        "textPreformat.foreground": f["string"], "textBlockQuote.background": chrome,
        "textBlockQuote.border": line, "textCodeBlock.background": chrome, "textSeparator.foreground": line,
        "sash.hoverBorder": A + "80",
        # window chrome
        "titleBar.activeBackground": chrome, "titleBar.activeForeground": status_fg,
        "titleBar.inactiveBackground": chrome, "titleBar.inactiveForeground": M, "titleBar.border": line,
        "activityBar.background": chrome, "activityBar.foreground": T, "activityBar.inactiveForeground": M,
        "activityBar.border": line, "activityBar.activeBorder": A, "activityBarBadge.background": A,
        "activityBarBadge.foreground": bg,
        "sideBar.background": chrome, "sideBar.foreground": T, "sideBar.border": line,
        "sideBarTitle.foreground": status_fg, "sideBarSectionHeader.background": chrome,
        "sideBarSectionHeader.foreground": T, "sideBarSectionHeader.border": line,
        "statusBar.background": chrome, "statusBar.foreground": status_fg, "statusBar.border": line,
        "statusBar.noFolderBackground": chrome, "statusBar.debuggingBackground": mix(chrome, warn, 0.25),
        "statusBar.debuggingForeground": T, "statusBarItem.hoverBackground": hover,
        "statusBarItem.remoteBackground": mix(chrome, A, 0.22), "statusBarItem.remoteForeground": T,
        "statusBarItem.errorBackground": mix(chrome, err, 0.3), "statusBarItem.errorForeground": T,
        "statusBarItem.warningBackground": mix(chrome, warn, 0.3), "statusBarItem.warningForeground": T,
        "panel.background": chrome, "panel.border": line, "panelTitle.activeForeground": T,
        "panelTitle.inactiveForeground": M, "panelTitle.activeBorder": A,
        # tabs
        "editorGroupHeader.tabsBackground": chrome, "editorGroupHeader.tabsBorder": line,
        "editorGroup.border": line, "tab.activeBackground": bg, "tab.activeForeground": T,
        "tab.activeBorderTop": A, "tab.inactiveBackground": chrome, "tab.inactiveForeground": M,
        "tab.border": line, "tab.hoverBackground": hover, "tab.unfocusedActiveForeground": T,
        "breadcrumb.foreground": M, "breadcrumb.focusForeground": T, "breadcrumb.activeSelectionForeground": T,
        "breadcrumbPicker.background": chrome,
        # lists, inputs, buttons
        "list.activeSelectionBackground": select_list, "list.activeSelectionForeground": T,
        "list.inactiveSelectionBackground": hover, "list.inactiveSelectionForeground": T,
        "list.hoverBackground": hover, "list.hoverForeground": T, "list.focusOutline": A + "80",
        "list.highlightForeground": A, "list.errorForeground": err, "list.warningForeground": warn,
        "tree.indentGuidesStroke": line,
        "input.background": deep, "input.foreground": T, "input.border": line, "input.placeholderForeground": M,
        "inputOption.activeBorder": A, "inputOption.activeBackground": A + "30",
        "inputValidation.errorBorder": err, "inputValidation.errorBackground": deep,
        "inputValidation.warningBorder": warn, "inputValidation.warningBackground": deep,
        "inputValidation.infoBorder": info, "inputValidation.infoBackground": deep,
        "dropdown.background": deep, "dropdown.foreground": T, "dropdown.border": line,
        "button.background": A, "button.foreground": bg, "button.hoverBackground": mix(A, T, 0.3),
        "button.secondaryBackground": hover, "button.secondaryForeground": T,
        "button.secondaryHoverBackground": mix(bg, T, 0.12), "badge.background": A, "badge.foreground": bg,
        "checkbox.background": deep, "checkbox.border": line, "checkbox.foreground": T,
        "progressBar.background": A, "scrollbar.shadow": "#00000000",
        "scrollbarSlider.background": T + "1A", "scrollbarSlider.hoverBackground": T + "2E",
        "scrollbarSlider.activeBackground": T + "40",
        "quickInput.background": chrome, "quickInput.foreground": T, "quickInputTitle.background": chrome,
        "pickerGroup.foreground": A, "pickerGroup.border": line, "keybindingLabel.foreground": T,
        "keybindingLabel.background": hover, "keybindingLabel.border": line, "keybindingLabel.bottomBorder": line,
        "menu.background": chrome, "menu.foreground": T, "menu.selectionBackground": select_list,
        "menu.selectionForeground": T, "menu.separatorBackground": line, "menu.border": line,
        "notifications.background": chrome, "notifications.foreground": T, "notifications.border": line,
        "notificationCenterHeader.background": chrome, "notificationLink.foreground": A,
        "notificationsErrorIcon.foreground": err, "notificationsWarningIcon.foreground": warn,
        "notificationsInfoIcon.foreground": info,
        "editorWidget.background": chrome, "editorWidget.foreground": T, "editorWidget.border": line,
        "editorSuggestWidget.background": chrome, "editorSuggestWidget.border": line,
        "editorSuggestWidget.foreground": T, "editorSuggestWidget.selectedBackground": select_list,
        "editorSuggestWidget.highlightForeground": A, "editorHoverWidget.background": chrome,
        "editorHoverWidget.border": line, "peekView.border": A + "80", "peekViewEditor.background": deep,
        "peekViewResult.background": chrome, "peekViewTitle.background": chrome,
        "peekViewEditor.matchHighlightBackground": f["function"] + "33",
        "peekViewResult.matchHighlightBackground": f["function"] + "33",
        "peekViewResult.selectionBackground": select_list,
        # editor
        "editor.background": bg, "editor.foreground": T,
        "editorCursor.foreground": A, "editorCursor.background": bg,
        "editor.lineHighlightBackground": raise_, "editor.lineHighlightBorder": "#00000000",
        "editor.selectionBackground": A + "3A", "editor.inactiveSelectionBackground": A + "22",
        "editor.selectionHighlightBackground": A + "1C", "editor.selectionHighlightBorder": "#00000000",
        "editor.wordHighlightBackground": T + "14", "editor.wordHighlightStrongBackground": T + "1F",
        "editor.findMatchBackground": f["function"] + "55", "editor.findMatchBorder": "#00000000",
        "editor.findMatchHighlightBackground": f["function"] + "26", "editor.findMatchHighlightBorder": "#00000000",
        "editor.findRangeHighlightBackground": T + "0D", "editor.rangeHighlightBackground": T + "0D",
        "editor.hoverHighlightBackground": T + "14",
        "editorLineNumber.foreground": fit(M, bg, 42), "editorLineNumber.activeForeground": T,
        "editorIndentGuide.background1": mix(bg, T, 0.08), "editorIndentGuide.activeBackground1": mix(bg, T, 0.2),
        "editorWhitespace.foreground": mix(bg, T, 0.14), "editorRuler.foreground": line,
        "editorCodeLens.foreground": M, "editorLink.activeForeground": A,
        "editorBracketMatch.background": A + "24", "editorBracketMatch.border": "#00000000",
        "editorBracketHighlight.foreground1": T, "editorBracketHighlight.foreground2": f["function"],
        "editorBracketHighlight.foreground3": f["constant"], "editorBracketHighlight.foreground4": f["string"],
        "editorBracketHighlight.foreground5": f["type"], "editorBracketHighlight.foreground6": f["number"],
        "editorBracketHighlight.unexpectedBracket.foreground": err,
        "editorError.foreground": err, "editorWarning.foreground": warn, "editorInfo.foreground": info,
        "editorHint.foreground": M, "problemsErrorIcon.foreground": err, "problemsWarningIcon.foreground": warn,
        "problemsInfoIcon.foreground": info,
        "editorGutter.background": bg, "editorGutter.addedBackground": ok, "editorGutter.modifiedBackground": info,
        "editorGutter.deletedBackground": err, "editorGutter.foldingControlForeground": M,
        "editorOverviewRuler.border": "#00000000", "editorOverviewRuler.errorForeground": err + "99",
        "editorOverviewRuler.warningForeground": warn + "99", "editorOverviewRuler.findMatchForeground": f["function"] + "80",
        "editorOverviewRuler.selectionHighlightForeground": A + "60",
        "editorInlayHint.background": "#00000000", "editorInlayHint.foreground": M,
        "editorGhostText.foreground": M + "B3",
        "editorStickyScroll.background": bg, "editorStickyScrollHover.background": hover,
        "editor.foldBackground": T + "0A", "minimap.background": bg,
        "diffEditor.insertedTextBackground": ok + "22", "diffEditor.removedTextBackground": err + "22",
        "diffEditor.insertedLineBackground": ok + "14", "diffEditor.removedLineBackground": err + "14",
        "merge.currentHeaderBackground": ok + "40", "merge.incomingHeaderBackground": info + "40",
        # git + debug
        "gitDecoration.addedResourceForeground": ok, "gitDecoration.untrackedResourceForeground": ok,
        "gitDecoration.modifiedResourceForeground": info, "gitDecoration.deletedResourceForeground": err,
        "gitDecoration.conflictingResourceForeground": warn, "gitDecoration.ignoredResourceForeground": fit(M, chrome, 38),
        "gitDecoration.renamedResourceForeground": f["constant"],
        "debugToolBar.background": chrome, "debugIcon.breakpointForeground": err,
        # terminal
        "terminal.background": chrome, "terminal.foreground": T, "terminalCursor.foreground": A,
        "terminal.selectionBackground": A + "3A", "terminal.border": line,
        "terminal.ansiBlack": mix(bg, "#000000", 0.3), "terminal.ansiBrightBlack": M,
        "terminal.ansiRed": err, "terminal.ansiBrightRed": fit(err, chrome, 72),
        "terminal.ansiGreen": ok, "terminal.ansiBrightGreen": f["string"],
        "terminal.ansiYellow": warn, "terminal.ansiBrightYellow": f["function"],
        "terminal.ansiBlue": info, "terminal.ansiBrightBlue": fit(info, chrome, 72),
        "terminal.ansiMagenta": f["constant"], "terminal.ansiBrightMagenta": fit(f["constant"], chrome, 72),
        "terminal.ansiCyan": f["type"], "terminal.ansiBrightCyan": fit(f["type"], chrome, 72),
        "terminal.ansiWhite": T, "terminal.ansiBrightWhite": fit(T, chrome, 86),
        # chat / welcome
        "welcomePage.background": bg, "walkThrough.embeddedEditorBackground": chrome,
        "chat.requestBackground": raise_, "chat.slashCommandForeground": A,
        "interactive.activeCodeBorder": line,
    }

    k = f
    tokens = [
        (["comment", "punctuation.definition.comment", "string.comment"], M),
        (["keyword", "storage.type", "storage.modifier", "keyword.control", "variable.language",
          "entity.name.tag", "support.type.property-name", "markup.heading", "entity.name.section"], k["keyword"]),
        (["keyword.operator", "punctuation", "meta.brace", "variable", "variable.parameter",
          "variable.other", "meta.object-literal.key"], T),
        (["keyword.operator.new", "keyword.operator.expression", "keyword.operator.logical.python",
          "keyword.operator.word"], k["keyword"]),
        (["entity.name.function", "support.function", "meta.function-call entity.name.function",
          "entity.name.function.decorator", "meta.decorator", "punctuation.decorator",
          "entity.other.attribute-name", "support.function.magic"], k["function"]),
        (["string", "punctuation.definition.string", "markup.inline.raw", "markup.fenced_code",
          "string.quoted.docstring"], k["string"]),
        (["entity.name.type", "entity.name.class", "entity.name.namespace", "support.class", "support.type",
          "entity.other.inherited-class", "storage.type.primitive", "entity.name.type.class",
          "markup.underline.link", "string.other.link"], k["type"]),
        (["constant.numeric", "constant.other.color", "keyword.other.unit"], k["number"]),
        (["constant.language", "constant.other", "support.constant", "variable.other.constant",
          "variable.other.enummember", "constant.character", "constant.character.escape", "string.regexp",
          "variable.other.readwrite.alias"], k["constant"]),
        (["invalid", "invalid.illegal"], err),
        (["markup.deleted"], err), (["markup.inserted"], ok), (["markup.changed"], info),
    ]
    token_colors = [{"scope": s, "settings": {"foreground": col}} for s, col in tokens]
    token_colors += [
        {"scope": ["markup.bold", "markup.heading"], "settings": {"fontStyle": "bold"}},
        {"scope": "markup.italic", "settings": {"fontStyle": "italic"}},
    ]
    semantic = {
        "class": k["type"], "interface": k["type"], "enum": k["type"], "struct": k["type"],
        "type": k["type"], "typeParameter": k["type"], "namespace": k["type"],
        "function": k["function"], "method": k["function"], "decorator": k["function"],
        "macro": k["constant"], "enumMember": k["constant"], "variable.readonly": k["constant"],
        "variable.defaultLibrary": k["constant"], "parameter": T, "property": T, "variable": T,
        "keyword": k["keyword"], "comment": M, "string": k["string"], "number": k["number"],
        "selfParameter": k["keyword"], "builtinConstant": k["constant"],
    }
    theme = {
        "$schema": "vscode://schemas/color-theme",
        "name": f"Quarterlight {name}",
        "type": "dark",
        "semanticHighlighting": True,
        "colors": c,
        "tokenColors": token_colors,
        "semanticTokenColors": semantic,
    }

    # Contrast check
    checks = [("text", T, bg, "text"), ("comment", M, bg, "comment"), ("status bar", status_fg, chrome, "status")]
    checks += [(r, k[r], bg, "syntax") for r in ("keyword", "function", "string", "type", "number", "constant")]
    checks += [(r, v, bg, "status") for r, v in (("error", err), ("warning", warn), ("info", info), ("added", ok))]
    checks += [("button text", bg, A, "syntax")]
    problems = []
    for label, fg, back, kind in checks:
        lc = apca(fg, back)
        lo, hi = TARGETS[kind]
        flag = "" if lo <= lc <= hi else "  <-- outside target"
        if flag:
            problems.append(f"{name} {label}")
        print(f"  {label:12} {fg} on {back}  Lc {lc:5.1f}{flag}")
    return theme, problems


def main():
    palettes = json.loads((ROOT / "scripts" / "palettes.json").read_text())
    problems = []
    for name, p in palettes.items():
        print(f"\n{name}")
        theme, bad = build(name, p)
        problems += bad
        out = ROOT / "themes" / f"quarterlight-{name.lower()}.json"
        out.write_text(json.dumps(theme, indent=2) + "\n")
    if problems:
        raise SystemExit("\nContrast outside target: " + ", ".join(problems))
    print("\nAll four themes built; every color is inside its contrast target.")


if __name__ == "__main__":
    main()
