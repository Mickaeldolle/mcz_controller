# Mise en service ON/OFF du MCZ Musa par ESP32 et CC1101

Procédure proposée le 2 novembre 2026, à partir du
[bilan des blocages](BLOCAGES_ALLUMAGE_EXTINCTION.md).

## 1. Objectif, périmètre et état initial

Objectif : depuis la page locale du PC Windows, envoyer une commande manuelle
ON capturée, observer son acceptation par le poêle, puis envoyer OFF et
observer son cycle normal d'arrêt.

Cette procédure est exécutable avec l'architecture existante. Elle décrit les
changements encore à appliquer ; **les profils actifs n'ont pas été modifiés
par la rédaction du document**. Aucun résultat physique n'est présumé.

**Précision terrain confirmée : le poêle ne répond déjà plus à sa télécommande
d'origine, dont notre ESP32 reçoit pourtant les trames valides.** Le succès
de notre émetteur est donc conditionnel au fonctionnement du chemin de réception
et à l'acceptation des commandes par le poêle. Avant de traiter cette procédure
comme une mise en service, suivre le diagnostic préalable ci-dessous.

Le démarrage local est maintenant confirmé : sélecteur sur ON, le poêle
démarre ; sélecteur sur REMOTE, l'appui ON de la télécommande ne déclenche
pas d'allumage. Il s'agit d'une absence de réaction constatée, sans preuve
permettant encore de distinguer absence de réception et commande ignorée.

L'utilisateur confirme aussi une tentative d'association avec « --- » affiché,
puis ON/OFF sur la télécommande, sans bip ni confirmation. Ce résultat est
acquis ; la procédure ci-dessous ne doit pas demander de refaire cet essai
à l'identique sans nouvelle hypothèse ou contrôle discriminant.

Le premier profil retenu est : ID C8CC02, mode manuel 1, puissance 1,
ventilation 1 à 2, paramètres complémentaires inchangés par rapport à la capture.
Ce choix reproduit un réglage réellement émis, sans thermostat à reconstruire
et sans générer de paramètres non observés.

## 2. Préparer le matériel et un état de départ connu

### Résultat du premier essai exécuté

Le [2 novembre à 22:46](ESSAI_TX_20261102_APPARIAGE.md), l'envoi unique
ESP32 de la trame manuelle ON a retourné `sent`, compteur TX de 0 à 1 et
nouveau statut RX prêt. Le poêle en apprentissage n'a pas réagi : « --- »
est resté affiché sans bip, à moins d'un mètre et sans obstacle.
Le port a été libéré, sans nouvel envoi. Avant de répéter cet essai,
la priorité est de qualifier indépendamment la sortie RF et de recouper
la procédure d'apprentissage exacte ; le résultat logiciel ne suffit pas.

### Essai d'appairage isolé disponible depuis le 2 novembre

L'outil `tools/pair_once.py`, lancé par `Appairer-MCZ.cmd`, permet maintenant
de tester le rejeu ON manuel sans changer les profils actifs de l'application
ni leurs tests historiques. Il utilise
[les profils manuels séparés](../config/manual_capture_profiles.json), vérifie
leurs CRC et leur présence dans le journal source, ouvre COM3 et attend un
statut prêt. Aucun ordre TX n'est envoyé à cette préparation.

Quand le poêle affiche « --- » et que l'opérateur est présent, saisir
`ENVOYER` dans cet outil déclenche **une seule commande**, contenant les cinq
répétitions de `C8 CC 02 45 B8 77 89`. Toute autre réponse annule. Une panne
ou un résultat incertain n'entraîne aucun renvoi. Le résultat USB, le compteur
TX et un statut reçu après l'envoi sont consignés dans `captures/*_pairing.log`.
L'observation du bip, de l'afficheur et de la réaction physique reste nécessaire.

Ce chemin suffit pour l'essai d'appairage : les étapes 3 à 5 de modification
des profils de l'application ne sont pas nécessaires à cet outil isolé.
Ce n'est pas une nouvelle trame d'apprentissage : nous testons une capture ON
connue. Son acceptation pendant l'apprentissage n'est pas encore démontrée.

Le câblage reste GDO0 ↔ GPIO27. Le firmware bascule cette liaison de RX vers
TX, puis revient en RX. Il n'existe pas de mode TX permanent à activer avant
l'essai ni de fil à déplacer. Pendant que cet outil possède COM3, fermer le
moniteur et le serveur MCZ. L'ouverture USB peut redémarrer l'ESP32 ; aucun
envoi n'a lieu au démarrage.

### Diagnostic préalable dans la situation actuelle

- Résultat déjà établi : le démarrage local fonctionne avec le sélecteur sur
  ON. Ne pas répéter ce démarrage pour obtenir de nouveau cette information.
  La recherche se concentre maintenant sur la commande distante en REMOTE.
- Vérifier visuellement le sélecteur REMOTE et relever toute alarme ou état
  qui inhibe normalement une commande. Ne pas contourner les sécurités.
- Une association a déjà échoué malgré l'affichage « --- » puis ON/OFF.
  Recouper les détails avec la notice exacte, sans supposer une panne du
  récepteur sur ce seul résultat et sans inventer de trame d'apprentissage.
- Pour progresser, comparer l'émission d'origine à un essai ESP32 maîtrisé.
  Si l'ESP32 fonctionne, une commande RF peut être acceptée par le poêle.
  Si les deux sont ignorés, vérifier la sortie RF de notre montage avant
  d'attribuer définitivement la panne au poêle.
- Si la télécommande reste ignorée, un essai ESP32 est un test de substitution
  d'émetteur, dont le succès ne peut être promis. Sa sortie RF doit être
  qualifiée si l'essai échoue ; un simple résultat `sent` ne suffit pas pour
  déclarer le récepteur du poêle défectueux.
- Ne pas commander un autre émetteur, augmenter la puissance ou changer l'ID
  uniquement pour masquer une absence de diagnostic. Le mainteneur du poêle
  peut être nécessaire si l'association et le chemin de réception restent en échec.

### Préparation de l'essai lorsque les conditions sont réunies

1. Garder les sécurités et commandes d'origine du poêle opérationnelles.
   Choisir un moment où un démarrage est souhaité, avec une personne présente
   pour observer le poêle jusqu'au traitement de l'arrêt.
2. Vérifier un état autorisant normalement le démarrage, sans alarme active,
   et le sélecteur du panneau d'urgence sur **REMOTE**. Ne pas lancer l'essai
   pendant une phase d'arrêt/refroidissement qui doit d'abord se terminer.
3. Consigner le défaut déjà confirmé de la télécommande d'origine, le résultat
   des commandes locales et celui de l'éventuelle association. Si la situation
   change, relever précisément quelle action rétablit le contrôle du poêle.
4. Après ce contrôle, ne plus actionner la télécommande pendant l'essai ESP32.
   Si nécessaire, retirer temporairement ses piles pour isoler ce test manuel ;
   cela peut remettre son heure/réglages à zéro selon le modèle. Les restaurer
   ensuite conformément à son manuel.
5. Couper l'alimentation du montage avant toute intervention sur ses fils.
   Le CC1101 est alimenté en **3,3 V**, jamais en 5 V. Garder antenne adaptée
   et connexions courtes. Ne rien relier au câblage interne du poêle.

| Signal CC1101 | GPIO ESP32 classique |
|---|---:|
| SCK | 18 |
| MOSI | 23 |
| MISO | 19 |
| CSn | 5 |
| GDO0 | 27 |
| VCC / GND | 3V3 / GND |
| GDO2 | Non connecté |

Ce câblage est celui du projet actuel. Les broches des références ESP32-C6 ou
S2 ne sont pas à recopier sur cette carte. GPIO5 étant une broche de strapping,
conserver le câblage déjà validé sans résistance externe incompatible.

## 3. Sauvegarder avant modification

Fermer le serveur MCZ, le moniteur de trames et les outils série, avec Ctrl+C.
Les commandes ci-dessous se lancent depuis la racine du projet, sans privilèges
administrateur. Cette première commande copie la configuration ; elle n'ouvre
pas le port USB et ne modifie pas le poêle.

```powershell
$mczBackup = "config/power_profiles.before-manual-$(Get-Date -Format yyyyMMdd-HHmmss).json"
Copy-Item -LiteralPath config/power_profiles.json -Destination $mczBackup
Write-Output $mczBackup
```

Conserver aussi une copie des fichiers de tests avant de les adapter à l'étape 5.
Le dossier de travail ne contient actuellement pas de dépôt Git racine : ne pas
compter sur un retour arrière Git qui n'existe pas. Les copies des références
dans `research/` ont leur propre historique, distinct de notre projet.

## 4. Préparer les deux profils manuels

Remplacer le contenu de `config/power_profiles.json` par le JSON suivant :

```json
{
  "remote_id": "C8CC02",
  "source": "captures/20261102-215528-553832_live.log",
  "on": "C8CC0245B87789",
  "off": "C8CC0244B844B8"
}
```

| Action | Trame | Signification des champs vérifiés |
|---|---|---|
| Allumer | C8 CC 02 45 B8 77 89 | Manuel 1, puissance 1, ventilation 1 à 2 |
| Éteindre | C8 CC 02 44 B8 44 B8 | Arrêt 0, puissance et ventilation conservées dans la commande |

Ces trames viennent du journal déclaré, avec respectivement dix et cinq
occurrences : le niveau 1 a été atteint à l'allumage puis au retour des quatre
diminutions. Il ne faut donc pas exiger exactement cinq occurrences de ON dans
ce fichier de provenance.

Le journal source doit être présent lors de l'installation : les captures
`*.log` sont exclues par le `.gitignore` du projet. Sur un autre PC, copier
explicitement ce fichier avec le projet ; ne pas remplacer une provenance
manquante par un nom de fichier fictif.

Vérifier le chargement, l'ID, la longueur et le CRC avec le validateur existant :

```powershell
@'
from app.bridge import load_profiles
profiles = load_profiles()
print("ON :", profiles["on"])
print("OFF:", profiles["off"])
'@ | .\.venv\Scripts\python.exe -
```

Résultat attendu : les deux chaînes ci-dessus, sans erreur. Cette commande
importe la passerelle mais ne la démarre pas : elle ne touche pas à l'USB.
Une erreur impose de corriger le fichier avant tout essai physique.

Si `.venv` est absent sur un nouveau PC, préparer les dépendances localement :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Ces commandes écrivent dans l'environnement Python local et peuvent télécharger
les paquets ; elles n'émettent pas de commande RF.

## 5. Adapter les tests aux profils et au journal retenus

Cette adaptation est nécessaire pour cette procédure : le test actuel compte
les lignes `Raw:` des anciens journaux, alors que le nouveau journal contient
des lignes `RX #...`. Deux attentes fixes utilisent également les anciens octets.
Sans cette adaptation, des tests échoueraient à cause du changement de fixture,
même si les nouvelles trames ont un CRC correct.

Dans [tests/test_app.py](../tests/test_app.py), ajouter `import re`, puis remplacer
uniquement la méthode `test_profiles_and_real_capture` par :

```python
def test_profiles_and_real_capture(self):
    profiles = load_profiles()
    log = (Path(__file__).resolve().parents[1] / profiles["source"]).read_text(encoding="utf-8")
    frames = re.findall(r"\b[0-9A-F]{2}(?: [0-9A-F]{2}){6}\b", log)
    for action in ("on", "off"):
        expected = bytes.fromhex(profiles[action]).hex(" ").upper()
        self.assertGreaterEqual(frames.count(expected), 5)
```

Cette extraction accepte les deux présentations de journal et garde un seuil
de cinq observations réelles du profil. Ne pas supprimer le contrôle de provenance.

Mettre également à jour les trois attentes littérales :

| Méthode | Attente précédente | Attente pour ce profil manuel |
|---|---|---|
| `test_profiles_are_normalized_for_firmware`, ON | `C8CC028FB88E16` | `C8CC0245B87789` |
| Même méthode, OFF | `C8CC028CB8DB45` | `C8CC0244B844B8` |
| `test_duplicate_exactly_once_and_no_action_change`, octets contenus dans l'écriture | `b"C8CC028CB8DB45"` | `b"C8CC0244B844B8"` |

Ces changements de tests sont proposés ici, pas encore appliqués au projet.
Un futur refactoring pourra séparer les fixtures fixes des profils actifs ;
ce n'est pas nécessaire pour le premier essai contrôlé.

La procédure ci-dessus a été vérifiée dans une copie temporaire du projet :
24 tests réussis, un test C++ optionnel ignoré sous Windows. Les six trames
manuelles ont aussi été encodées/redécodées avec les fonctions C++ du projet,
en cinq répétitions identiques chacune, sans périphérique radio. Cette preuve
locale ne constitue pas l'application des changements à notre configuration active.

Exécuter les contrôles hors émission :

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py' -v
$env:PLATFORMIO_SETTING_ENABLE_TELEMETRY = 'no'
.\.venv\Scripts\python.exe -m platformio run
```

Les tests HTTP ouvrent seulement des sockets locales avec une passerelle simulée.
Le build compile sans téléverser. Attendre l'absence d'échec ; le test optionnel
du lecteur C++ peut être ignoré sur Windows. Une coupure HTTP locale Windows
10053 a été observée ponctuellement : si elle se répète, diagnostiquer le poste
et les requêtes avant l'essai, sans désactiver les protections du service.

Sous Linux/WSL, les contrôles C++ complémentaires se lancent sans accès RF :

```sh
bash tools/check_native.sh
```

Résultat attendu : trois suites C++ réussies et trois tests Python d'outils réussis.

## 6. Firmware : conserver ou réinstaller une version connue

Changer les profils JSON ne nécessite pas de modifier le firmware. La carte
actuelle dispose du protocole USB RX/TX selon les validations précédentes.
Un simple statut `j` ne porte toutefois pas de version ni de hash du binaire.

Si le firmware est déjà identifié et que ses sources n'ont pas changé,
passer à l'étape 7. Sinon, après compilation réussie, archiver le binaire :

```powershell
New-Item -ItemType Directory -Path captures/firmware -Force | Out-Null
Copy-Item -LiteralPath .pio/build/esp32dev/firmware.bin -Destination captures/firmware/firmware-onoff.bin
Get-FileHash -LiteralPath captures/firmware/firmware-onoff.bin -Algorithm SHA256
```

Cette copie archive le binaire compilé, **pas** une sauvegarde du firmware
précédemment installé sur la carte. Avant réinstallation, conserver le projet
ou une sauvegarde connue permettant de restaurer la version précédente.

Pour installer le firmware du projet, uniquement si cette réinstallation est
nécessaire et voulue :

```powershell
.\.venv\Scripts\python.exe -m platformio run -t upload --upload-port COM3
```

L'upload remplace le firmware et redémarre l'ESP32. Il ne doit pas déclencher
d'émission RF au démarrage. Tous les autres propriétaires de COM3 doivent être
fermés. Ne pas flasher les YAML des références pour résoudre un échec non isolé.

## 7. Démarrer l'application et contrôler le statut

Lancer `Demarrer-MCZ.cmd`, ou utiliser la commande manuelle équivalente :

```powershell
.\.venv\Scripts\python.exe -m app.server --serial-port COM3
```

Garder cette console ouverte et ouvrir [la page locale](http://127.0.0.1:8765).
Attendre « ESP32 connecté ». L'ouverture et le rafraîchissement de la page ne
doivent provoquer aucune émission. Une seule instance doit être active, et
elle doit avoir été démarrée après le changement des profils.

Pour lire le statut depuis une seconde console :

```powershell
$mczStatus = Invoke-RestMethod -Uri http://127.0.0.1:8765/api/status
$mczStatus | Select-Object connected,busy,profiles_ready,port,tx_count,last
```

Résultat attendu : `connected=True`, `busy=False`, `profiles_ready=True`, port
COM3. Noter le compteur TX initial. Une valeur non nulle peut correspondre à
des essais antérieurs depuis le dernier redémarrage ; elle n'est pas un état
du poêle. Cette lecture n'envoie que des demandes de statut.

Ne pas ouvrir `Ecouter-MCZ.cmd` en parallèle : le serveur possède déjà COM3.

## 8. Essai physique ON puis OFF

### ON : une seule commande

1. Confirmer l'état de départ, la présence d'une personne et la disponibilité
   d'un moyen d'arrêt d'origine conforme au manuel du poêle.
2. Cliquer **une fois** sur Allumer. Un clic représente une commande contenant
   les cinq répétitions du protocole, pas cinq demandes indépendantes.
3. Relever le résultat et le compteur TX après traitement. Normalement, il
   progresse d'une unité ; un redémarrage invaliderait cette comparaison.
4. Observer l'afficheur et l'entrée dans le cycle d'allumage normal, en notant
   le moment. Le délai d'apparition de la flamme n'est pas un timeout logiciel :
   utiliser les indications du poêle et son manuel, sans fixer arbitrairement
   un délai de quelques secondes pour toute la phase d'allumage.

### OFF : un cycle d'arrêt normal

1. Lorsque l'état de fonctionnement permet normalement la commande d'arrêt,
   cliquer **une fois** sur Éteindre.
2. Relever résultat, compteur et début du cycle d'arrêt sur le poêle.
3. Laisser sa ventilation et son refroidissement se terminer naturellement.
   Ne pas couper le secteur pour simuler une extinction.

| Retour de l'application | Signification | Action |
|---|---|---|
| Envoyée / `sent` | Le firmware a terminé le signal et restauré RX | Vérifier la réaction du poêle ; aucune confirmation physique implicite |
| Non confirmé / `uncertain` | L'émission ou le retour d'information a pu être incomplet | Observer le poêle avant toute nouvelle décision ; pas de renvoi automatique |
| Indisponible / `unavailable` | Radio ou liaison non prête | Corriger USB/profil/état RX, sans multiplier les clics |
| Occupé / `busy` | Commande en cours ou délai de protection | Attendre la fin ; aucune file de commandes à alimenter |
| Refusée / `rejected` | Commande rejetée | Revoir ID, CRC et profil avant tout nouvel essai |

Le délai de trois secondes de l'application est une protection contre les
envois rapprochés, **pas** un délai autorisant le redémarrage thermique du poêle.
Le firmware a aussi un verrou temporel de deux secondes. Respecter les cycles
physiques même lorsque les boutons redeviennent disponibles.

## 9. Si le poêle ne réagit pas : isoler la cause

| Observation | Vérification suivante |
|---|---|
| ON local confirmé, télécommande sans effet et aucun bip après « --- » puis ON/OFF | Échec d'association déjà constaté ; vérifier la procédure exacte, puis comparer les émetteurs et le chemin réception/décodage/apprentissage |
| Situation initiale confirmée : télécommande reçue par l'ESP32 mais ignorée du poêle | Commandes locales, REMOTE, alarmes, association exacte ; le décodage ESP32 ne prouve pas une réception par le poêle |
| ESP32 non connecté | Port USB, carte, exclusivité COM3, journal de démarrage |
| `uncertain`, puis plus de statut prêt | Retour RX ou SPI en erreur ; redémarrer la carte et vérifier son état, sans rejouer automatiquement la commande |
| `sent` et compteur TX augmente, aucune réaction | Vérifier le profil réellement chargé, puis comparer l'émission avec un récepteur indépendant |
| GPIO27 présente la forme attendue, mais pas de signal RF mesuré | Alimentation/module/antenne, configuration TX et puissance nominale |
| Le signal RF est décodé avec les bons octets, mais le poêle ignore aussi la télécommande | REMOTE, alarmes, association et récepteur du poêle deviennent prioritaires |
| La télécommande commande réellement le poêle, notre RF correctement décodée n'agit pas | Comparer fréquence réelle, niveau, polarité, préfixe, séparateurs et répétitions ; les sept octets seuls ne qualifient pas toute l'émission |

Le second récepteur doit d'abord décoder la télécommande d'origine pour que
son silence sur notre émission soit interprétable. Un analyseur logique vérifie
la broche numérique, pas la porteuse radio. Le CC1101 actuel est demi-duplex :
il ne peut pas servir de témoin RX pendant sa propre émission.

Ne pas changer simultanément fréquence, puissance, trames et timing. Conserver
les 414 µs de l'encodeur RMT ; les 393 µs d'APPLI_MCZ compensent un autre chemin
logiciel. Ne pas recopier automatiquement les 10 dBm du projet ESPHome.

Si l'association doit être refaite, utiliser la notice exacte de la génération
du poêle et constater sa confirmation. Ce guide ne suppose ni une commande
spéciale inventée ni l'efficacité garantie d'une commande ordinaire en mode
appairage. Garder l'ID C8CC02 tant qu'aucune preuve n'impose de le changer.

## 10. Critères d'acceptation et preuve à conserver

Un succès exige simultanément :

- Les deux profils chargés correspondent aux captures manuelles choisies.
- Le système reste passif au démarrage et à la reconnexion.
- Un clic ON produit un résultat cohérent et une réaction d'allumage observée.
- Un clic OFF produit un résultat cohérent et un cycle normal d'arrêt observé.
- L'ESP32 redevient prêt en réception après chaque commande.
- Aucune relance automatique ni commande concurrente ne brouille l'essai.

Un premier cycle valide la faisabilité dans ces conditions, pas la fiabilité
à toute distance. Répéter lors de cycles d'usage ultérieurs souhaités, sans
enchaîner artificiellement les démarrages pour fabriquer un taux de succès.

Créer une fiche `docs/ESSAI_TX_YYYYMMDD.md` et renseigner :

```text
Date, modèle exact du poêle, position REMOTE, état et éventuelles alarmes :
Réaction réelle à la télécommande d'origine :
Version ou hash du firmware et résultat du build :
Port, distance et disposition du montage/antenne :
Fichier des profils et trames ON/OFF :
Heure ON, résultat application, compteur avant/après, observation du poêle :
Heure OFF, résultat application, compteur avant/après, observation du poêle :
Retour RX après chaque commande, déconnexion ou redémarrage éventuel :
Télécommande isolée pendant l'essai :
Capture indépendante ou photo de l'afficheur si disponible :
Conclusion : émission seule / ON confirmé / OFF confirmé / cycle complet confirmé :
```

## 11. Exploitation et retour arrière

Le serveur et le PC doivent rester disponibles pour envoyer OFF. Une minuterie
logicielle ne constitue pas une garantie d'extinction si le PC, l'USB ou la radio
tombe en panne. Garder les commandes d'origine accessibles ; ne pas automatiser
sans surveillance tant que les échecs ne sont pas observables.

Pour revenir à la configuration précédente : arrêter le serveur, restaurer le
JSON sauvegardé à l'étape 3 et remettre les attentes de tests correspondant à
ce profil, puis relancer le serveur. Restaurer un JSON n'arrête pas un poêle
déjà en marche : effectuer d'abord son arrêt normal si nécessaire.

Le firmware inchangé peut rester installé. Si une version de firmware a été
remplacée, son retour arrière nécessite de réinstaller une version connue,
pas de restaurer uniquement les profils JSON.

Références : [fonctionnement des trames](FONCTIONNEMENT_TRAMES_MCZ.md),
[comparaison des projets et blocages](BLOCAGES_ALLUMAGE_EXTINCTION.md),
[application locale actuelle](APPLICATION_LOCALE.md).
