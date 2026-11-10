# Enregistrer des trames MCZ sur le PC

Ce dossier regroupe les outils de capture et d’analyse. Ils utilisent un
récepteur série compatible à **434,50 MHz**. Le firmware de commande du
poêle est dédié à l’émission. Pour capter après son installation, utilise
un récepteur distinct capable de fournir les données décrites ci-dessous.

## Enregistrer les trames décodées

Le récepteur doit produire à **115200 bauds** des lignes commençant par
`Raw:` suivies des sept octets en hexadécimal séparés par des espaces.
Le firmware MCZ de réception utilisé pour les captures précédentes
produisait ce format.

Depuis PowerShell, à la racine du dépôt, installe les dépendances du
[guide de développement](../docs/GUIDE_DEVELOPPEMENT.md#1-préparer-le-poste)
et repère le port du récepteur.

```powershell
.\.venv\Scripts\python.exe -m serial.tools.list_ports -v
.\.venv\Scripts\python.exe reception\monitor_serial.py --port COM3 --seconds 120
```

Remplace `COM3` par le port détecté. Si un autre programme utilise ce port,
ferme-le avant le moniteur. L’ouverture de la liaison peut redémarrer le
récepteur. Sans `--seconds`, arrête le moniteur avec **Ctrl+C**.

Le moniteur lit le port sans lui envoyer de données par défaut.
`--legacy-status` ajoute les requêtes série de statut `j` et `s` du
récepteur MCZ historique. En réception, garde les autres réglages fixes
et change un paramètre à la fois. Note l’ordre des gestes et laisse
quelques secondes entre eux. La télécommande d’origine peut commander
le poêle pendant l’essai.

Le fichier horodaté est écrit dans [`captures/`](../captures/README.md).
Les lignes `RX #` contiennent les octets, le mode, la flamme, les deux
ventilateurs et le résultat du CRC. Pour intégrer une commande, vérifie
que cinq trames identiques correspondent au geste et à l’identifiant
attendu avant d’ajouter une ligne au [catalogue](../config/catalogue_mcz.csv).

## Enregistrer et décoder les impulsions brutes

`record_serial.py` peut demander au récepteur MCZ historique de produire
des blocs `RX_BURST_BEGIN` / `RX_BURST_END`. Ce mode exige un récepteur
qui prend en charge les requêtes série de capture brute.

```powershell
.\.venv\Scripts\python.exe reception\record_serial.py --port COM3 --seconds 30 --continuous-raw
```

Le script enregistre la sortie du récepteur telle qu’elle arrive. Le
décodeur natif lit les blocs d’impulsions signées et affiche les trames
avec un CRC valide. Depuis Linux ou WSL, avec `g++`, compile-le à la
racine du dépôt et remplace le nom de journal d’exemple par le tien.

```sh
mkdir -p .pio
g++ -std=c++11 -Wall -Wextra -Isrc -Ireception reception/decode_capture.cpp \
    reception/mcz_decoder.cpp src/mcz_crc.cpp -o .pio/decode_capture
.pio/decode_capture captures/exemple_brut.log
```

PlatformIO compile le firmware à partir de `src/`. Les sources de ce
dossier servent aux outils du PC et aux tests natifs.
