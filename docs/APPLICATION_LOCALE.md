# Application locale USB

La page tourne sur le PC à `http://127.0.0.1:8765`. Le serveur Python
est le propriétaire exclusif de COM3 pendant son fonctionnement. Il lit
le catalogue, vérifie la capture et attend le statut USB. Le firmware bascule
en émission lorsqu’il reçoit une commande valide, puis remet la radio au
repos.

## Utilisation

1. Branche l’ESP32 avec son CC1101 et son antenne, puis lance `Demarrer-MCZ.cmd`.
2. Attends **ESP32 connecté**. Le poêle doit être prêt à recevoir ses commandes
   distantes.
3. Choisis la puissance et la ventilation, puis clique **Allumer / appliquer**.
   Si la combinaison manque, le bouton est désactivé. **Éteindre** envoie la
   trame d’arrêt du catalogue, quels que soient les curseurs.
   Pour régler le ventilateur 2, déplace son curseur sur l’arrêt (0),
   un niveau de 1 à 5 ou Auto (6). Avec un niveau explicite, l’application
   peut combiner les trois réglages. Pour utiliser les profils calculés en
   USB, téléverse la version du firmware qui contient la même table.
4. Observe l’afficheur ou le comportement du poêle. Respecte son cycle normal
   d’arrêt et de refroidissement.

Le PC doit rester en marche pour la page USB. Pour utiliser l’API Wi-Fi,
l’ESP32 peut fonctionner indépendamment du serveur Python. Si tu ouvres le
port pour configurer le Wi-Fi ou téléverser le firmware, arrête d’abord le
serveur avec Ctrl+C dans sa console si elle est ouverte.

## Essai sur le poêle — 9 novembre 2026

Le propriétaire a confirmé l’allumage puis l’extinction avec les deux boutons
de la page. Le statut de l’application sur COM3 indiquait un compteur TX
passé de 0 à 2 et un dernier résultat OFF `sent`. Le catalogue provenait de
la [capture du 9 novembre](../captures/20261109-205625-968354_live.log).

Cet essai a précédé l’ajout de l’API Wi-Fi. L’observation établit le
fonctionnement des deux commandes jouées sur le poêle. La réaction aux
autres réglages et la mise en service du nouveau firmware restent à vérifier
sur le matériel.

## Protections et dépannage

Le serveur écoute uniquement sur la boucle locale. Il contrôle Host,
Origin et le jeton de l’instance avant tout POST. Il sérialise les écritures
USB et attend au plus quatre secondes pour le résultat. L’application
affiche une émission non confirmée après un délai ou une coupure, sans
relancer la commande.

Si la page reste déconnectée, vérifie le port et ferme les autres
applications série. Si la liaison est prête mais que l’envoi est incertain,
observe le poêle avant toute nouvelle commande. L’état du poêle ne change
dans l’interface qu’avec une mesure réelle, absente de ce montage.
