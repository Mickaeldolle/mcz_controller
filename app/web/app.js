"use strict";
const on = document.getElementById("on");
const off = document.getElementById("off");
const connection = document.getElementById("connection");
const feedback = document.getElementById("feedback");
let status = null;
let sending = false;
let hasResult = false;
let serverError = false;
let restoreFocus = null;

function render() {
  const connected = status?.connected === true;
  connection.textContent = status?.preview ? "Aperçu · aucune émission" : connected ? "ESP32 connecté" : "ESP32 déconnecté";
  connection.classList.toggle("connected", connected);
  const enabled = connected && status.profiles_ready && !sending && !status.busy && status.cooldown <= 0;
  on.disabled = off.disabled = !enabled;
  on.setAttribute("aria-busy", String(sending));
  off.setAttribute("aria-busy", String(sending));
  if (enabled && restoreFocus) {
    if (document.activeElement === document.body || document.activeElement === restoreFocus) restoreFocus.focus({preventScroll: true});
    restoreFocus = null;
  }
  if (!sending && !hasResult) {
    feedback.textContent = !connected ? "Branche l’ESP32 en USB. La connexion sera rétablie automatiquement."
      : !status.profiles_ready ? "Les commandes Allumer et Éteindre doivent encore être enregistrées."
      : "Prêt à envoyer une commande.";
  }
}

async function refresh() {
  try {
    const response = await fetch("/api/status", {cache: "no-store", signal: AbortSignal.timeout(2500)});
    if (!response.ok) throw new Error("status");
    status = await response.json();
    if (serverError && !sending) { hasResult = false; serverError = false; }
  } catch {
    status = null;
    if (!sending) feedback.textContent = "Application locale inaccessible. Relance l’application sur le PC.";
    hasResult = true;
    serverError = true;
  }
  render();
}

async function command(action) {
  if (sending || !status?.connected || !status.profiles_ready || status.busy || status.cooldown > 0) return;
  const token = status.token;
  const button = action === "on" ? on : off;
  if (button.matches(":focus-visible")) restoreFocus = button;
  sending = true;
  hasResult = true;
  feedback.textContent = action === "on" ? "Envoi de la commande Allumer…" : "Envoi de la commande Éteindre…";
  render();
  try {
    const id = crypto.randomUUID().replaceAll("-", "");
    const response = await fetch("/api/command", {
      method: "POST", headers: {"Content-Type": "application/json", "X-MCZ-Token": token},
      body: JSON.stringify({action, id}), signal: AbortSignal.timeout(6500)
    });
    if (!response.ok) throw new Error("command");
    const result = await response.json();
    const label = action === "on" ? "Allumer" : "Éteindre";
    feedback.textContent = result.result === "sent" ? `Commande « ${label} » envoyée. Vérifie la réaction du poêle.`
      : result.result === "unavailable" ? "ESP32 indisponible. Vérifie le branchement USB avant de réessayer."
      : result.result === "busy" ? "Une commande est déjà en cours. Attends quelques secondes."
      : result.result === "rejected" ? "Commande refusée. Vérifie la configuration de l’application."
      : "Envoi non confirmé. Vérifie le poêle avant toute nouvelle commande.";
  } catch {
    feedback.textContent = "Envoi non confirmé. Vérifie le poêle avant toute nouvelle commande.";
  } finally {
    sending = false;
    await refresh();
  }
}
on.addEventListener("click", () => command("on"));
off.addEventListener("click", () => command("off"));
async function poll() { await refresh(); setTimeout(poll, 1000); }
poll();
