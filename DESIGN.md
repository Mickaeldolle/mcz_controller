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
Usage sur PC à domicile, lumière ambiante variable. Interface de produit en français, deux actions sans navigation. Aucun marché commercial supposé. La terre cuite distingue Allumer ; le texte reste prioritaire.
Tokens : app/web/style.css est la source d'exécution ; les valeurs ci-dessus la reflètent. Modifier les deux ensemble. API propriétaire des commandes, firmware propriétaire de la validation radio ; aucun état réel du poêle déduit d'un clic.
## Colors
Fond background, texte ink, texte secondaire muted. Ember pour Allumer, surface pour Éteindre, focus bleu. Success indique seulement la connexion USB. Pas de thème sombre.
## Typography
Segoe UI locale, repli système. Corps 15px, titre 36–48px, actions 22px. Aucun téléchargement de police.
## Layout
Colonne de 640px maximum. Deux boutons en grille, marge réduite sous 420px. Retour d'envoi sous les actions avec espace réservé.
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
### Forms and overlays
Aucun formulaire ni dialogue ; erreurs dans la page.
### Iconography
Deux SVG géométriques, traits de 2 unités ; libellés toujours visibles.
### Motion
Changement de couleur 120ms ; désactivé avec reduced-motion.
### Content and data visualization
Français direct. « Envoyée » signifie émission, pas réception. Aucun graphique.
## Do's and Don'ts
- Garder les deux actions immédiatement accessibles.
- Toujours distinguer connexion USB et état du poêle.
- Ne pas ajouter de réglages de température ou de ventilation.
- Ne jamais afficher « poêle allumé » sans mesure indépendante.
