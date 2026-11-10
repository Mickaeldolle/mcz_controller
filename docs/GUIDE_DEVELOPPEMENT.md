# Guide de développement et de mise en service

Le firmware s’exécute sur l’ESP32 et pilote le CC1101. Sur le PC, le serveur
Python sert le frontend et transmet les commandes par USB. Une application
externe peut aussi appeler directement l’ESP32 par Wi-Fi après configuration.

| Accès | Adresse | Authentification |
|---|---|---|
| Frontend sur le PC | `http://127.0.0.1:8765/` | Jeton local généré par Python et récupéré automatiquement par la page |
| API Wi-Fi de l’ESP32 | `http://<adresse-ip-esp32>/api/v1/status` | Clé API saisie une fois par USB, puis envoyée par le client avec `Authorization: Bearer <clé>` |

## 1. Préparer le poste

Ouvre PowerShell à la racine du dépôt. Les commandes utilisent Python 3.11
et l’environnement virtuel du projet. Si `.venv` existe déjà, passe
directement à l’installation des dépendances ou à l’étape suivante si elles
sont présentes.

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

L’installation télécharge les dépendances Python. La première compilation
peut également télécharger l’outillage ESP32. Aucun droit administrateur
n’est normalement requis. Le frontend est servi par Python et utilise
directement les fichiers HTML, CSS et JavaScript de `app/web/`.

## 2. Repérer la carte et libérer le port USB

```powershell
.\.venv\Scripts\python.exe -m serial.tools.list_ports -v
```

Repère le port affiché lorsque tu branches l’ESP32. Les exemples utilisent
`COM3`. Remplace-le par le port détecté si nécessaire.

Un seul programme peut tenir ce port. Avant un téléversement, une
configuration Wi-Fi ou un diagnostic série, arrête le serveur Python avec
**Ctrl+C** dans sa console et ferme tout moniteur série. Fermer l’onglet du
navigateur laisse le serveur en marche. L’ouverture du port peut redémarrer
la carte.

## 3. Compiler et téléverser le firmware

Vérifie le [câblage ESP32–CC1101](FONCTIONNEMENT_TRAMES_MCZ.md#matériel)
et l’alimentation **3,3 V** du CC1101 avant de brancher la carte. La cible
`esp32dev`, les versions des outils et le débit de 115200 bauds pour la
console et le téléversement sont définis dans
[`platformio.ini`](../platformio.ini).

**Compiler sans la carte**

```powershell
.\.venv\Scripts\python.exe -m platformio run -e esp32dev
```

Un résultat `SUCCESS` confirme la compilation. Le binaire se trouve dans
`.pio/build/esp32dev/firmware.bin`. La compilation valide le catalogue
et génère `.pio/build/esp32dev/generated/mcz_profiles.h`. Elle intègre
aussi la page de `app/web/` au firmware, sans transfert séparé de fichiers.

**Installer sur la carte**

Garde une version connue et les fichiers source correspondants pour
pouvoir la reconstruire et la réinstaller en cas de régression. Le
téléversement remplace le firmware de la carte et la redémarre. Vérifie le
port avant de lancer la commande.

Si la carte utilise un firmware de capture, sauvegarde-le avant de
téléverser. Conserve toute image brute de la flash hors du dépôt et dans
un emplacement privé, car elle peut contenir des identifiants Wi-Fi.

```powershell
.\.venv\Scripts\python.exe -m platformio run -e esp32dev -t upload --upload-port COM3
```

Après le téléversement ou une mise sous tension, le firmware prépare
l’émetteur et laisse le CC1101 au repos (`IDLE`). Une commande explicite
déclenche l’émission, puis le CC1101 revient au repos.

**Lire le statut série**

```powershell
.\.venv\Scripts\python.exe -m serial.tools.miniterm COM3 115200 --eol LF
```

Tape `j` pour demander le statut radio, ou `!NET` suivi d’**Entrée** pour le
statut réseau du firmware API v1. Ces deux requêtes sont en lecture seule.
Le message `TX READY` au démarrage ou la réponse `APP` avec
`ready: true` indique que l’émetteur est prêt. Quitte le moniteur avec
**Ctrl+]** avant de relancer un autre outil.

## 4. Exécuter le serveur et ouvrir le frontend

**Lancement habituel depuis PowerShell**

```powershell
.\Demarrer-MCZ.cmd
```

Le lanceur démarre le serveur Python et ouvre le navigateur. Si le serveur
est déjà actif à l’adresse par défaut, il ouvre sa page. Pour choisir un
autre port USB, utilise par exemple
`.\.venv\Scripts\python.exe -m app.launch --serial-port COM4` après avoir
arrêté l’instance précédente.

**Lancement manuel pour développer**

```powershell
.\.venv\Scripts\python.exe -m app.server --serial-port COM3 --http-port 8765
```

Ouvre [le frontend](http://127.0.0.1:8765/) et attends **ESP32 connecté**.
Si le port HTTP 8765 est occupé par une autre application, choisis par
exemple `--http-port 8767` et ouvre `http://127.0.0.1:8767/`. Le serveur
reste accessible uniquement sur le PC.

- Après une modification dans `app/web/`, recharge la page.
- Après une modification du code Python ou du catalogue, arrête puis
  redémarre le serveur.
- Après une modification de `src/`, `include/`, `platformio.ini` ou des
  profils embarqués, recompile puis téléverse le firmware pour l’essayer
  sur la carte.

Le serveur PC crée son jeton à chaque démarrage. Le frontend le reçoit
via `/api/status` et l’envoie dans `X-MCZ-Token`. Cette clé est distincte
de celle de l’API Wi-Fi.

Pour vérifier l’USB et les profils sans afficher le jeton local, utilise
ce GET en lecture seule dans une deuxième console.

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/status' -TimeoutSec 5 |
    Select-Object connected, port, profiles_ready, presets, tx_count
```

`connected = True` indique que le serveur a reçu un statut radio récent
sur le port USB. Les boutons **Allumer / appliquer** et **Éteindre**
déclenchent de vraies commandes. Pour un essai, reste devant le poêle et
observe sa réaction.

## 5. Configurer le Wi-Fi et la clé de l’API ESP32

1. Téléverse le firmware avec l’API v1 et libère le port USB.
2. Choisis un réseau Wi-Fi **2,4 GHz** compatible WPA2-PSK. Le SSID doit
   contenir de 1 à 32 octets UTF-8. Le mot de passe doit contenir de 8 à
   63 caractères ASCII imprimables.
3. Génère une clé API propre à cette carte dans ta console locale.
   La commande affiche une valeur aléatoire de 64 caractères
   hexadécimaux minuscules. Range-la dans ton gestionnaire de mots de
   passe et évite de l’inclure dans le code, un journal ou une capture
   d’écran.

   ```powershell
   .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
   ```

4. Lance la configuration dans une console interactive. Saisis le SSID,
   le mot de passe Wi-Fi et la clé API. Le mot de passe et la clé sont
   saisis sans affichage.

   ```powershell
   .\.venv\Scripts\python.exe -m app.network_setup --port COM3
   ```

5. Ouvre la page affichée à l’adresse IPv4 de la carte depuis un appareil
   du même réseau. La page de test reçoit automatiquement la clé depuis
   l’ESP32. Tout appareil qui peut ouvrir cette page peut commander le poêle.
   Les paramètres persistent sur l’ESP32 après redémarrage. La page et
   ses fichiers sont intégrés au firmware lors de la compilation.

Si l’outil affiche **Firmware API v1 non détecté**, vérifie le port et la
version téléversée. Si les paramètres sont enregistrés mais que la carte
reste déconnectée, vérifie le SSID 2,4 GHz, le mot de passe et la couverture
Wi-Fi avant de refaire la configuration.

Pour lire le statut Wi-Fi ou retrouver l’adresse, libère le port USB et
lance cette commande.

```powershell
.\.venv\Scripts\python.exe -m app.network_setup --port COM3 --status
```

Pour changer le SSID, le mot de passe ou la clé, relance la configuration
interactive avec les trois valeurs voulues. Les clients doivent utiliser
la nouvelle clé après rotation. Pour effacer la configuration réseau et
désactiver l’API Wi-Fi, utilise `--forget`. Cette action nécessite ensuite
une nouvelle configuration USB pour réactiver le Wi-Fi.

```powershell
.\.venv\Scripts\python.exe -m app.network_setup --port COM3 --forget
```

L’API Wi-Fi utilise **HTTP en clair** et le projet ne configure pas le
chiffrement de la mémoire flash. Utilise un réseau privé de confiance.
Garde le serveur PC sur la boucle locale et évite toute redirection de
port vers l’ESP32.

## 6. Vérifier l’API Wi-Fi

Pour la recette locale, ouvre d’abord la page depuis le téléphone ou le
PC. Vérifie que les boutons s’activent lorsque la radio est prête.
Vérifie que la sélection d’un profil et un rechargement de la page
n’incrémentent pas le compteur TX. La réservation DHCP du routeur
permet de retrouver la même adresse après redémarrage.
Une fois la configuration vérifiée, alimente l’ESP32 par USB sans le
serveur PC et rouvre la page. Fais l’essai physique devant le poêle,
une commande à la fois, avec le sélecteur du poêle en mode distant.

Depuis le même sous-réseau IPv4 que l’ESP32, remplace l’adresse d’exemple
par celle affichée à l’étape précédente. Ce test est en lecture seule.
Il demande la clé sans l’afficher.

```powershell
$mczUrl = 'http://192.168.1.42'
$mczSecret = Read-Host 'Clé API ESP32' -AsSecureString
$mczHeaders = @{
    Authorization = 'Bearer ' + [System.Net.NetworkCredential]::new('', $mczSecret).Password
}
try {
    Invoke-RestMethod -Uri "$mczUrl/api/v1/status" -Headers $mczHeaders -TimeoutSec 5
} finally {
    Remove-Variable mczHeaders, mczSecret
}
```

La réponse contient `ready`, `tx_count` et la liste des `profiles`.
Un HTTP **401** indique une clé absente ou incorrecte. Un HTTP **403**
indique que l’ESP32 rejette la source, notamment si elle se trouve hors du
sous-réseau local. En cas de délai dépassé, vérifie l’adresse, le masque,
le réseau invité ou l’isolation des clients, puis teste le port HTTP.
Cette dernière commande vérifie seulement l’accès TCP.

```powershell
Test-NetConnection -ComputerName 192.168.1.42 -Port 80
```

Les commandes réelles utilisent un POST avec un profil renvoyé par le
GET, un identifiant de 32 caractères hexadécimaux minuscules et un corps
vide. Consulte les [routes et les résultats possibles](API.md#contrat)
avant un essai d’émission.

Pour un **essai d’arrêt réel**, ajoute ce bloc après le GET, à l’intérieur
du `try` de l’exemple précédent. Lance-le lorsque tu es devant le poêle
et qu’il est prêt à recevoir les commandes distantes.

```powershell
if ((Read-Host "Tape ENVOYER OFF pour confirmer l’arrêt") -ceq 'ENVOYER OFF') {
    $mczId = [guid]::NewGuid().ToString('N')
    Invoke-RestMethod -Method Post -Uri "$mczUrl/api/v1/command?profile=off&id=$mczId" `
        -Headers $mczHeaders -TimeoutSec 5
}
```

`sent` décrit l’émission rapportée par l’ESP32. Observe le poêle pour
confirmer son action et avant tout nouvel envoi après un délai ou un
résultat incertain.

## 7. Valider une modification hors matériel

```powershell
git diff --check
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py' -v
.\.venv\Scripts\python.exe -m platformio run -e esp32dev
```

Les tests Python simulent l’USB et ouvrent des ports HTTP sur la boucle
locale. Ils ne nécessitent normalement aucun privilège administrateur.
Sous Linux ou WSL, avec Python 3 et `g++`, les tests natifs vérifient
également l’encodage, le décodage et le moteur de commande.

```sh
sh tools/check_native.sh
```

Pour contrôler le [catalogue](../config/catalogue_mcz.csv) et sa
[capture d’origine](../captures/20261109-205625-968354_live.log) sans
ouvrir le port série, charge les profils depuis Python.

```powershell
.\.venv\Scripts\python.exe -c "from app.catalog import load_presets; print(', '.join(sorted(load_presets())))"
```

Le catalogue doit correspondre aux groupes de cinq réceptions dans le
journal. Pour modifier un profil, conserve la preuve de capture, valide
le catalogue, puis redémarre le serveur et recompile le firmware.

Voir aussi l’[architecture](agents/ARCHITECTURE.md),
le [protocole radio](FONCTIONNEMENT_TRAMES_MCZ.md) et l’[état des essais](agents/ETAT_PROJET.md).

## 8. Enregistrer de nouvelles trames

Le dossier [`reception/`](../reception/README.md) contient le moniteur
série, l’enregistreur brut et le décodeur hors ligne. Ils s’exécutent
sur le PC. Les journaux produits vont dans `captures/`. Le firmware
de commande de l’ESP32 reste dédié à l’émission.
