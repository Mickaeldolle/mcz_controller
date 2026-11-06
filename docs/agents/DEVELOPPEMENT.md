# Développer et valider

Retour au [guide des agents](../../AGENTS.md). Commandes à exécuter depuis la
racine du dépôt. Ne pas lancer tous les exemples comme une procédure automatique.

## Prérequis et installation

Environnement de travail actuel : Windows/PowerShell, Python 3.11 observé.
Versions déclarées : PlatformIO 6.2.0, pyserial 3.5, plateforme espressif32 6.9.0,
Arduino, cible `esp32dev`. C++ natif en C++11 ; Linux/WSL avec g++ pour les
sanitizers. Il n'existe pas de dépendances npm pour la page.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:PLATFORMIO_CORE_DIR = Join-Path $PWD '.platformio'
$env:PLATFORMIO_SETTING_ENABLE_TELEMETRY = 'no'
```

À faire uniquement si l'environnement n'est pas déjà prêt. Pas de droits
administrateur attendus. Installation et premier build téléchargent des outils ;
une erreur d'accès réseau n'est pas une erreur de compilation du projet.
Ne pas versionner `.venv/`, `.pio/` ou `.platformio/`.

## Vérifications sans carte

```powershell
git status --short
git diff --check
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py' -v
.\.venv\Scripts\python.exe -m platformio run
```

La suite Python utilise des doubles pour USB et pour les commandes. Ses tests
HTTP ouvrent un serveur sur la boucle locale ; ils nécessitent l'autorisation
des sockets locaux, sans privilège administrateur normalement. Un test du lecteur
C++ est ignoré si `MCZ_DECODER` n'est pas défini. Le build compile sans flasher
et ne prouve ni le câblage, ni l'émission RF, ni l'état du poêle.

Sous Linux ou WSL, depuis le dossier du projet :

```sh
bash tools/check_native.sh
```

Le script compile et lance les trois suites C++ avec AddressSanitizer et
UndefinedBehaviorSanitizer, puis les tests Python de l'outil avec le lecteur C++
compilé. Il utilise un dossier temporaire supprimé à la sortie. Prérequis :
g++, python3 et outils shell standards ; aucun accès USB ou RF.

| Modification | Contrôles adaptés |
|---|---|
| Documentation seule | Liens locaux, conformité aux sources, diff et absence de changement fonctionnel |
| Bridge ou serveur | Suite Python, surtout concurrence, panne USB, anti-doublon et protections HTTP |
| Profils | CRC, ID, cinq occurrences originales de chaque trame, tests de provenance et attentes fixes |
| CRC, encodeur, décodeur ou impulsions | Tests natifs, suite Python d'analyse et build ESP32 |
| Pilote SPI/RMT, broches, firmware | Tests pertinents et build ; qualification matérielle séparée si autorisée |
| Interface | Suite Python et simulation visuelle ; `PRODUCT.md` et `DESIGN.md` cohérents |

Ne pas assouplir une protection ni ignorer silencieusement un échec pour obtenir
du vert. `WinError 10013` peut signaler une restriction des sockets locaux.
`WinError 10053` a également été observé lors des tests HTTP ; sa cause exacte
n'est pas établie. Conserver le résultat initial, vérifier les permissions et
relancer de manière ciblée si justifié, sans désactiver pare-feu ou contrôles HTTP.

## Prévisualisation de l'interface sans USB

```powershell
.\.venv\Scripts\python.exe tools/preview_app.py
```

Ouvrir `http://127.0.0.1:8766`, puis arrêter avec Ctrl+C. Le bridge est simulé :
aucune ouverture USB ni émission RF. Le résultat `sent` de cette page est fictif.
Vérifier clavier, focus, messages, état déconnecté, attente, erreur et petit écran.
La simulation peut lire `.pio/preview-state.json` ; ne pas la confondre avec
le serveur réel sur le port 8765.

## Opérations avec le matériel

Ces commandes sont des références, pas des vérifications à exécuter par défaut.
Fermer d'abord les autres propriétaires du port ; COM3 est un défaut local,
pas un identifiant portable. L'ouverture série peut redémarrer l'ESP32.

```powershell
.\.venv\Scripts\python.exe -m serial.tools.list_ports -v
.\.venv\Scripts\python.exe -m app.server --serial-port COM3
```

La première commande liste les ports. La seconde ouvre réellement USB et sert
la page sur `127.0.0.1:8765`. Aucun TX à l'ouverture ; cliquer Allumer/Éteindre
est une commande réelle. Ctrl+C ferme le serveur et libère le port.
`Demarrer-MCZ.cmd` est le lanceur usuel ; `Ecouter-MCZ.cmd` démarre le moniteur
RX. Ne pas les lancer ensemble.

Pour flasher seulement si la tâche le demande et après vérification du montage :

```powershell
.\.venv\Scripts\python.exe -m platformio run -t upload --upload-port COM3
```

Cette commande remplace le firmware. Conserver le binaire connu et sa
configuration pour le retour arrière ; une simple compilation n'archive pas
automatiquement l'état installé. Ne pas flasher pour vérifier la documentation.

`Appairer-MCZ.cmd` lance un essai ON réel avec les profils manuels. Il exige
`ENVOYER` après préparation par l'opérateur, envoie une commande à cinq
répétitions puis contrôle le retour RX. Lire le
[guide de mise en service](../MISE_EN_SERVICE_ALLUMAGE_EXTINCTION.md).
Un résultat incertain impose l'observation, jamais un renvoi automatique.

## Provenance et retour arrière

Les profils actifs et manuels sont distincts ; les chemins et valeurs sont
dans [l'état du projet](ETAT_PROJET.md). Les tests actifs ont des attentes fixes
et une lecture du journal historique ; ils doivent évoluer avec un changement
de provenance. Le validateur de l'essai manuel accepte les journaux live et
exige cinq occurrences des deux trames. Ne pas désactiver ces contrôles.

Conserver les originaux de `captures/`, travailler sur une sortie distincte
pour les analyses et marquer les données synthétiques dans les tests.
Avant modification de profils, garder leur version antérieure et la capture
associée ; le serveur charge ses profils au démarrage, donc un retour arrière
nécessite son redémarrage. Pour le code, annuler seulement les changements de
sa propre tâche, sans effacer ceux de l'utilisateur. Aucune sauvegarde Git ne
couvre un fichier non suivi tant qu'il n'a pas été explicitement conservé.
