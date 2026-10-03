// Quarterlight: seasonal theme switching, eye-comfort settings and a 20-20-20 break reminder.
const vscode = require("vscode");
const fs = require("fs");
const os = require("os");
const path = require("path");

const SEASONS = ["Winter", "Spring", "Summer", "Autumn"];
const THEME_PREFIX = "Quarterlight ";
const FONT_PAGE = "https://fonts.google.com/specimen/Atkinson+Hyperlegible+Mono";
const FONT_STACK = "'Atkinson Hyperlegible Mono', 'Cascadia Mono', Consolas, 'SF Mono', Menlo, monospace";

// Settings applied by "Apply Eye-Comfort Settings". Each one is undone by "Restore My Previous Settings".
const COMFORT = {
  "editor.fontFamily": FONT_STACK,
  "editor.fontSize": 17,
  "editor.fontWeight": "500",
  "editor.lineHeight": 1.7,
  "editor.letterSpacing": 0.3,
  "editor.cursorBlinking": "solid",
  "editor.cursorWidth": 2,
  "editor.cursorSmoothCaretAnimation": "off",
  "editor.smoothScrolling": false,
  "workbench.list.smoothScrolling": false,
  "terminal.integrated.smoothScrolling": false,
  "workbench.reduceMotion": "on",
  "editor.minimap.enabled": false,
  "editor.renderLineHighlight": "line",
  "editor.occurrencesHighlight": "off",
  "editor.bracketPairColorization.enabled": false,
  "editor.guides.bracketPairs": false,
  "editor.hover.delay": 800,
  "editor.semanticHighlighting.enabled": true,
  "terminal.integrated.fontFamily": FONT_STACK,
  "terminal.integrated.fontSize": 16,
  "terminal.integrated.lineHeight": 1.3,
  "terminal.integrated.cursorBlinking": false,
};

let ctx;
let switchingTheme = false;
let statusItem;
let statusHideTimer;
let countdownTimer;

// ---------- seasons ----------
// Dates are compared as MMDD numbers, so "03-20" becomes 320 and October 3 becomes 1003.
function seasonFor(date, starts) {
  const today = (date.getMonth() + 1) * 100 + date.getDate();
  const [spring, summer, autumn, winter] = [starts.spring, starts.summer, starts.autumn, starts.winter]
    .map((mmdd) => Number(mmdd.replace("-", "")));
  if (today >= winter || today < spring) return "Winter";
  if (today < summer) return "Spring";
  if (today < autumn) return "Summer";
  return "Autumn";
}

function currentSeason() {
  const cfg = vscode.workspace.getConfiguration("quarterlight");
  const starts = Object.fromEntries(
    ["spring", "summer", "autumn", "winter"].map((s) => [s, cfg.get(`seasonStarts.${s}`)])
  );
  let season = seasonFor(new Date(), starts);
  if (cfg.get("southernHemisphere", false)) {
    season = SEASONS[(SEASONS.indexOf(season) + 2) % 4];
  }
  return season;
}

function activeTheme() {
  return vscode.workspace.getConfiguration("workbench").get("colorTheme", "");
}

async function setTheme(name) {
  if (activeTheme() === name) return;
  switchingTheme = true;
  try {
    await vscode.workspace.getConfiguration("workbench").update("colorTheme", name, vscode.ConfigurationTarget.Global);
  } finally {
    setTimeout(() => (switchingTheme = false), 1500);
  }
}

async function applySeason(force) {
  const cfg = vscode.workspace.getConfiguration("quarterlight");
  if (!force && !cfg.get("autoSeason", true)) return;
  // Only take over when a Quarterlight theme is already in use, so another theme you picked is left alone.
  if (!force && !activeTheme().startsWith(THEME_PREFIX)) return;
  await setTheme(THEME_PREFIX + currentSeason());
}

// ---------- comfort settings ----------
async function applyComfort() {
  const saved = ctx.globalState.get("ql.previousSettings") || {};
  for (const [key, value] of Object.entries(COMFORT)) {
    const dot = key.lastIndexOf(".");
    const section = vscode.workspace.getConfiguration(key.slice(0, dot));
    const leaf = key.slice(dot + 1);
    if (!(key in saved)) saved[key] = section.inspect(leaf)?.globalValue ?? null;
    await section.update(leaf, value, vscode.ConfigurationTarget.Global);
  }
  await ctx.globalState.update("ql.previousSettings", saved);
  if (!fontInstalled()) {
    const pick = await vscode.window.showInformationMessage(
      "Eye-comfort settings are on. The Atkinson Hyperlegible Mono font isn't on this computer yet, so a similar font is being used for now.",
      "Get the Font"
    );
    if (pick) await getFont();
  } else {
    vscode.window.showInformationMessage("Eye-comfort settings are on.");
  }
}

async function restoreComfort() {
  const saved = ctx.globalState.get("ql.previousSettings");
  if (!saved) {
    vscode.window.showInformationMessage("There are no saved settings to restore.");
    return;
  }
  for (const [key, value] of Object.entries(saved)) {
    const dot = key.lastIndexOf(".");
    await vscode.workspace
      .getConfiguration(key.slice(0, dot))
      .update(key.slice(dot + 1), value === null ? undefined : value, vscode.ConfigurationTarget.Global);
  }
  await ctx.globalState.update("ql.previousSettings", undefined);
  vscode.window.showInformationMessage("Your previous editor settings are back.");
}

// ---------- font ----------
function fontDirs() {
  const home = os.homedir();
  if (process.platform === "win32") {
    return [path.join(process.env.LOCALAPPDATA || path.join(home, "AppData", "Local"), "Microsoft", "Windows", "Fonts"),
      path.join(process.env.WINDIR || "C:\\Windows", "Fonts")];
  }
  if (process.platform === "darwin") return [path.join(home, "Library", "Fonts"), "/Library/Fonts"];
  return [path.join(home, ".local", "share", "fonts"), path.join(home, ".fonts"), "/usr/share/fonts", "/usr/local/share/fonts"];
}

function fontInstalled() {
  return fontDirs().some((dir) => {
    try {
      return fs.readdirSync(dir).some((f) => f.toLowerCase().startsWith("atkinsonhyperlegiblemono"));
    } catch {
      return false;
    }
  });
}

// Opens the free Google Fonts page; installing a font is left to the operating system.
async function getFont() {
  await vscode.env.openExternal(vscode.Uri.parse(FONT_PAGE));
  vscode.window.showInformationMessage(
    "On the page, click \"Get font\", then \"Download all\". Open the downloaded zip, right-click each .ttf file and choose Install. Then close and reopen VS Code."
  );
}

// ---------- 20-20-20 break reminder ----------
// The timing state lives in a shared file so several open VS Code windows don't all remind you at once.
function stateFile() {
  return path.join(ctx.globalStorageUri.fsPath, "break-state.json");
}

function readState() {
  try {
    return JSON.parse(fs.readFileSync(stateFile(), "utf8"));
  } catch {
    const now = Date.now();
    return { lastBreak: now, lastSeen: now, snoozeUntil: 0 };
  }
}

function writeState(s) {
  try {
    fs.mkdirSync(path.dirname(stateFile()), { recursive: true });
    fs.writeFileSync(stateFile(), JSON.stringify(s));
  } catch {
    /* a missed write only delays the next reminder */
  }
}

function breakTick() {
  const cfg = vscode.workspace.getConfiguration("quarterlight.breakReminder");
  if (!cfg.get("enabled", true) || !vscode.window.state.focused || countdownTimer) return;
  const now = Date.now();
  const s = readState();
  // Five minutes with no VS Code window in focus counts as a break.
  if (now - s.lastSeen > 5 * 60000) s.lastBreak = now;
  s.lastSeen = now;
  const due = now - s.lastBreak >= cfg.get("intervalMinutes", 20) * 60000 && now >= (s.snoozeUntil || 0);
  if (due) s.lastBreak = now; // claim this reminder before another window does
  writeState(s);
  if (due) remind();
}

async function remind() {
  const cfg = vscode.workspace.getConfiguration("quarterlight.breakReminder");
  if (cfg.get("style", "popup") === "statusBar") {
    showStatus("$(eye) Look away for 20 seconds", "quarterlight.startBreak", 60000);
    return;
  }
  const pick = await vscode.window.showInformationMessage(
    "20-20-20 break: look at something about 20 feet (6 m) away for 20 seconds, and blink slowly a few times.",
    "Start 20-Second Timer",
    "Snooze 5 Minutes",
    "Settings"
  );
  if (pick === "Start 20-Second Timer") startCountdown();
  if (pick === "Snooze 5 Minutes") {
    const s = readState();
    s.snoozeUntil = Date.now() + 5 * 60000;
    s.lastBreak = Date.now() - cfg.get("intervalMinutes", 20) * 60000; // due again as soon as the snooze ends
    writeState(s);
  }
  if (pick === "Settings") vscode.commands.executeCommand("workbench.action.openSettings", "quarterlight.breakReminder");
}

function startCountdown() {
  if (countdownTimer) return;
  let left = 20;
  showStatus(`$(eye) Look away… ${left}`);
  countdownTimer = setInterval(() => {
    left -= 1;
    if (left > 0) {
      showStatus(`$(eye) Look away… ${left}`);
      return;
    }
    clearInterval(countdownTimer);
    countdownTimer = undefined;
    const s = readState();
    s.lastBreak = Date.now();
    writeState(s);
    showStatus("$(check) Break done", undefined, 6000);
  }, 1000);
}

function showStatus(text, command, hideAfter) {
  clearTimeout(statusHideTimer); // a newer message must not be hidden by an older message's timer
  statusItem.text = text;
  statusItem.command = command;
  statusItem.tooltip = "Quarterlight 20-20-20 break";
  statusItem.show();
  if (hideAfter) statusHideTimer = setTimeout(() => statusItem.hide(), hideAfter);
}

// ---------- first run ----------
async function welcome() {
  const pick = await vscode.window.showInformationMessage(
    `Quarterlight is installed. Turn on the ${currentSeason()} theme and the eye-comfort settings (larger low-vision font, no blinking, no animations)?`,
    "Turn On Everything",
    "Theme Only",
    "Not Now"
  );
  if (pick === "Turn On Everything" || pick === "Theme Only") await applySeason(true);
  if (pick === "Turn On Everything") await applyComfort();
  if (pick) await ctx.globalState.update("ql.welcomed", true);
}

// Settings Sync carries the font setting to your other computers, but not the font itself.
// This key is not synced, so each computer is asked once.
async function offerFontOnThisComputer() {
  const family = vscode.workspace.getConfiguration("editor").get("fontFamily", "");
  if (!family.includes("Atkinson Hyperlegible Mono") || fontInstalled() || ctx.globalState.get("ql.fontAsked")) return;
  await ctx.globalState.update("ql.fontAsked", true);
  const pick = await vscode.window.showInformationMessage(
    "Your Quarterlight font settings came over from another computer, but the Atkinson Hyperlegible Mono font isn't installed on this one.",
    "Get the Font"
  );
  if (pick) await getFont();
}

// ---------- activation ----------
function activate(context) {
  ctx = context;
  context.globalState.setKeysForSync(["ql.welcomed"]);
  statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  context.subscriptions.push(statusItem);

  context.subscriptions.push(
    vscode.commands.registerCommand("quarterlight.useCurrentSeason", async () => {
      await vscode.workspace.getConfiguration("quarterlight").update("autoSeason", true, vscode.ConfigurationTarget.Global);
      await applySeason(true);
      vscode.window.showInformationMessage(`Quarterlight ${currentSeason()} is on, and it will change with the seasons.`);
    }),
    vscode.commands.registerCommand("quarterlight.applyComfortSettings", applyComfort),
    vscode.commands.registerCommand("quarterlight.restoreSettings", restoreComfort),
    vscode.commands.registerCommand("quarterlight.getFont", getFont),
    vscode.commands.registerCommand("quarterlight.startBreak", () => {
      statusItem.hide();
      startCountdown();
    }),
    vscode.commands.registerCommand("quarterlight.remindNow", remind),

    // Picking a different season by hand pauses the automatic switching.
    vscode.workspace.onDidChangeConfiguration(async (e) => {
      if (!e.affectsConfiguration("workbench.colorTheme") || switchingTheme) return;
      const theme = activeTheme();
      const cfg = vscode.workspace.getConfiguration("quarterlight");
      if (theme.startsWith(THEME_PREFIX) && theme !== THEME_PREFIX + currentSeason() && cfg.get("autoSeason", true)) {
        await cfg.update("autoSeason", false, vscode.ConfigurationTarget.Global);
        const pick = await vscode.window.showInformationMessage(
          `You chose ${theme}, so automatic season changes are paused.`,
          "Keep Changing With the Seasons"
        );
        if (pick) vscode.commands.executeCommand("quarterlight.useCurrentSeason");
      }
    })
  );

  if (context.globalState.get("ql.welcomed")) {
    applySeason(false);
    offerFontOnThisComputer();
  } else {
    welcome();
  }

  const seasonCheck = setInterval(() => applySeason(false), 60 * 60000); // hourly, for windows left open across a season change
  const breakCheck = setInterval(breakTick, 60000);
  context.subscriptions.push({
    dispose() {
      clearInterval(seasonCheck);
      clearInterval(breakCheck);
    },
  });
}

function deactivate() {
  clearInterval(countdownTimer);
  clearTimeout(statusHideTimer);
}

module.exports = { activate, deactivate, seasonFor };
