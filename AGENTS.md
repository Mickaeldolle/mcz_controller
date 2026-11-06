# Guide des agents de code — MCZ Musa

Ce fichier est le point d'entrée des agents qui interviennent dans ce dépôt.
Lire aussi [AGENT.md](AGENT.md) si votre outil utilise ce nom : il renvoie ici.
Les instructions explicites de l'utilisateur priment sur ce guide.

## Comprendre le projet

POC de commande locale d'un poêle MCZ Musa Comfort Air : page web sur un PC
Windows, serveur Python, liaison USB vers un ESP32 classique, radio CC1101
E07-M1101D à 434,50 MHz. Deux actions : Allumer et Éteindre. Pas de Wi-Fi,
de cloud, de base de données ou de gestionnaire JavaScript nécessaire.

La réception des trames d'origine et le chemin logiciel TX sont documentés.
La réception par le poêle, l'association et l'action physique ne sont pas
qualifiées de bout en bout. Ne pas annoncer un contrôle du poêle opérationnel
sur la seule base de la compilation, d'un test ou d'un résultat USB `sent`.

## Parcours de lecture

1. [État et preuves](docs/agents/ETAT_PROJET.md) : acquis, limites et suite utile.
2. [Architecture](docs/agents/ARCHITECTURE.md) : composants et contrats.
3. [Développement et validation](docs/agents/DEVELOPPEMENT.md) : commandes et risques.
4. [README](README.md) : installation, matériel et utilisation.
5. [Produit](PRODUCT.md) et [design](DESIGN.md) avant toute évolution de l'interface.

Selon le travail, compléter avec le [format des trames](docs/FONCTIONNEMENT_TRAMES_MCZ.md),
les [blocages](docs/BLOCAGES_ALLUMAGE_EXTINCTION.md), le
[dernier essai terrain formellement décrit](docs/ESSAI_TX_20261102_APPARIAGE.md)
et le [guide de mise en service](docs/MISE_EN_SERVICE_ALLUMAGE_EXTINCTION.md).
Les rapports sont datés : les confronter au code, aux profils et aux journaux présents.

## Avant de modifier

- Répondre en français, avec des faits, hypothèses et limites explicites.
- Examiner `git status --short` et `git diff` ; préserver les travaux déjà présents,
  y compris les fichiers non suivis. Ne pas réinitialiser ni nettoyer le dépôt.
- Chercher avec `rg` en excluant `.git/`, `.venv/`, `.pio/`, `.platformio/` et
  `research/` sauf besoin précis ; ce sont surtout des dépendances ou références.
- Identifier la couche concernée et faire le plus petit changement cohérent.
- Ne pas lancer serveur USB, moniteur, capture, flash ou essai radio pour une simple
  modification documentaire ou un contrôle logiciel hors matériel.

## Invariants à préserver

- Aucun envoi RF au démarrage, à l'ouverture de page ou à la reconnexion USB.
- Une action explicite produit une commande contenant les cinq répétitions du
  protocole. Ne pas les confondre avec cinq tentatives applicatives.
- Aucun renvoi automatique après délai dépassé, déconnexion ou résultat `uncertain`.
  Une absence de confirmation ne prouve pas que la commande n'a pas été émise.
- Garder les identifiants de requête, l'anti-doublon, le verrou de commande et
  les délais entre commandes. Les historiques sont bornés et non persistants :
  ce n'est pas une garantie d'exécution unique après redémarrage.
- Garder le serveur sur `127.0.0.1`, les contrôles Host/Origin et le jeton de
  requête. Ne pas ouvrir le service sur le réseau pour contourner un test.
- Le CRC vérifie l'intégrité du format ; il n'authentifie pas l'émetteur.
- Le TX reste limité à l'identifiant capturé `C8CC02`. Ne pas inventer de
  trames, de réglages ou de commande spéciale d'appairage.
- Ne pas remplacer les profils actifs par les profils manuels comme effet
  secondaire. Tout changement doit conserver la provenance et adapter ses tests.
- L'interface distingue connexion USB, commande envoyée et état réel inconnu
  du poêle. Garder deux actions simples, accessibles, en français.

## Matériel et essais réels

- CC1101 en 3,3 V uniquement. Aucun raccordement au câblage interne du poêle.
- Brochage : SCK=18, MISO=19, MOSI=23, CS=5, GDO0=27 ; source :
  `include/radio_config.h`. Ne pas transposer à une autre famille ESP32 sans étude.
- `MCZ_WIRING_CONFIRMED=1` est activé dans `platformio.ini` pour le montage
  confirmé ; cela ne qualifie pas un nouveau montage.
- Un seul propriétaire du port série, actuellement COM3 par défaut, à 115200 bauds.
  Son ouverture peut redémarrer la carte ; ne pas interrompre un outil existant
  sans comprendre son activité.
- Un flash remplace le firmware. Une émission ON peut réellement allumer le
  poêle. Ne réaliser ces opérations que dans le périmètre demandé, avec un
  opérateur pour les essais physiques ; lire le guide de mise en service.
- Ne pas augmenter la puissance RF ou répéter les essais au hasard. Comparer
  notre TX avec la télécommande à l'aide d'un récepteur indépendant avant
  d'attribuer l'échec à la radio ou au récepteur du poêle.
- Ne jamais utiliser une coupure électrique comme arrêt normal du poêle :
  préserver son cycle de refroidissement et ses sécurités.

## Fin de travail

- Exécuter les vérifications adaptées dans le [guide de développement](docs/agents/DEVELOPPEMENT.md).
  Une documentation seule exige surtout la vérification des liens et des faits.
- Rapporter les commandes réellement exécutées, leurs résultats, les tests
  ignorés et les limites. Ne pas convertir un ancien rapport en validation actuelle.
- Séparer preuves statiques, tests logiciels, USB, mesure RF et observation du poêle.
- Conserver les captures originales ; aucune fixture synthétique dans `captures/`.
  Ne pas publier captures et identifiants locaux sans instruction explicite.
- Mettre à jour les documents affectés si un contrat ou un résultat change.
  Utiliser le [modèle de passation](docs/agents/PASSATION.md) si la tâche continue.
- Ne pas committer, pousser ou publier automatiquement pour une demande de fichiers.
