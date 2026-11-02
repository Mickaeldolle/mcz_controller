# Application locale USB — 30 octobre 2026

Le propriétaire a demandé explicitement la phase émission et choisi une page
sur le PC, avec ESP32 branché en USB. Cette évolution succède au POC RX ; les
rapports RX antérieurs décrivent leur version historique.

## Utilisation

1. Brancher l'ESP32 avec le câblage déjà validé ; conserver l'antenne.
2. Ouvrir `Demarrer-MCZ.cmd` dans le dossier du projet.
3. Accéder à http://127.0.0.1:8765 ; attendre « ESP32 connecté ».
4. Cliquer Allumer ou Éteindre et vérifier le poêle. L'état affiché ne sera
   jamais déduit du dernier clic. Respecter son cycle normal d'arrêt.

Le PC et le serveur doivent rester en marche. Aucun Wi-Fi ni compte requis.
Pour arrêter le serveur lancé dans une console : Ctrl+C. Une instance lancée
en arrière-plan pendant cette mise en place est déjà disponible sur le port 8765.
Ne pas lancer deux instances ; si la page fonctionne déjà, utiliser celle-ci.

## Commandes enregistrées

Source réelle : `captures/20261030-124843_buttons.log`, capture passive pendant
les appuis demandés Allumer puis Éteindre. Identifiant C8CC02.

| Bouton | Trame complète | Mode | Nombre reçu |
|---|---|---|---|
| Allumer | C8 CC 02 8F B8 8E 16 | 3 | 5 |
| Éteindre | C8 CC 02 8C B8 DB 45 | 0 | 5 |

Le CRC XMODEM est vérifié séparément par Python et par le firmware.
Ces trames conservent aussi les réglages capturés : puissance 3, ventilation 1
à 4, ventilation 2 à 7 et utilisateur 2. Le sens opérationnel de fan2=7 reste
non qualifié. Allumer restaure cette commande capturée ; ce n'est pas une
commande indépendante de tous les réglages. Aucune synthèse d'autres réglages.

## Architecture et protections

Navigateur → serveur Python local → USB COM3 → firmware → CC1101.

- HTML/CSS/JavaScript sans dépendance web, police locale, interface française.
- Serveur Python standard + pyserial, profil dans `config/power_profiles.json`.
- Écoute 127.0.0.1 seulement ; contrôle Host/Origin, jeton aléatoire au lancement,
  requêtes POST bornées, aucune commande en GET, politique CSP locale.
- Actions limitées à on/off ; les octets radio ne sont pas fournis par le navigateur.
- Validation CRC et identifiant par le firmware ; commande explicite avec identifiant
  de requête, cache des 16 dernières requêtes côté ESP32 et 512 côté PC.
- Un seul envoi à la fois, délai de 3 secondes, aucune file d'attente ni relance
  après timeout/reconnexion. Résultat « non confirmé » si accusé USB manquant.
- Aucun envoi au démarrage, à l'ouverture, au rafraîchissement ou à la reconnexion.
- Bascule GDO0 en haute impédance côté CC1101 avant sortie ESP32, puis retour
  en entrée ESP32 avant restauration RX. Timeout du signal RMT 1,5 seconde.
- Encodage Manchester, préambule par octet, 5 répétitions, durée totale nominale
  512790 µs. Les longs niveaux sont découpés sans changer leur durée.
- Puissance radio nominale 0 dBm, sans mesure de puissance rayonnée. Paramètres
  fondés sur la [documentation TI CC1101](https://www.ti.com/lit/ds/symlink/cc1101.pdf),
  sections 24–27, et les sources déjà référencées dans ANALYSE_PROTOCOLE.md.

L'accès local HTTP n'est pas destiné à être publié. Ne pas remplacer l'adresse
d'écoute par 0.0.0.0 ou désactiver les contrôles pour exposer le service.
Les profils ne sont pas des secrets d'authentification ; le protocole radio
existant ne doit pas être assimilé à un lien chiffré et authentifié.

## Validation et limites

- Compilation PlatformIO réussie et téléversement USB vérifié par esptool.
- Encodeur natif testé sous AddressSanitizer et UndefinedBehaviorSanitizer :
  cinq trames redécodées à l'identique, durée et CRC, rejet du CRC invalide.
- Tests Python : profils, absence d'envoi à la construction/hors ligne/GET,
  doublon, changement d'action avec même ID, panne USB sans relance,
  filtres Host/Origin/jeton et validation des entrées.
- Capture réelle des deux commandes : 10 trames valides, analyse indépendante
  dans `power-capture-analysis.json`.
- Vérification navigateur sur un serveur simulé sans ouverture USB : chargement,
  envoi et attente, résultat réussi et incertain, déconnexion et reprise,
  clavier avec retour du focus, écran 375px sans débordement.
- Résultat final : 13 tests Python réussis, un test optionnel ignoré ; trois
  suites C++ réussies avec les sanitizers. Audit UI strict sans constat bloquant.
- Serveur réel : liaison COM3 prête, compteur TX=0 vérifié par lecture du statut
  (`application-status-verified.json`). Aucun clic réel effectué par l'agent.
- L'émission effective et la réaction du poêle ne sont pas encore qualifiées :
  ni mesure à l'analyseur RF ni accusé de réception du poêle disponible.
- « Envoyée » signifie que le firmware a terminé son signal et restauré RX.
  Cela ne garantit ni puissance rayonnée, ni appairage, ni démarrage du poêle.

Tests Python : `.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py'`.
Un test optionnel de l'ancien décodeur hors ligne est ignoré sans son exécutable.
Les tests HTTP peuvent demander la sortie du bac à sable pour les sockets locales.

## Dépannage et retour arrière

Si déconnecté : vérifier USB, COM3 et l'absence d'autre moniteur série. Si le
firmware échoue à restaurer RX, débrancher/rebrancher l'ESP32 ; aucune commande
ne sera rejouée. Si non confirmé : observer le poêle avant de décider d'un nouvel
appui. Ne pas multiplier les commandes pour masquer une panne radio.

Pour revenir à un usage passif : arrêter le serveur. Le firmware reste en
réception tant qu'aucune commande USB explicite n'est reçue. Les outils de
capture existants continuent à utiliser r, s, d et t. Aucune modification du
poêle, de son installation électrique ou de sa procédure d'arrêt n'a été faite.
