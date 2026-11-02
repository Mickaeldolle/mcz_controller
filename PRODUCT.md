# Commande locale MCZ Musa
<!-- impeccable:product-schema 1 -->
## Platform
web
## Users
Propriétaire du poêle, sur son PC Windows.
## Product Purpose
Deux boutons Allumer / Éteindre, sur une page locale du PC, ESP32 branché en USB : choix confirmé par l'utilisateur.
## Operating Context
ESP32 + CC1101 E07-M1101D, 434,50 MHz ; aucune connexion cloud.
## Capabilities and Constraints
Rejouer les commandes réellement capturées, sans inventer de réglages. Aucun envoi au démarrage ou à la reconnexion. L'état du poêle demeure inconnu sans retour du poêle.
## Evidence on Hand
captures/20261030-124843_buttons.log : cinq trames Mode=3 puis cinq Mode=0, ID C8CC02, CRC valide.
## Product Principles
Simplicité, commande explicite, absence de répétition automatique, retour honnête sur les limites.
