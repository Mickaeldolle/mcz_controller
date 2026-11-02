# Rapport RX réel — MCZ Musa Comfort Air — 30 octobre 2026

## Résultat

**Réception et structure des trames confirmées sur la télécommande testée.**
35 trames réelles validées, regroupées en **7 séries de 5 répétitions**.
Les 35 captures d'impulsions ont été redécodées hors ligne avec le décodeur C++.
Les CRC des octets affichés ont aussi été vérifiés indépendamment avec
`binascii.crc_hqx` de Python. Les trois vérifications concordent.

Journal de preuve : `captures/20261030-123642_buttons.log`.
Consigne utilisateur : ventilation +/− ; télécommande à 30–50 cm.
Poêle précédemment déclaré éteint, sélecteur **REMOTE confirmé par l'utilisateur**.
Aucune émission ESP32, aucun rejeu, aucun nouvel appairage effectué.

## Paramètres observés

| Champ | Observation |
|---|---|
| Identifiant 24 bits | `C8CC02`, stable sur les 35 trames |
| Mode brut | `3`, interprété ECO par les sources ; affichage AUTO déclaré par l'utilisateur à recouper avec l'icône ECO |
| Puissance | `3`, stable |
| Ventilation 1 | `2 → 3 → 4 → 5 → 6 → 5 → 4` ; `6` correspond à AUTO dans les sources |
| Ventilation 2 | `7`, stable ; valeur observée, sens exact non confirmé sur cet appareil |
| User | `2`, stable, signification fonctionnelle non établie |
| Bits réservés | `0` |
| CRC | XMODEM, initial 0, polynôme 0x1021, MSB/LSB ; **35/35 valides** |

## Trames distinctes

| Fan1 | Octets réels | Nombre reçu |
|---:|---|---:|
| 2 | `C8 CC 02 4F B8 98 42` | 5 |
| 3 | `C8 CC 02 6F B8 9E A4` | 5 |
| 4 | `C8 CC 02 8F B8 8E 16` | 10 |
| 5 | `C8 CC 02 AF B8 88 F0` | 10 |
| 6 | `C8 CC 02 CF B8 83 DA` | 5 |

Les ventilations 4 et 5 ont été traversées à la montée puis à la descente.
Seul le champ fan1 de l'octet 3 varie dans cet essai, avec les deux octets de
CRC recalculés. Aucune température de consigne n'a été identifiée dans la trame.

## Acquisition

ESP32-D0WD-V3, E07-M1101D, GDO0 sur GPIO27, réception ASK/OOK à 434,50 MHz,
bande nominale 101,6 kHz. Fréquence configurée, pas mesurée par instrument RF.
RMT RX à résolution 1 µs, filtre matériel environ 3,19 µs, pause limite 3 ms.
La dernière pause exportée est une borne minimale de 3000 µs, pas une mesure
exacte ; elle représente la fin de niveau omise par le pilote, sans modifier
les bits utiles ni les octets de CRC.

35 blocs bruts exportés ; aucun niveau adjacent de même signe dans ces blocs.
1978 blocs RMT traités pendant l'essai ; aucun bloc rejeté par le contrôle local,
aucune erreur SPI ni erreur pilote RMT retrouvée dans le journal.
Le préfixe de commande long n'est pas conservé par ce mode RMT ; il avait été
mesuré autour de 102 ms lors des captures GPIO précédentes.

## Comparaison aux références

La longueur 7 octets, les mots 12 bits, start/stop, le drapeau de premier octet,
la parité, les séparateurs Manchester et le CRC décrits par KerberRF et repris
par sfauvart/mylifeos permettent de décoder ces captures réelles sans correction
des bits. Les cinq répétitions correspondent également aux références.

Deux points restent à interpréter : fan2=7 et mode=3 alors que l'utilisateur
indique AUTO. Ne pas remplacer ces valeurs ni en déduire une panne.
Le [manuel MCZ §5.6.1](https://solarnet-online.com/wp-content/uploads/2017/03/Musa-comfort-air-Manual.pdf)
décrit une configuration de télécommande pour 1 ou 2 ventilateurs ; vérifier
cette configuration est une piste, pas la preuve que fan2=7 signifie « absent ».

## Conclusion et suite

Le **niveau 2 du POC RX est atteint pour la structure, l'ID et la ventilation 1**.
La panne totale d'émission de la télécommande est écartée pour cet essai.
La réception par le poêle, son association et la correspondance de ses réglages
ne sont pas prouvées par cette capture ESP32. Fan2 et commandes ON/OFF réelles
restent à qualifier séparément.

Le succès suit plusieurs changements et une autre commande de test : RMT,
bande élargie et ventilation. Il ne prouve pas que le remplacement de l'ISR
GPIO par RMT explique à lui seul les échecs précédents.

**TX reste non implémenté.** Avant une éventuelle émission : validation explicite
de la phase RX par l'utilisateur et choix d'un essai adapté à l'état du poêle.
Ne pas réappairer ni modifier la configuration de ventilation avant d'avoir
relevé son état actuel et décidé du prochain diagnostic.
