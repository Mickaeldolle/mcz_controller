# Découverte et commande avec l’Echo Pop

La cible PlatformIO `esp32dev-alexa` expose une seule ampoule virtuelle
**Test Alexa MCZ**. Son callback écrit l’état et la valeur reçus sur
le port série. L’envoi radio reste accessible depuis la page MCZ et l’API.
La cible `esp32dev-alexa-radio` permet aussi la commande radio depuis
cette ampoule.

| Service | Adresse sur le réseau local |
|---|---|
| fauxmoESP | TCP 80 et découverte SSDP sur UDP 1900 |
| Page MCZ | `http://<ip-esp32>:8080/` |
| API MCZ | `http://<ip-esp32>:8080/api/v1/status` |

La configuration Wi-Fi enregistrée sur la carte reste utilisée.
L’Echo et l’ESP32 doivent être sur le même réseau local avec le
multicast autorisé entre les appareils. La version de test utilise
[fauxmoESP 3.4.1](https://github.com/vintlabs/fauxmoESP/releases/tag/3.4.1)
et [AsyncTCP 3.3.4](https://github.com/ESP32Async/AsyncTCP/releases/tag/v3.3.4).
La compilation applique un correctif qui borne les requêtes Hue,
vérifie les identifiants de lampes et assemble les requêtes réparties
sur plusieurs segments TCP.

## Installer la cible de test

Depuis PowerShell, à la racine du dépôt, ferme tout moniteur ou serveur
qui utilise COM3 et remplace le port si nécessaire.

```powershell
.\.venv\Scripts\python.exe -m platformio run -e esp32dev-alexa
.\.venv\Scripts\python.exe -m platformio run -e esp32dev-alexa -t upload --upload-port COM3
.\.venv\Scripts\python.exe -m serial.tools.miniterm COM3 115200
```

L’ouverture du port série peut redémarrer la carte. Attends la ligne
`ALEXA test ready on TCP 80`. Pour retrouver l’adresse de la page,
quitte le moniteur avec **Ctrl+]**, puis lance
`.\.venv\Scripts\python.exe -m app.network_setup --port COM3 --status`.

## Vérifier la découverte et les routines

1. Lance la détection d’appareils dans Alexa et cherche **Test Alexa MCZ**.
2. Active puis désactive cette ampoule depuis l’application Alexa.
   Le journal doit afficher une ligne `ALEXA` pour chaque action avec
   `state=ON` ou `state=OFF` et la valeur reçue.
3. Répète le test avec deux routines, en choisissant l’ampoule de test
   comme cible. Le compteur `tx_count` de l’API MCZ doit rester stable
   pendant ces essais.

Sur un navigateur du même réseau, `http://<ip-esp32>/description.xml`
permet de vérifier que le service Hue répond. La validation de la
découverte reste propre à l’Echo Pop et à son environnement réseau.

Lors du test du 10 novembre 2026, le PC a reçu la réponse SSDP de
l’ESP32 et a lu l’ampoule sur le port 80. Deux requêtes HTTP, dont un
`ON` envoyé en trois morceaux espacés, ont produit `ON` et `OFF` dans le
journal série. L’API a conservé ses 221 profils sur le port 8080 et son
compteur TX est resté à zéro.

Le propriétaire a ensuite confirmé que son Echo Pop découvre
**Test Alexa MCZ** et que l’application Alexa permet de passer
l’ampoule sur ON et OFF. La lecture suivante de l’API MCZ indiquait
toujours `tx_count: 0`. L’essai concernait le contrôle virtuel.

## Commander le poêle avec Alexa

La cible `esp32dev-alexa-radio` utilise les mêmes ports et le même nom
d’ampoule. Elle relie les commandes explicites au moteur de commande MCZ.

| Action sur l’ampoule | Profil | Réglage |
|---|---|---|
| ON | `5:5:3` | Flamme 5, ventilateur 1 au niveau 5, ventilateur 2 au niveau 3 |
| OFF | `off` | Arrêt du poêle avec son cycle habituel |

La route Hue accepte une requête `PUT` du sous-réseau local avec le seul
champ booléen `on`. Les réglages de luminosité et de couleur sont
écartés. L’action la plus récente remplace celle en attente. Le moteur
commun applique le verrou radio et le délai de trois secondes. Une action
expirée ou refusée reste sans nouvel essai automatique.

```powershell
.\.venv\Scripts\python.exe -m platformio run -e esp32dev-alexa-radio -t upload --upload-port COM3
```

Sur cette cible, **Test Alexa MCZ pilote le poêle**. Une routine ou une
commande de groupe peut atteindre l’ampoule. La route Hue est prévue pour
un réseau local de confiance. Effectue le premier essai devant le poêle.
La ligne `ALEXA profile=5:5:3 result=sent` indique une émission. Observe
la réaction du poêle pour confirmer le résultat.

La cible radio a été téléversée le 10 novembre 2026. Après redémarrage,
l’ampoule et l’API MCZ répondaient. La radio était prête et son compteur
TX indiquait zéro. Le propriétaire a ensuite confirmé que la commande
depuis Alexa faisait réagir le poêle.

## Revenir au firmware habituel

Ferme le moniteur et téléverse la cible standard. La page redevient
accessible sur le port HTTP 80.

```powershell
.\.venv\Scripts\python.exe -m platformio run -e esp32dev -t upload --upload-port COM3
```
