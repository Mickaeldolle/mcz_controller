# État du projet pour une reprise

Relevé documentaire du **6 novembre 2026** à partir des fichiers locaux.
Aucun contrôle du matériel actuellement branché n'est impliqué par ce relevé.
Retour au [guide des agents](../../AGENTS.md).

## Ce qui est établi et ce qui reste à qualifier

| Sujet | Preuve locale | Limite |
|---|---|---|
| Télécommande d'origine reçue par ESP32 | Captures réelles et rapports RX, ID `C8CC02`, CRC valides | Ne prouve pas sa réception par le poêle |
| Application et firmware RX/TX | Sources, tests et essais USB consignés | Version installée actuellement non inspectée pour cette documentation |
| Essai du 2 novembre | Rapport : `sent`, TX 0→1, retour RX ; utilisateur : `---` maintenu sans bip | Appairage non confirmé ; aucune mesure RF indépendante |
| Journaux des 3 et 4 novembre | D'autres `sent` et retours RX sont présents, ainsi que des abandons et une annulation | Aucune observation physique nouvelle ne peut être déduite de ces lignes |
| Commande locale du poêle | Utilisateur : démarrage avec sélecteur ON | Ne valide pas la chaîne distante en REMOTE |
| Réaction distante / association | Échec documenté avec télécommande d'origine et essai ESP32 | Cause non isolée ; ne pas diagnostiquer un récepteur défectueux par défaut |

Références principales : [rapport RX](../RAPPORT_RX_VALIDE.md),
[blocages](../BLOCAGES_ALLUMAGE_EXTINCTION.md),
[essai décrit du 2 novembre](../ESSAI_TX_20261102_APPARIAGE.md).
Les [validations historiques](../VALIDATION.md) contiennent aussi des étapes
antérieures au TX ; ne pas interpréter leurs anciens statuts comme l'état actuel.

Journaux plus récents consultés :

- [3 novembre, envoi](../../captures/20261103-111115-521516_pairing.log).
- [4 novembre, annulation](../../captures/20261104-184648-062038_pairing.log).
- [4 novembre, envoi](../../captures/20261104-184745-024287_pairing.log).

Un journal USB ne contient pas nécessairement les bips ou la réaction observée
par la personne. Ne pas généraliser le résultat terrain du 2 novembre aux autres
dates. Plusieurs fichiers de ces essais ne sont pas encore suivis par Git au
moment du relevé ; vérifier leur présence avant une reprise depuis un clone.

## Profils en place

| Usage | Source de configuration | ON | OFF |
|---|---|---|---|
| Application par défaut | `config/power_profiles.json` | `C8CC028FB88E16` | `C8CC028CB8DB45` |
| Essai manuel distinct | `config/manual_capture_profiles.json` | `C8CC0245B87789` | `C8CC0244B844B8` |

Provenance active : [capture du 30 octobre](../../captures/20261030-124843_buttons.log).
Provenance manuelle : [capture du 2 novembre](../../captures/20261102-215528-553832_live.log).
Les réglages ON diffèrent : mode 3 / puissance 3 / ventilation 1 à 4 pour
l'application ; mode 1 / puissance 1 / ventilation 1 à 2 pour l'essai manuel.
Le champ ventilation 2 à 7 reste inexpliqué ; préserver la trame capturée.
Le fichier manuel ne remplace pas automatiquement les profils du serveur.

## Prochaine étape utile

La priorité technique documentée est de qualifier notre émission avec un
récepteur indépendant ou SDR capable de recevoir aussi la télécommande.
Comparer fréquence, octets, polarité, répétitions et durées. Un analyseur
logique sur GPIO27 peut qualifier la sortie numérique, mais pas l'onde RF.
Recouper aussi la procédure d'apprentissage de la génération exacte du poêle.

Si aucune mesure indépendante n'est disponible, poursuivre l'analyse hors
ligne et documenter la limite. Ne pas inventer une trame d'appairage ni migrer
vers ESPHome/Home Assistant pour masquer ce manque de preuve.

## Actualiser cet état

Ajouter la date, le contexte, le journal et l'observation physique explicite.
Séparer résultat logiciel, résultat USB, mesure RF et résultat poêle. Un nouveau
`sent` seul ne lève pas le blocage d'appairage. Ne pas écraser les rapports
historiques ni déclarer tous les tests réussis à partir d'un bilan ancien.

## Vérifications de cette documentation — 6 novembre 2026

- Huit documents créés ou actualisés : lecture UTF-8, blocs de code et 43 liens
  locaux vérifiés ; `git diff --check` sans erreur d'espacement.
- Suite Python : 31 tests recensés, 29 réussis, 1 ignoré faute de `MCZ_DECODER`,
  1 en erreur (`test_reject_foreign_origin_host_and_bad_input`) avec
  `ConnectionAbortedError: WinError 10053`. La relance ciblée des 13 tests
  d'application confirme 12 réussites et la même erreur HTTP. Cause non isolée.
  La première exécution en environnement restreint avait aussi rencontré
  `WinError 10013` sur les trois tests HTTP ; une exécution autorisée pour les
  connexions locales a levé ces refus, mais pas l'interruption 10053.
- `python -m platformio run` via le Python du projet : succès, RAM 26520 octets,
  flash 300041 octets. Une première exécution restreinte avait échoué à
  `checkprogsize` avec une erreur de repositionnement de DLL Windows ; la
  relance autorisée à exécuter les outils locaux a réussi, sans changement du code.
- Suites C++ natives non relancées pour cette tâche documentaire. Aucun port
  série ouvert, aucune carte flashée et aucune émission RF effectuée.

La suite Python complète n'est donc pas verte dans cette session. Ne pas
affaiblir les contrôles Host/Origin pour contourner l'interruption HTTP.
