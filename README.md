# MCZ Musa · commande locale

Pilotage d’un poêle MCZ Musa Comfort Air avec un ESP32 classique et un
CC1101 E07-M1101D. Le propriétaire a confirmé l’allumage et l’extinction
depuis la page locale le 9 novembre 2026.
Le firmware du dépôt est dédié à l’émission sur commande. Le CC1101 reste
au repos entre les envois.

| Accès | Utilisation |
|---|---|
| Page sur l’ESP32 | Depuis un téléphone ou un PC sur le même Wi-Fi, ouvre l’adresse IP de la carte |
| Page locale sur le PC | [Application USB](docs/APPLICATION_LOCALE.md) sur `127.0.0.1:8765` |
| Application externe | [API HTTP de l’ESP32](docs/API.md) sur le Wi-Fi local après configuration |
| Radio du poêle | [Protocole et câblage](docs/FONCTIONNEMENT_TRAMES_MCZ.md) à 434,50 MHz ASK/OOK |
| Enregistrer des trames | [Outils de réception sur le PC](reception/README.md) avec un récepteur compatible |

Le [guide de développement](docs/GUIDE_DEVELOPPEMENT.md) réunit les
commandes de compilation, de téléversement, de lancement et de configuration.

## Installation

Depuis PowerShell, à la racine du projet, avec Python 3.11 ou plus récent :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Pour la page locale, branche l’ESP32 en USB et ouvre `Demarrer-MCZ.cmd`.
Attends **ESP32 connecté**, puis utilise **Allumer / appliquer** ou **Éteindre**.
Si ton ESP32 est sur un autre port, lance
`.\.venv\Scripts\python.exe -m app.launch --serial-port COMx`.

Les curseurs sélectionnent la flamme de 1 à 5, le ventilateur 1 de 1 à 6
et le ventilateur 2 de 0 à 6. La position 6 correspond à Auto et la
position 0 à l’arrêt du ventilateur 2. Avec un niveau explicite du
ventilateur 2, les trois réglages se combinent librement. Le premier
cran **Profil d’origine** donne accès aux combinaisons d’origine
capturées avant la réapparition du menu du ventilateur 2.
Pour envoyer, le poêle doit accepter
les commandes distantes et le bouton doit être activé. Déplacer les curseurs
prépare le réglage. **Éteindre** est indépendant des curseurs.

## Mettre l’ESP32 en service sur le Wi-Fi

1. Vérifie le [câblage](docs/FONCTIONNEMENT_TRAMES_MCZ.md#matériel) et ferme
   la page et le serveur USB pour libérer COM3.
2. Compile le firmware avec `.\.venv\Scripts\python.exe -m platformio run`.
3. Installe le nouveau firmware et saisis les paramètres dans le terminal
   local en suivant le [guide de l’API](docs/API.md#mise-en-service).
4. Ouvre la page à l’adresse IP affichée et vérifie que l’ESP32 apparaît
   connecté. Une alimentation USB suffit ensuite
   pour utiliser la page, même quand le PC est éteint.

La page de test donne accès aux commandes à tout appareil autorisé à
l’ouvrir. La page et l’API utilisent HTTP sur le réseau domestique de confiance.
Le contrat [API v1](docs/API.md#contrat) servira aussi à la future application Kotlin.

Le catalogue [CSV](config/catalogue_mcz.csv) s’appuie sur la
[capture d’origine](captures/20261109-205625-968354_live.log) et la
[capture du ventilateur 2](captures/20261110-065656-157595_live.log).
Le PC et la compilation vérifient les groupes de cinq réceptions,
reconstruisent les trames manuelles capturées et calculent les autres
combinaisons avec le même [format de trame](docs/FONCTIONNEMENT_TRAMES_MCZ.md#ventilateur-2).
Un clic ou un POST explicite envoie
une commande de cinq répétitions. Le dernier résultat d’envoi ne constitue
pas un état mesuré du poêle.

Voir le [guide de validation](docs/agents/DEVELOPPEMENT.md) pour tester
sans matériel et le [guide des agents](AGENTS.md) pour reprendre le projet.

La cible `esp32dev-alexa` sert à vérifier la découverte sur l’Echo Pop.
La cible `esp32dev-alexa-radio` relie ON et OFF au poêle.
[Procédure Alexa](docs/TEST_ALEXA.md)
