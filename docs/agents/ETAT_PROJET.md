# État du projet

Le 9 novembre 2026, le propriétaire a confirmé l’allumage et l’extinction
du poêle avec les boutons de la page locale. Le compteur TX est passé
de 0 à 2, avec OFF `sent` en dernier résultat.
[Compte rendu](../APPLICATION_LOCALE.md#essai-sur-le-poêle--9-novembre-2026)

La [capture d’origine](../../captures/20261109-205625-968354_live.log)
et la [capture du ventilateur 2](../../captures/20261110-065656-157595_live.log)
sont les références du [catalogue](../../config/catalogue_mcz.csv).
La deuxième capture ajoute sept réglages du ventilateur 2, de l’arrêt
(0) à Auto (6), avec flamme 3 et ventilateur 1 au niveau 5. Leur rejeu
par l’ESP32 reste à vérifier sur le poêle.

Le firmware conserve le contrat USB et sert une page autonome sur le même
port que l’[API Wi-Fi v1](../API.md). Cette API est aussi le contrat
prévu pour la future application Kotlin.

Vérification du refactor le 9 novembre 2026 : compilation PlatformIO
réussie (48 960 octets de RAM statique et 795 089 octets de flash), 15 tests
Python et quatre suites C++ avec sanitizers réussis. Le serveur PC relancé
voit la carte sur COM3, avec onze profils et un compteur TX à zéro.

Le 10 novembre 2026, le firmware d’émission avec la page embarquée a
été téléversé sur COM3 après sauvegarde locale de la zone réécrite.
Le statut USB au démarrage indiquait `ready: true`,
`frequency: 434500000` et `tx_count: 0`. Après la configuration Wi-Fi,
la page et ses fichiers ont été servis par la carte. Le GET authentifié
a confirmé les 18 profils et un compteur TX à zéro. Les essais HTTP
ont confirmé le refus d’une clé absente ou incorrecte et d’un hôte ou
d’une origine étrangers.

La variante de test sans formulaire a ensuite été téléversée sur COM3.
Dans Chrome, la page s’est connectée au chargement et après
rechargement. Le GET authentifié a confirmé les 18 profils et un
compteur TX à zéro. Le HTML fournit la clé aux appareils qui peuvent
ouvrir la page sur le réseau local.

Une incompatibilité des commandes HTTP a été reproduite dans Firefox.
Avec `Referrer-Policy: no-referrer`, le POST du navigateur recevait
`403 invalid_origin`.
La carte a été mise à jour avec `Referrer-Policy: same-origin`. Une
requête Firefox portant un profil inexistant atteint maintenant la
validation du catalogue et reçoit `422`. Les origines étrangères
restent refusées et le compteur TX est resté à zéro pendant ces essais.
Après rechargement de la page sur le téléphone, le propriétaire a
confirmé une commande envoyée et une réaction du poêle. Le compteur
TX est passé de zéro à un.

Le générateur de profils manuels a ensuite été ajouté. Il reconstruit
les trames manuelles capturées, puis calcule les 210 combinaisons avec
un réglage explicite du ventilateur 2. La table comporte 221 profils
au total. La compilation, les 16 tests Python, les suites natives et
un essai de sélection dans Chrome avec API simulée ont réussi.
Cette version a été téléversée sur COM3. Après redémarrage, l’API Wi-Fi
a renvoyé les 221 profils et Chrome a confirmé la sélection des profils
`1:1:2` et `2:4:3`. Le compteur TX est resté à zéro. L’essai sur le
poêle d’une combinaison calculée reste à effectuer.

La compilation, les 15 tests Python de commande, les six tests du
moniteur de réception et les quatre suites C++ ont réussi. La page
Wi-Fi a été testée dans Chrome à 360 px de large avec une API simulée.
Le [guide de développement](../GUIDE_DEVELOPPEMENT.md#6-vérifier-lapi-wi-fi)
décrit la procédure de vérification sur le Wi-Fi réel.
