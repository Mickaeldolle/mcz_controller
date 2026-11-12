---
version: alpha
name: "MCZ Musa local"
description: "Une commande domestique simple, papier chaud et terre cuite."
colors:
  background: "#f3f1ec"
  surface: "#fffdf9"
  ink: "#272d30"
  muted: "#61666a"
  line: "#d4d2cd"
  ember: "#984323"
  ember-hover: "#7d351c"
  focus: "#1e607c"
  success: "#286242"
typography:
  sans:
    fontFamily: '"Segoe UI", system-ui, sans-serif'
rounded:
  DEFAULT: "12px"
spacing:
  page-max: "640px"
components:
  button: {}
---
# MCZ Musa Design System
## Overview
### Creative North Star
Un interrupteur domestique lisible posé sur une surface de papier chaud.
### Product context and register
Usage sur téléphone ou PC à domicile, lumière ambiante variable. Interface de produit en français, deux actions sans navigation. Aucun marché commercial supposé. La terre cuite distingue Allumer et le texte reste prioritaire.
Tokens : app/web/style.css est la source d'exécution ; les valeurs ci-dessus la reflètent. Modifier les deux ensemble. API propriétaire des commandes, firmware propriétaire de la validation radio ; aucun état réel du poêle déduit d'un clic.
## Colors
Fond background, texte ink, texte secondaire muted. Ember pour Allumer, surface pour Éteindre, focus bleu. Success indique la connexion à l’ESP32. Pas de thème sombre.
## Typography
Segoe UI locale, repli système. Corps 15px, titre 36–48px, actions 22px. Aucun téléchargement de police.
## Layout
Colonne de 640px maximum. Les curseurs précèdent les deux boutons. Sous 420px, les curseurs s’empilent et les boutons restent côte à côte. Le retour d’envoi garde son espace sous les actions.
## Elevation & Depth
Séparation par traits ; aucune ombre ou superposition.
## Shapes
Boutons de rayon 12px ; aucun conteneur imbriqué.
## Components
### Foundational visual states
Chargement initial désactivé ; connexion, déconnexion, attente, résultat et erreur dans un retour aria-live stable. Le message d'envoi ne change jamais l'état du poêle.
### Buttons and actions
Boutons natifs, clic ou Entrée/Espace. Focus visible, survol, pression et indisponibilité. Désactivation pendant l'envoi et trois secondes de délai. Pas de nouvelle tentative automatique.
### Navigation and data display
Une seule page, sans menu ni tableau.
Les mesures ambiantes du DHT11 s’affichent sur deux colonnes avant les réglages.
Elles sont masquées sur un firmware sans capteur et indiquent « Indisponible »
pour chaque valeur manquante, sans décaler les commandes lors d’une interruption.
### Forms and overlays
Trois curseurs natifs à pas entier, chacun avec un libellé et la valeur choisie. Le curseur du ventilateur 2 apparaît quand le catalogue contient ses réglages. Son premier cran conserve le profil d’origine, suivi de l’arrêt (0), des niveaux 1 à 5 et d’Auto (6). Le texte sous les contrôles indique les combinaisons disponibles. Allumer / appliquer envoie le réglage choisi. Éteindre reste indépendant des réglages.
La page de test Wi-Fi ouvre directement la commande. Le même composant de retour décrit l’envoi dans les deux modes.
### Iconography
Deux SVG géométriques, traits de 2 unités ; libellés toujours visibles.
### Motion
Changement de couleur 120ms ; désactivé avec reduced-motion.
### Content and data visualization
Français direct. « Envoyée » signifie émission, pas réception. Aucun graphique.
## Do's and Don'ts
- Garder les deux actions immédiatement accessibles.
- Toujours distinguer connexion à l’ESP32 et état du poêle.
- Indiquer les combinaisons de flamme et de ventilation disponibles dans la table de commandes.
- Ne jamais afficher « poêle allumé » sans mesure indépendante.
