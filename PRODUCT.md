# Commande locale MCZ Musa
<!-- impeccable:product-schema 1 -->
## Platform
web
## Users
Propriétaire du poêle, sur son téléphone ou son PC.
## Product Purpose
Allumer, régler la flamme et les ventilateurs, ou éteindre depuis la page de l’ESP32 sur le Wi-Fi domestique ou depuis le PC relié en USB.
## Operating Context
ESP32 + CC1101 E07-M1101D à 434,50 MHz. Page PC via USB et API authentifiée sur le Wi-Fi local.
## Capabilities and Constraints
Rejouer les commandes capturées et calculer les combinaisons manuelles à partir des champs vérifiés. La flamme va de 1 à 5, le ventilateur 1 de 1 à 6 et le ventilateur 2 de 0 à 6. La valeur 6 correspond à Auto. La combinaison choisie doit figurer dans la table du firmware pour être envoyée. Un changement de réglage prépare la commande. L'envoi exige un clic explicite et l'état réel du poêle demeure inconnu.
## Evidence on Hand
captures/20261109-205625-968354_live.log : 22 gestes, dont l’arrêt et dix réglages manuels distincts, catalogués localement.
captures/20261110-065656-157595_live.log : 11 gestes et sept réglages distincts du ventilateur 2 à flamme 3 et ventilateur 1 au niveau 5.
## Product Principles
Simplicité, commande explicite, absence de répétition automatique, retour honnête sur les limites.
