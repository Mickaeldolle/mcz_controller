"use strict";
const on = document.getElementById("on");
const off = document.getElementById("off");
const connection = document.getElementById("connection");
const feedback = document.getElementById("feedback");
const settings = document.getElementById("settings");
const power = document.getElementById("power");
const fan = document.getElementById("fan");
const fan2 = document.getElementById("fan2");
const fan2Control = document.getElementById("fan2-control");
const powerValue = document.getElementById("power-value");
const fanValue = document.getElementById("fan-value");
const fan2Value = document.getElementById("fan2-value");
const settingsNote = document.getElementById("settings-note");
const onLabel = document.getElementById("on-label");
const wifi = document.documentElement.dataset.transport === "wifi";
const apiKey = document.documentElement.dataset.apiKey;
const originalFan2 = "-1";
let cooldownUntil = 0;
let status = null;
let sending = false;
let hasResult = false;
let serverError = "";
let restoreFocus = null;
let refreshId = 0;

function fanText(value) {
  if (value === "6") return "Auto";
  if (value === "0") return "arrêt";
  return value;
}
function selectedFan2() {
  return fan2.value === originalFan2 ? "" : fan2.value;
}
function selectedProfile(fan2Level) {
  const base = `${power.value}:${fan.value}`;
  return fan2Level ? `${base}:${fan2Level}` : base;
}

function render() {
  const connected = status?.connected === true;
  connection.textContent = status?.preview ? "Aperçu · aucune émission"
    : connected ? "ESP32 connecté" : "ESP32 déconnecté";
  connection.classList.toggle("connected", connected);
  const enabled = connected && status.profiles_ready && !sending && !status.busy && status.cooldown <= 0;
  const presets = status?.presets ?? [];
  const adjustable = presets.some(profile => profile !== "off");
  if (status) {
    fan2Control.hidden = !presets.some(profile => profile.split(":").length === 3);
    if (fan2Control.hidden) fan2.value = originalFan2;
  }
  const fan2Level = selectedFan2();
  const supported = presets.includes(selectedProfile(fan2Level));
  const compatible = presets.filter(profile => profile !== "off")
    .map(profile => profile.split(":"))
    .filter(([, , second = ""]) => second === fan2Level);
  const availableFans = compatible.filter(([flame]) => flame === power.value)
    .map(([, first]) => fanText(first));
  const alternative = compatible[0];
  settings.disabled = !adjustable || sending;
  powerValue.textContent = power.value;
  fanValue.textContent = fanText(fan.value);
  fan.setAttribute("aria-valuetext", fan.value === "6" ? "6, automatique" : fan.value);
  const fan2Text = fan2Level === "0" ? "Arrêt (0)" : fan2Level ? fanText(fan2Level) : "Profil d’origine";
  fan2Value.textContent = fan2Text;
  fan2.setAttribute("aria-valuetext", fan2Text);
  onLabel.textContent = adjustable ? "Allumer / appliquer" : "Allumer";
  let note;
  if (!status) {
    note = "Réglages en attente de connexion à l’application.";
  } else if (!adjustable) {
    note = "Aucun réglage manuel dans le catalogue. Le bouton Allumer utilise le profil enregistré par défaut.";
  } else if (supported) {
    note = "Ces réglages sont envoyés quand tu cliques sur Allumer / appliquer.";
  } else if (availableFans.length) {
    note = `Combinaison non capturée. À cette puissance, choisis le ventilateur 1 parmi ${availableFans.join(", ")}.`;
  } else if (fan2Level && alternative) {
    note = `Pour ce réglage du ventilateur 2, choisis flamme ${alternative[0]} et ventilateur 1 au niveau ${fanText(alternative[1])}.`;
  } else if (fan2Level) {
    note = "Ce niveau du ventilateur 2 manque dans le catalogue.";
  } else if (presets.some(profile => profile.startsWith(`${power.value}:${fan.value}:`))) {
    note = "Pour cette combinaison, sélectionne un niveau du ventilateur 2.";
  } else {
    note = "Aucun réglage capturé à cette puissance.";
  }
  if (settingsNote.textContent !== note) settingsNote.textContent = note;
  on.disabled = !enabled || (adjustable && !supported);
  off.disabled = !enabled;
  on.setAttribute("aria-busy", String(sending));
  off.setAttribute("aria-busy", String(sending));
  if (restoreFocus && !restoreFocus.disabled) {
    if (document.activeElement === document.body || document.activeElement === restoreFocus) restoreFocus.focus({preventScroll: true});
    restoreFocus = null;
  }
  if (!sending && !hasResult) {
    const message = serverError || (!connected ? "Branche l’ESP32 en USB. La connexion sera rétablie automatiquement."
      : !status.profiles_ready ? (wifi ? "Radio indisponible. Vérifie l’ESP32 et le module CC1101."
        : "Les commandes Allumer et Éteindre doivent encore être enregistrées.")
      : "Prêt à envoyer une commande.");
    if (feedback.textContent !== message) feedback.textContent = message;
  }
}

function requestOptions(timeout) {
  return {cache: "no-store", credentials: "omit", mode: "same-origin", redirect: "error",
    signal: AbortSignal.timeout(timeout)};
}

async function refresh() {
  const id = ++refreshId;
  try {
    const response = await fetch(wifi ? "/api/v1/status" : "/api/status", {
      ...requestOptions(2500), headers: wifi ? {Authorization: `Bearer ${apiKey}`} : {}
    });
    if (id !== refreshId) return;
    if (wifi && response.status === 401) {
      status = null;
      serverError = "Accès refusé. Recharge la page pour rétablir la connexion.";
      render();
      return;
    }
    if (!response.ok) throw new Error("status");
    const next = await response.json();
    if (id !== refreshId) return;
    if (wifi && (next.version !== 1 || !Array.isArray(next.profiles))) throw new Error("api");
    status = wifi ? {connected: true, profiles_ready: next.ready === true,
      presets: next.profiles, cooldown: Math.max(0, cooldownUntil - performance.now())} : next;
    serverError = "";
  } catch {
    if (id !== refreshId) return;
    status = null;
    serverError = wifi ? "ESP32 inaccessible. Vérifie le Wi-Fi et l’adresse de la carte."
      : "Application locale inaccessible. Relance l’application sur le PC.";
  }
  render();
}

async function command(action) {
  const button = action === "on" ? on : off;
  if (button.disabled || sending) return;
  const token = status.token;
  const presets = status.presets ?? [];
  const fan2Level = selectedFan2();
  const candidate = action === "on" ? selectedProfile(fan2Level) : "off";
  const profile = presets.includes(candidate) ? candidate : null;
  const second = fan2Level ? `, ventilateur 2 ${fanText(fan2Level)}` : "";
  const label = action === "off" ? "Éteindre"
    : profile ? `Flamme ${power.value}, ventilateur 1 ${fanText(fan.value)}${second}` : "Allumer";
  if (button.matches(":focus-visible")) restoreFocus = button;
  sending = true;
  hasResult = true;
  feedback.textContent = `Envoi de la commande « ${label} »…`;
  render();
  try {
    const id = Array.from(crypto.getRandomValues(new Uint8Array(16)),
      byte => byte.toString(16).padStart(2, "0")).join("");
    const request = {action, id};
    if (profile) request.profile = profile;
    const response = wifi
      ? await fetch(`/api/v1/command?profile=${encodeURIComponent(profile)}&id=${id}`, {
        ...requestOptions(6500), method: "POST", headers: {Authorization: `Bearer ${apiKey}`}
      })
      : await fetch("/api/command", {
        ...requestOptions(6500), method: "POST",
        headers: {"Content-Type": "application/json", "X-MCZ-Token": token}, body: JSON.stringify(request)
      });
    if (wifi && response.status === 401) {
      status = null;
      feedback.textContent = "Commande refusée. Recharge la page pour rétablir la connexion.";
      return;
    }
    if (wifi && (response.status === 400 || response.status === 403)) {
      feedback.textContent = `Commande refusée par l’ESP32 (HTTP ${response.status}). Ouvre directement la page Wi-Fi de l’ESP32.`;
      return;
    }
    if (!wifi && !response.ok) throw new Error("command");
    const result = await response.json();
    if (wifi && result.id !== id) throw new Error("command");
    feedback.textContent = result.result === "sent" ? `Commande « ${label} » envoyée. Vérifie la réaction du poêle.`
      : result.result === "unavailable" ? (wifi ? "Radio indisponible. Vérifie l’ESP32 avant de réessayer."
        : "ESP32 indisponible. Vérifie le branchement USB avant de réessayer.")
      : result.result === "busy" ? "Une commande est déjà en cours. Attends quelques secondes."
      : result.result === "rejected" ? "Commande refusée. Vérifie la configuration de l’application."
      : "Envoi non confirmé. Vérifie le poêle avant toute nouvelle commande.";
  } catch {
    feedback.textContent = "Envoi non confirmé. Vérifie le poêle avant toute nouvelle commande.";
  } finally {
    if (wifi) cooldownUntil = performance.now() + 3000;
    sending = false;
    await refresh();
  }
}
on.addEventListener("click", () => command("on"));
off.addEventListener("click", () => command("off"));
power.addEventListener("input", render);
fan.addEventListener("input", render);
fan2.addEventListener("input", render);

if (wifi) document.getElementById("transport").textContent = "WI-FI · LOCAL";

async function poll() {
  if (!sending) await refresh();
  setTimeout(poll, wifi ? 2000 : 1000);
}
poll();
