# Capture ON/OFF prolongé — 2 novembre 2026

L'utilisateur a été invité à maintenir ON/OFF pendant deux secondes, puis a
confirmé « fait ». Il a ensuite précisé avoir effectué un seul appui, avec le poêle hors mode
d'appairage. Cette confirmation permet d'attribuer le second groupe à une
émission sans nouvel appui ; sa fonction exacte reste inconnue.

## Résultats observés

Deux groupes distincts, espacés d'environ 59,6 secondes, ont été reçus.
Chaque groupe comporte cinq trames CRC valides. Le décodeur du firmware et
le décodeur Python indépendant retrouvent les mêmes dix trames, sans
correction des impulsions brutes.

| Groupe | Temps ESP32 des blocs | Trame répétée cinq fois | Interprétation des champs |
|---|---|---|---|
| 1 | 53,499 à 53,829 s | C8 CC 02 8F B8 8E 16 | Identique au profil Allumer enregistré : mode 3, puissance 3, fan1=4, fan2=7, bits user=2, réservé=0 |
| 2 | 113,087 à 113,426 s | C8 CC 02 8B 38 D3 5A | Même ID et mode ; puissance 2, bits user=0 ; autres champs identiques |

L'ID C8CC02 est identique pour les deux groupes. Le nom historique « user »
ne constitue pas une explication validée de la fonction des deux bits concernés.
La seconde trame ne doit pas être assimilée à une commande d'appairage sur la
seule base de cette différence. Une émission automatique est cohérente avec la confirmation d'un seul appui.
Sa périodicité et son rôle exact ne sont pas établis par cette capture.

Aucune émission continue pendant deux secondes n'a été établie. Les durées
ci-dessus sont les horodatages de traitement des blocs reçus, pas une mesure
précise de la durée d'appui ni du début de l'émission radio.

## Qualité et limites

- Deux détections fortes : RSSI estimés -47,5 puis -64,5 dBm.
- Dernier diagnostic : RX STATE=0D, dropped=0, spi_errors=0, VALID=10.
- 1651 blocs bruts complets conservés ; le dernier bloc, interrompu lors de
  l'arrêt de l'enregistrement, est incomplet et exclu de l'analyse.
- Les fenêtres autour des deux événements sont complètes dans l'extrait.
- Les blocs de moins de 20 impulsions peuvent ne pas être exportés ; le
  périphérique RX coupe les pauses longues et la pause finale est une borne
  minimale de 3000 microsecondes. Une absence de trame spéciale décodée ne
  démontre donc pas l'absence absolue de tout autre signal.
- L'enregistrement est arrêté. Après réouverture USB et redémarrage de la
  carte, retour RX confirmé : ready=true, fréquence 434500000 Hz, TX=0,
  diagnostics et capture déclenchée désactivés. Aucune commande ESP32 !TX envoyée.

## Fichiers

- Source non modifiée : ../captures/20261102-211909_buttons.log
- Extrait de blocs complets : ../captures/20261102-211909_longpress_excerpt.log
- Analyse détaillée et variantes de décodage : appui-long-20261102.json

## Conclusion

Le premier groupe reproduit exactement le profil Allumer existant. Un second
message différent a été reçu environ une minute plus tard. Ce test n'identifie
pas de commande d'appairage spécifique : l'appui long a été effectué hors mode
d'appairage. Le second groupe est cohérent avec une émission automatique sans
nouvel appui. La réaction du poêle et l'apprentissage de l'identifiant pendant
un véritable essai en mode « --- » restent à vérifier. Aucun profil d'émission
n'a été modifié.
