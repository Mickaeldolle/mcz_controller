# Fonctionnement du MCZ Musa

## Matériel

ESP32 classique (`esp32dev`), CC1101 E07-M1101D avec antenne 433 MHz et
liaison USB au PC si utilisée. Alimente le module en **3,3 V** et partage
la masse avec l’ESP32. Le montage communique par radio avec le poêle.

| Signal | GPIO ESP32 |
|---|---:|
| SCK | 18 |
| MISO | 19 |
| MOSI | 23 |
| CS | 5 |
| GDO0 | 27 |

Le firmware configure le CC1101 par SPI et désactive la sortie de GDO0
avant que le RMT de l’ESP32 pilote cette ligne. En émission asynchrone,
le CC1101 lit les niveaux sur GDO0. Entre les commandes, le CC1101
reste au repos (`IDLE`) et le RMT maintient GPIO27 au niveau bas.
Une panne SPI ou RMT pendant un envoi rend l’émetteur indisponible
jusqu’au redémarrage.

## Fréquences et temps

| Liaison | Paramètre |
|---|---|
| ESP32 ↔ routeur | Wi-Fi **2,4 GHz**, mode station, WPA2-PSK minimum |
| CC1101 ↔ poêle | Porteuse nominale **434,50 MHz**, modulation **ASK/OOK** |
| Quartz supposé du CC1101 | **26 MHz**, mot de fréquence calculé à la compilation |
| PC ↔ ESP32 | USB-série **115200 bauds**, 8N1 |

Le programme du CC1101 fixe la fréquence MCZ. Le mode asynchrone du circuit
transporte des niveaux, et l’ESP32 réalise l’encodage Manchester.
[Documentation CC1101 de Texas Instruments](https://www.ti.com/lit/ds/symlink/cc1101.pdf)

L’encodeur utilise un demi-bit de **414 µs**, un préambule haut de **103 ms**,
un séparateur bas/haut de **414/828 µs** avant chaque octet et une pause
basse de **3 712 µs** entre les répétitions. Il transmet cinq fois la même
trame. La commande dure environ **513 ms** selon ce modèle. Le RMT vise
un pas de **1 µs**. Ces durées décrivent le signal construit par le firmware.

## Format des trames

| Octets | Contenu |
|---|---|
| 1 à 3 | Identifiant de la télécommande |
| 4 | Trois bits ventilateur 1, trois bits puissance, deux bits mode |
| 5 | Bits 5 à 3 pour le ventilateur 2, autres bits conservés tels que capturés |
| 6 et 7 | CRC-16/XMODEM des cinq premiers octets, poids fort d’abord |

Le mode 1 correspond au manuel et le mode 0 à l’arrêt pour la séquence
capturée. Le code fixe un **réglage absolu**. Un appui `+` et un appui `−`
qui ramènent à la même combinaison produisent les mêmes octets. La position
6 du ventilateur 1 correspond à Auto. Le CRC vérifie l’intégrité de la
trame. L’authentification réseau repose sur une clé séparée.

Le [journal conservé](../captures/20261109-205625-968354_live.log) contient
110 réceptions valides regroupées en 22 gestes. Le
[catalogue](../config/catalogue_mcz.csv) les associe aux gestes dans leur
ordre. La validation vérifie les CRC et les cinq réceptions de chaque
ligne. Chaque journal repart de `RX #0001`. La compilation déduplique
les profils des deux captures avant de calculer les profils dérivés.

### Ventilateur 2

La [capture du 10 novembre](../captures/20261110-065656-157595_live.log)
contient 55 trames en 11 groupes de cinq. Le propriétaire a fait varier
uniquement le ventilateur 2, en mode manuel avec **flamme 3** et
**ventilateur 1 au niveau 5**. Le quatrième octet est resté à `AD`.

| Réglage du ventilateur 2 | Trame capturée |
|---|---|
| Arrêt (0) | `C8 CC 02 AD 80 59 C9` |
| Niveau 1 | `C8 CC 02 AD 88 D8 C1` |
| Niveau 2 | `C8 CC 02 AD 90 4B F8` |
| Niveau 3 | `C8 CC 02 AD 98 CA F0` |
| Niveau 4 | `C8 CC 02 AD A0 7D AB` |
| Niveau 5 | `C8 CC 02 AD A8 FC A3` |
| Auto (6) | `C8 CC 02 AD B0 6F 9A` |

À flamme et ventilateur 1 constants, seuls les bits `0x38` de l’octet 5
et les deux octets du CRC changent. Pour un niveau `v` de 0 à 6, on
calcule `octet5 = (octet5 & 0xC7) | (v << 3)`. Si la flamme ou le
ventilateur 1 change aussi, on calcule l’octet 4 avec
`(ventilateur1 << 5) | (flamme << 2) | 1` en mode manuel. On recalcule
ensuite le CRC-16/XMODEM des cinq premiers octets.

Par exemple, la trame calculée pour **flamme 1, ventilateur 1 à 1,
ventilateur 2 à 2** est `C8 CC 02 25 90 D9 C9`. Les deux champs de
ventilation et la puissance sont également encodés séparément dans
le [transmetteur MCZ EGO de sfauvart](https://github.com/sfauvart/esp32-s2-mcz/blob/a7933043a11a2984a114f9644365f35a24b516ea/components/mcz_rf_driver/mcz_rf_driver.cpp#L128-L151).

La génération vérifie qu’elle reproduit chaque profil manuel capturé
octet pour octet. Lorsque les sept niveaux du ventilateur 2 sont
présents dans les captures, elle produit les 210 combinaisons
explicites. Parmi elles, sept sont capturées et 203 sont calculées.
La table conserve aussi les dix profils d’origine à deux réglages et
la trame d’arrêt `off`. Le CSV et les journaux contiennent les
observations réelles. Les profils calculés sont validés sur le format
et le CRC, et leur réponse sur le poêle se vérifie séparément.

## Chaîne de commande

Application externe → Wi-Fi → [API HTTP de l’ESP32](API.md) → encodeur →
RMT → CC1101 → poêle. La [page locale](APPLICATION_LOCALE.md) emprunte
USB jusqu’à l’ESP32, puis la même chaîne radio. Les deux entrées partagent
un délai entre commandes et l’historique des requêtes. Le firmware de
la carte est dédié à l’émission. Il attend au repos une commande valide
et explicite.

Le signal reçu par le poêle et le changement physique s’observent sur
le matériel. Le compteur TX et le résultat `sent` décrivent l’émission
vue par le firmware.
