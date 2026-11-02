# Revue et validation du 2 novembre 2026

## 1. Analyse

Relecture du code propre au projet : serveur HTTP et lancement Windows,
passerelle USB, page HTML/CSS/JavaScript, firmware ESP32/CC1101,
CRC, décodage/encodage, traitement des impulsions et outils de capture/analyse.
Les sources tierces conservées dans `research/` ne sont pas des dépendances
du firmware et ne font pas partie du code maintenu revu ici.

Le dossier ne contient pas de dépôt Git ; aucun historique ni état antérieur
versionné n'a pu être comparé. Aucun téléversement de firmware effectué.

## 2. Recommandation

Conserver l'architecture locale actuelle. La compilation, les tests hors
matériel, les parcours navigateur simulés et la lecture du statut USB réel
réussissent. La réception de la commande radio par le poêle reste à qualifier.

## 3. Implémentation

Corrections dans `app/bridge.py` :

- Un JSON USB valide mais de type liste, nombre ou null pouvait arrêter
  définitivement le lecteur avec une exception. Les objets inattendus,
  données mal encodées et imbrications excessives sont désormais ignorés.
- Un résultat reçu sans requête active pouvait accéder à une entrée absente.
  Les résultats sans requête correspondante sont désormais ignorés.
- `readline` peut retourner une ligne partielle après son délai de 200 ms.
  Les fragments sont maintenant conservés jusqu'au saut de ligne, avec une
  limite de 2048 octets. Une ligne trop longue est rejetée intégralement.
- Les trames hexadécimales contenant des espaces passaient la validation CRC
  mais étaient refusées par le protocole série du firmware. Les profils
  sont désormais normalisés en 14 caractères hexadécimaux avant envoi.
- Les réponses aux requêtes déjà connues sont copiées sous verrou pour éviter
  qu'un autre fil modifie leur contenu après le retour.

Correction dans `app/server.py` : un jeton HTTP contenant des caractères
non ASCII provoquait une exception dans la comparaison. Il est maintenant
refusé normalement par une réponse 403, sans appel à la passerelle.

Ajout de six tests Python de régression : profils espacés, messages USB
invalides, fragments/limites, déconnexion, timeout/réponse tardive et requêtes
simultanées. Extension du test HTTP aux jetons non ASCII et requêtes cross-site.
Ajout de `tools/check_native.sh` pour reproduire les trois suites C++ et le test
du lecteur de captures. Dépendance directe `pyserial==3.5` déclarée explicitement.
README corrigé pour refléter le firmware RX/TX actuel.

## 4. Sécurité et risques

Les protections Host/Origin/jeton, écoute sur 127.0.0.1, CRC et identifiant radio
restent en place. Les tests confirment qu'une panne, un doublon, une requête
simultanée ou une réponse tardive ne déclenchent pas de nouvelle tentative.
Les caches d'identifiants restent bornés et volatils : aucune garantie de
déduplication persistante après redémarrage ou éviction du cache n'est revendiquée.

La vérification USB réelle a uniquement interrogé le statut avec `j`.
Aucune commande `!TX`, aucun clic réel et aucun changement du firmware installé.
L'ouverture du port série peut redémarrer l'ESP32 ; son démarrage reste passif.

## 5. Validation

| Vérification | Résultat |
|---|---|
| Python Windows : `python -m unittest discover -s tests -p 'test_*.py' -v` avec le Python de `.venv` | 19 réussis ; 1 test C++ optionnel ignoré sur Windows |
| Linux/WSL : `bash tools/check_native.sh` | 3 suites C++ réussies avec AddressSanitizer et UndefinedBehaviorSanitizer ; 3 tests d'outils Python réussis, dont celui ignoré sur Windows |
| Firmware : `.venv/Scripts/python.exe -m platformio run` | Réussite ; RAM 26 520 octets (8,1 %), Flash 300 041 octets (22,9 %) |
| JavaScript : `node --check app/web/app.js` | Réussite |
| Python : `python -m compileall -q app tools tests` | Réussite |
| Dépendances : `python -m pip check` | Aucune dépendance incohérente |
| Audit statique UI strict | Aucun constat ; `revue-ui-20261102.json` |
| Navigateur, serveur simulé sur 8766 sans USB | Chargement, envoi/attente, succès, résultat incertain, clavier, focus restauré, déconnexion et reconnexion réussis ; aucun avertissement/erreur console observé |
| Affichage navigateur à 375 × 812 | Largeur du document = 375 px ; aucun débordement horizontal |
| ESP32 réel sur COM3, lecture du statut uniquement | `connected=true`, `profiles_ready=true`, `busy=false`, `last=null`, `tx_count=0` |

Les restrictions initiales empêchaient les connexions HTTP locales et certains
outils Windows/WSL. Les vérifications concernées ont ensuite réussi avec
l'accès nécessaire autorisé, sans assouplir les protections de l'application.

Au total, les 20 tests Python distincts ont été exécutés avec succès entre
Windows et WSL. La capture `revue-20261102.png` montre uniquement l'aperçu simulé.
Le serveur d'aperçu utilisé pour la revue est arrêté après les vérifications.

## 6. Alternatives et limites

Aucune refonte ni dépendance web supplémentaire nécessaire.
La qualification de bout en bout exige encore un essai supervisé : envoyer une
commande depuis la page réelle, observer le poêle et respecter son cycle normal
d'arrêt. Un résultat « envoyée » confirme la fin du traitement firmware, sans
constituer un accusé de réception du poêle ni une mesure RF.

Les tests avec détection d'erreurs mémoire valident le code C++ hors périphériques ; ils ne
simulent pas les défauts électriques SPI, le périphérique RMT ou l'étage radio.
La lecture USB réussie ne constitue pas un essai de déconnexion physique prolongé.
