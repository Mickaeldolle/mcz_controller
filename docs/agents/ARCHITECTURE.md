# Architecture et carte du code

Retour au [guide des agents](../../AGENTS.md).

## Chaîne de commande

```text
Navigateur → app/server.py → app/bridge.py → USB 115200 bauds
          → src/main.cpp → encodeur → RMT TX → CC1101 → onde RF → poêle
```

Le dernier maillon n'a pas d'accusé d'exécution exploité dans ce projet.
La page ne connaît donc pas l'état réel du poêle.

| Chemin | Responsabilité |
|---|---|
| `app/web/` | HTML, CSS et JavaScript natifs ; deux actions et retour d'état USB |
| `app/server.py` | Serveur HTTP local, routes, validation et protections d'origine |
| `app/bridge.py` | Chargement des profils, propriétaire USB, statut, verrou et anti-doublon |
| `app/launch.py` | Ouvre l'instance locale reconnue ou lance le serveur |
| `src/main.cpp` | Commandes série, capture RMT RX, bascule TX/RX et compteurs |
| `src/cc1101_radio.*` | SPI, registres CC1101, états radio et profils RX |
| `include/radio_config.h` | Broches et constantes RX ; verrou de confirmation du câblage |
| `src/mcz_crc.*` | CRC16 XMODEM |
| `src/mcz_decoder.*` | Décodage des impulsions, validation des mots et des sept octets |
| `src/mcz_encoder.*` | Encodage de la commande et de ses cinq répétitions |
| `src/mcz_pulses.*` | Assemblage borné des impulsions mesurées |
| `config/power_profiles.json` | Profils ON/OFF chargés par défaut par l'application |
| `config/manual_capture_profiles.json` | Profils distincts pour l'essai supervisé manuel |
| `tools/pair_once.py` | Un seul ON après saisie `ENVOYER`, journal et contrôle du retour RX |
| `tools/monitor_serial.py`, `tools/record_serial.py` | Suivi des trames et enregistrement série |
| `tools/scan_garage.py` | Exploration RX 868 MHz ; retour au profil MCZ à vérifier |
| `tools/analyze_mcz_capture.py`, `tools/compare_frames.py` | Analyse hors ligne Python |
| `tools/decode_capture.cpp` | Lecteur de captures utilisant le décodeur C++ |
| `tools/preview_app.py` | Simulation de l'interface sans ouverture USB |
| `tests/`, `tools/check_native.sh` | Suites Python et C++ natives hors matériel |
| `captures/`, `docs/` | Journaux originaux, analyses et preuves datées |
| `research/` | Copies locales ignorées de projets étudiés, potentiellement absentes |

## Contrat HTTP

Serveur par défaut : `http://127.0.0.1:8765`, bibliothèque standard Python.

- `GET /`, `/style.css`, `/app.js` : ressources explicitement autorisées.
- `GET /api/status` : statut USB et jeton de l'instance ; aucun envoi RF.
- `POST /api/command` : JSON contenant exactement `action` (`on` ou `off`) et
  `id` (32 caractères hexadécimaux minuscules). Corps limité à 256 octets.
  Host et Origin locaux attendus, jeton `X-MCZ-Token` obligatoire.

Le jeton est généré au démarrage ; ce mécanisme protège la commande locale
contre des appels depuis une autre origine, sans constituer une authentification
multi-utilisateur. L'application n'est pas conçue comme un service public.

## Contrat USB et concurrence

`j` demande un statut JSON préfixé `APP `. `s` demande un diagnostic lisible.
La commande TX est `!TX <id_requete_32_hex> <trame_14_hex>` suivie d'un LF.
L'identifiant USB est distinct de l'identifiant radio sur trois octets.

Les réponses `APP` ont un type `status` (`ready`, `frequency`, `tx_count`) ou
`result` (`id`, `result`). Les résultats reconnus sont `sent`, `uncertain`,
`busy`, `unavailable` et `rejected`. `sent` correspond à une transmission RMT
achevée et un retour RX réussi selon le firmware, sans mesure RF indépendante.

Le bridge réserve l'identifiant avant écriture, interdit les commandes
concurrentes et applique un délai de trois secondes. Il attend jusqu'à quatre
secondes pour la réponse ; le statut devient périmé après cinq secondes.
La reconnexion ne rejoue pas les commandes. Le firmware garde 16 identifiants,
le bridge jusqu'à 512 résultats ; ces mémoires sont volatiles et bornées.
Le firmware applique aussi un délai de deux secondes entre transmissions.

## Protocole radio et capture

ASK/OOK à 434,50 MHz ; sept octets dont trois d'identifiant et deux de CRC.
CRC16 XMODEM : polynôme `0x1021`, initialisation `0`, sur les cinq premiers
octets, résultat transmis poids fort d'abord. L'encodeur TX limite l'ID à `C8CC02`.

Manchester, mots de 12 bits avec parité et marqueur de premier octet ; demi-bit
nominal 414 µs, préfixe HIGH 103000 µs, séparateur LOW 414 / HIGH 828 µs avant
chaque octet, pause LOW 3712 µs et cinq répétitions. Consulter le
[rapport de protocole](../FONCTIONNEMENT_TRAMES_MCZ.md) avant de toucher aux bits.

RMT utilise GDO0/GPIO27 et une résolution de 1 µs ; le même chemin est basculé
entre RX et TX. Notre CC1101 ne peut pas témoigner de sa propre émission en RX
simultané. La fin de bloc RX à 3000 µs produit une borne `idle_tail_min_us`,
pas une mesure exacte de la pause. Le filtre de 255 cycles APB vaut environ
3,19 µs, pas 255 µs. Ne pas mélanger captures historiques GPIO et captures RMT.

## Points de défaillance et observation

Une page accessible ne garantit pas USB prêt ; USB prêt ne qualifie pas TX RF.
Consulter `connected`, `busy`, `last`, `tx_count` et les journaux série.
Le compteur repart à zéro au redémarrage et ne prouve aucune action physique.
Une panne SPI, un bloc RMT perdu ou un échec de retour RX doit rester visible,
sans tentative automatique d'une nouvelle commande. La qualification finale
requiert une mesure RF indépendante et/ou une observation explicite du poêle.
