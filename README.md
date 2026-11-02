# MCZ Musa Comfort Air — POC ESP32 + CC1101

Application locale sur le PC : **Allumer / Éteindre** via ESP32 USB et CC1101,
sans Wi-Fi ni cloud. La réception et les outils de diagnostic sont conservés.

**Statut : firmware RX/TX installé ; page locale et USB opérationnels.**
Deux commandes réelles capturées, cinq répétitions chacune, CRC valide.
La réaction physique du poêle à l'émission ESP32 reste à vérifier.
Voir [le guide de l'application](docs/APPLICATION_LOCALE.md) et
[le rapport RX historique](docs/RAPPORT_RX_VALIDE.md).
La [revue du code du 2 novembre 2026](docs/REVUE_CODE_2026-11-02.md)
détaille les corrections et les vérifications logicielles et USB les plus récentes.

La [documentation du fonctionnement des trames](docs/FONCTIONNEMENT_TRAMES_MCZ.md)
explique les octets, les champs, le CRC, l'encodage radio et les exemples issus
des captures réelles en mode manuel et en ventilation.

Pour préparer le premier essai d'allumage et d'arrêt par notre émetteur :
[bilan des blocages](docs/BLOCAGES_ALLUMAGE_EXTINCTION.md) et
[guide de mise en service](docs/MISE_EN_SERVICE_ALLUMAGE_EXTINCTION.md).
Ces documents proposent un profil manuel capturé ; ils ne modifient pas les
profils actifs et ne constituent pas une preuve de réaction du poêle.

## Utiliser l'application

Ouvrir `Demarrer-MCZ.cmd`, puis http://127.0.0.1:8765.
La page ne déclenche aucun envoi à son ouverture. Un clic envoie une seule
commande contenant les cinq répétitions du protocole. L'état du poêle reste
inconnu : « envoyée » ne prouve pas sa réception.

Lancement manuel depuis le dossier du projet :

```powershell
.\.venv\Scripts\python.exe -m app.server --serial-port COM3
```

Garder le processus ouvert. Une seule application peut utiliser COM3 à la fois :
fermer les outils de capture avant le lancement. Le serveur écoute uniquement
sur 127.0.0.1 ; pas d'ouverture vers Internet ou le réseau local.
Consulter [l'analyse des sources](docs/ANALYSE_PROTOCOLE.md) et
[le suivi de validation](docs/VALIDATION.md).
La [comparaison des sources avec les captures réelles](docs/ANALYSE_SIGNAUX_MCZ.md)
documente la signature temporelle observée et les limites du décodage actuel.

## Voir les trames en direct dans un terminal

Ouvrir `Ecouter-MCZ.cmd`. Le moniteur utilise COM3 et affiche chaque trame
valide avec son heure, ses sept octets et le délai depuis la précédente.
Les commandes identiques aux profils Allumer/Éteindre sont signalées.
Les cinq répétitions restent visibles : cinq lignes ne signifient pas cinq appuis.

Le journal horodaté est sauvegardé dans `captures/*_live.log`. Fermer avec
Ctrl+C pour libérer le port. Une déconnexion USB entraîne une tentative de
reconnexion, sans rejouer de commande.

Une seule application peut utiliser COM3 : arrêter l'application locale et les
outils de capture avant de lancer ce moniteur ; le fermer avant de les réutiliser.
Le moniteur n'envoie que les demandes de statut série `j` et `s`, sans émission
RF. Il affiche les trames reconnues par le décodeur actuel, pas toutes les
impulsions ni les éventuelles trames d'un format inconnu.

L'heure et les intervalles sont mesurés sur le PC, après le décodage et le
transport USB ; ils servent à corréler les appuis, sans mesurer exactement les
temps radio. L'ouverture du port peut redémarrer l'ESP32.

Pour choisir un autre port dans PowerShell :

```powershell
.\.venv\Scripts\python.exe -u tools/monitor_serial.py --port COM7
```

Cette commande ne nécessite pas de privilèges administrateur. Remplacer COM7
par le port de la carte ; `RX PRET` et `STATE=0D` confirment sa disponibilité.

## Matériel et câblage à confirmer

Les photos fournies montrent une **carte ESP32 classique à 38 broches avec CP2102**,
compatible avec le profil `esp32dev` retenu, et un module radio marqué **433M V2.0**
avec antenne SMA et connecteur 2×4. La photo du verso indique **E07-M1101D**.
Le brochage de la variante SMA a été recoupé avec le
[manuel Ebyte, section 3](https://techfun.sk/wp-content/uploads/2020/10/E07-M1101D-SMA_Usermanual_EN_v1.30.pdf).
L'identification visuelle ne constitue pas un test électrique du module.

La configuration fournie cible **ESP32 classique WROOM / DevKit**.
Elle ne s'applique pas automatiquement aux C3, C6, S2, S3 ou aux cartes avec
broches réservées. Ne rien brancher à partir d'un numéro de position de connecteur :
utiliser les noms inscrits sur le module CC1101 et sa documentation.

| Contact CC1101 | Signal | Inscription ESP32 |
|---|---|---|
| 1 | GND | GND |
| 2 | VCC | 3V3 uniquement |
| 3 | GDO0 | D27 |
| 4 | CSn | D5 |
| 5 | SCK | D18 |
| 6 | MOSI / SI | D23 |
| 7 | MISO / SO | D19 |
| 8 | GDO2 | non connecté |

Vue **côté composants** (première photo), antenne vers le haut :

```text
       Antenne
          ↑
   [composants CC1101]
     2   4   6   8   ← rangée proche de l'antenne
     1   3   5   7   ← rangée au bord de la carte
```

Attention : la vue du verso inverse gauche et droite. Utiliser les numéros
sérigraphiés côté composants comme référence. Brancher hors tension.

GPIO5 est une broche de strapping sur l'ESP32 classique : vérifier l'absence de
résistance externe incompatible ou choisir une autre broche disponible.
Utiliser des fils courts, une alimentation stable et une antenne adaptée 433 MHz.
Vérifier le module 433 MHz et son quartz 26 MHz. Couper l'alimentation avant câblage.
Ne connecter aucune broche au câblage interne du poêle.

Le câblage a été confirmé par l'utilisateur le 30 octobre 2026. La réception est
donc activée dans `platformio.ini` avec le réglage suivant sous `build_flags` :

```ini
    -DMCZ_WIRING_CONFIRMED=1
```

Sans ce réglage, le firmware affiche STOP et ne touche pas à la radio.
Ce réglage autorise l'accès à la radio. Le démarrage reste en réception ;
l'émission exige une commande USB explicite `!TX`, utilisée par l'application locale.

## Installation et compilation Windows

Depuis ce dossier, PowerShell sans privilèges administrateur :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:PLATFORMIO_CORE_DIR = Join-Path $PWD '.platformio'
$env:PLATFORMIO_SETTING_ENABLE_TELEMETRY = 'no'
.\.venv\Scripts\python.exe -m platformio run
```

Ces commandes installent les outils localement puis compilent, sans flasher de carte.
La plateforme ESP32 et PlatformIO sont versionnés ; la première compilation
télécharge le framework et le compilateur. Aucun code externe des dépôts étudiés
n'est ajouté comme dépendance au firmware.

Après vérification du matériel, identifier son port :

```powershell
.\.venv\Scripts\python.exe -m serial.tools.list_ports -v
.\.venv\Scripts\python.exe -m platformio run -t upload --upload-port COM7
.\.venv\Scripts\python.exe -m platformio device monitor --port COM7 --filter log2file
```

Remplacer COM7 par le port USB réel. L'upload remplace le firmware de l'ESP32 :
conserver au préalable tout firmware existant à sauvegarder. Ouvrir le moniteur
peut redémarrer la carte. Aucun de ces redémarrages n'entraîne d'émission RF.
Le filtre enregistre le journal dans un fichier local annoncé par le moniteur.

## Premier essai passif

1. Piles neuves dans la télécommande, antenne à 20–50 cm.
2. Vérifier `CC1101 PART=00 VERSION=...`, puis `RX READY`.
3. Envoyer `s` depuis le moniteur : `STATE=0D` est l'état RX attendu.
4. Envoyer `r` pour armer une capture brute, puis appuyer sur un bouton.
5. Sauvegarder des journaux distincts pour OFF, ON, puissance et chaque ventilation.
6. Rechercher plusieurs `MCZ FRAME VALID`, ID stable, CRC OK et paramètres cohérents.

La télécommande d'origine peut toujours agir normalement sur le poêle pendant
les essais : choisir les boutons et conditions en conséquence. Le POC n'arrête
pas le poêle et ne remplace aucun dispositif de sécurité.

Les impulsions positives représentent HIGH et les négatives LOW, en µs.
La commande `d` active/désactive un diagnostic par seconde : état radio,
nombre de fronts, échantillons RSSI, erreurs SPI, min/max du niveau reçu estimé.
Le RSSI est échantillonné environ toutes les 10 ms ; des signaux plus courts
peuvent être manqués et les valeurs ne constituent pas une mesure calibrée.
La commande `t` active/désactive l'export des blocs RMT lorsque le niveau dépasse
−85 dBm estimés : fenêtre de 700 ms, export des blocs d'au moins 80 durées.
Un réarmement est possible après une seconde. Une capture pleine/invalide
est signalée par `RMT_DROPPED` et rejetée. Les erreurs du pilote RMT doivent
également être recherchées dans le journal (`RMT RX BUFFER FULL`, etc.).
Le seuil sélectionne un signal fort, sans garantir qu'il provient de la télécommande.
Pour enregistrer le diagnostic pendant 30 secondes (ouverture du port pouvant
redémarrer l'ESP32) :

```powershell
.\.venv\Scripts\python.exe tools/record_serial.py --port COM3 --seconds 30 --diagnostics --label buttons
```

Ajouter `--trigger` pour conserver les impulsions lors des pics de signal.

### Contrôle exploratoire avec la télécommande de garage 868 MHz

Le module est une version 433 MHz : sa réception à 868 MHz n'est pas qualifiée
par le fabricant. Une absence de signal sur ce test ne permet pas de conclure.
Les touches série `1`, `2`, `3` sélectionnent respectivement les profils RX
868,30 / 868,95 / 869,85 MHz ; `0` rétablit 434,50 MHz. Les transitions passent
par IDLE, relisent les registres puis vérifient l'état RX. Le décodeur MCZ est
désactivé sur les profils 868 MHz. Aucun profil n'autorise l'émission.

```powershell
.\.venv\Scripts\python.exe tools/scan_garage.py --port COM3 --seconds-per-band 15
```

Ce test mesure les niveaux et le nombre de fronts pendant 15 secondes par bande.
Il tente toujours de rétablir le profil MCZ à la sortie et vérifie l'accusé de
réception série. Si la connexion USB est perdue ou le changement échoue,
redémarrer l'ESP32 pour retrouver le profil MCZ par défaut et vérifier son journal.
Les appuis sur la télécommande peuvent actionner la porte du garage.

Les séquences `RX_BURST_BEGIN` / `RX_BURST_END` se prêtent à l'analyse hors ligne.
La capture utilise maintenant le périphérique **RMT RX**, résolution 1 µs,
sur le même GDO0/GPIO27. Filtre matériel de 255 cycles APB (environ 3,19 µs),
512 mots matériels et tampon pilote 32 Kio. Ce filtre ne supprime pas les
parasites de 50–200 µs, qui restent visibles pour le diagnostic.
Les niveaux adjacents identiques sont fusionnés sans changer la durée totale.
Décodage et logs s'exécutent hors interruption.

Une pause de 3 ms termine un bloc : le préfixe long de 103 ms n'est pas mesuré
intégralement par ce mode. La dernière pause est représentée par une borne
minimale de 3000 µs, explicitement annoncée `idle_tail_min_us`, pour conserver
le dernier demi-bit Manchester. Cette borne n'est pas une mesure exacte de la
pause ni une reconstruction des données manquantes. Les captures de l'ancien
mode GPIO et du nouveau mode RMT doivent être distinguées dans les analyses.

L'absence de CRC valide ne signifie pas automatiquement « télécommande morte ».
Vérifier SPI, état RX, antenne, alimentation, fréquence/quartz et configuration
OOK avec une autre source connue avant cette conclusion. La bande RX et l'AGC
sont des réglages initiaux à qualifier ; ne pas les changer au hasard simultanément.

## Comparer deux trames

Outil Python sans dépendance ; exemples **synthétiques**, jamais des captures :

```powershell
python tools/compare_frames.py "A1 B2 C3 CD A0 36 C9" "A1 B2 C3 CD A8 B7 C1"
```

L'outil affiche l'intégrité, les paramètres et les bits modifiés de chaque octet.
Un CRC correct atteste l'intégrité selon le protocole supposé, pas l'authenticité
d'une télécommande ni l'exécution d'une commande par le poêle.

## Tests logiciels hors matériel

Sous Linux/WSL avec g++ (sans carte et sans accès RF) :

```sh
bash tools/check_native.sh
```

Ce script exécute les trois suites C++ avec détection des erreurs mémoire et
le test du lecteur de captures. Sous Windows, les tests Python de l'application
s'exécutent séparément :

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py' -v
```

Le test du lecteur C++ est ignoré dans cette dernière commande ; il est exécuté
par `check_native.sh`. Pour compiler manuellement le décodeur :

```sh
g++ -std=c++11 -Wall -Wextra -Werror -fsanitize=address,undefined -Isrc tests/test_decoder.cpp src/mcz_decoder.cpp src/mcz_crc.cpp -o /tmp/mcz-test
/tmp/mcz-test
g++ -std=c++11 -Wall -Wextra -Werror -Isrc tools/decode_capture.cpp src/mcz_decoder.cpp src/mcz_crc.cpp -o /tmp/mcz-decode
MCZ_DECODER=/tmp/mcz-decode python3 tests/test_tools.py
/tmp/mcz-decode captures/ma-capture.log
```

Les tests couvrent le CRC XMODEM connu, les champs, les répétitions, la polarité,
les variations de temps, la parité, start/stop, le drapeau de premier octet,
le mauvais CRC, les troncatures, les limites et le bruit déterministe.
Le lecteur de journal renvoie 0 si au moins une trame valide, 1 sinon, 2 si erreur.

## Suite

Renseigner `docs/VALIDATION.md` à partir de vraies captures. L'émission USB est
implémentée ; sa réception et la réaction physique du poêle restent à qualifier.
Garder les sécurités MCZ intactes ;
ne jamais utiliser une coupure électrique pour arrêter normalement le poêle.
