# Analyse préalable — 30 octobre 2026

## État

Mise à jour : **35 trames RX réelles valides**, ID stable `C8CC02`, ventilation 1
cohérente. Structure et CRC confirmés sur la télécommande testée ; voir
[le rapport RX réel](RAPPORT_RX_VALIDE.md). Fan2=7 et mode=3 restent à recouper
avec les réglages de l'appareil. Aucun émetteur, rejeu ou appairage implémenté.
Les sections suivantes conservent l'analyse préalable des références.

## Sources étudiées

Les dépôts complets ont été téléchargés dans `research/`, exclus du suivi.
Révisions examinées :

| Source | Révision |
|---|---|
| [KerberRF/APPLI_MCZ](https://github.com/KerberRF/APPLI_MCZ) | `9e40d5b78ca106b9dbddf0c227b899ccd6cb30be` |
| [sfauvart/esp32-s2-mcz](https://github.com/sfauvart/esp32-s2-mcz) | `a7933043a11a2984a114f9644365f35a24b516ea` |
| [mylifeos/mcz-musa-esphome-home-assistant](https://github.com/mylifeos/mcz-musa-esphome-home-assistant) | `cc8d07ae5b46f06a549a92f1a203ef965424050c` |
| [rfxcom/node-rfxcom](https://github.com/rfxcom/node-rfxcom) | `12999d4f2946402cb9636392e0775b30de7a2e0a` |

## Comparaison

| Sujet | Conclusion et limite |
|---|---|
| Charge utile | KerberRF décrit 7 octets : ID 24 bits, paramètres sur 2 octets, CRC sur 2 octets. |
| CRC | KerberRF emploie une division augmentée ; sfauvart reprend cette approche. Le calcul direct XMODEM de mylifeos correspond au même résultat attendu, initial 0, polynôme 0x1021, MSB en premier. |
| Encapsulation | Start=1, données MSB d'abord, premier-octet=1 seulement sur l'octet 0, parité paire couvrant données et indicateur, stop=1. |
| Manchester | 1=HIGH/LOW. Un préfixe LOW/HIGH/HIGH précède chaque mot ; le décodeur recherche le premier start puis vérifie les six séparateurs suivants. |
| Temps | KerberRF documente 414 µs mesurés mais utilise 393 µs pour compenser la latence logicielle Raspberry Pi. sfauvart utilise 414 µs, espace 3712 µs et préfixe 103000 µs. Ne pas reprendre 393 comme durée physique cible. |
| Répétitions | Les émetteurs de référence répètent cinq fois ; notre RX rapporte chaque trame séparément, sans exiger cinq répétitions pour diagnostiquer une télécommande défaillante. |
| Ventilateurs | 0..5 et auto=6 dans KerberRF et node-rfxcom. La valeur 7 n'est pas interprétée comme absence confirmée : elle reste visible comme atypique. |
| User/réservé | KerberRF indique user 0..3, défaut 2, sans expliquer sa fonction ; les bits bas restent inconnus. Aucune signification supplémentaire n'est supposée. |

sfauvart dérive de KerberRF : ce ne sont pas deux preuves indépendantes.
node-rfxcom confirme les domaines logiques mais envoie au matériel RFXCOM un
paquet hôte différent : ses octets ne sont pas directement une trame RF MCZ.

## Radio et matériel

Le [manuel MCZ 8901166500, §5.1 page 38](https://solarnet-online.com/wp-content/uploads/2017/03/Musa-comfort-air-Manual.pdf)
indique 434,5 MHz pour la télécommande et couvre le Musa Comfort Air.
Cela ne confirme pas à lui seul l'encapsulation de l'exemplaire de l'utilisateur.

Le projet mylifeos utilise le CC1101 pour **TX** ; son RX utilise un **RXB12 séparé**.
Son succès ON/OFF annoncé sur Musa 2.0 Air ne prouve donc ni notre RX CC1101,
ni la compatibilité avec l'ancien Comfort Air. Les niveaux de puissance physiques
ne sont pas tous vérifiés par son auteur.

Notre pilote SPI minimal suit la [fiche TI CC1101, §27.1 et registres](https://www.ti.com/lit/ds/symlink/cc1101.pdf) :
mode série asynchrone, GDO0 sortie démodulée, ASK/OOK, Manchester matériel et
CRC matériel désactivés. Oscillateur supposé 26 MHz, fréquence 434,50 MHz,
débit nominal environ 2400 baud. Bande RX initiale 58 kHz et paramètres AGC
à qualifier par capture réelle ; une absence de trames n'établit pas une panne
de télécommande. Le module, son quartz, l'antenne et les GPIO restent à confirmer.

## Corrections du document initial

Le séparateur de trois demi-bits doit être pris en compte. L'exemple
`A1 B2 C3 6D A0 12 34` est illustratif : `6D` représente fan1=3, pas 6,
et le CRC ne doit pas être pris pour une capture validée.

## Passage éventuel à TX

Requis : plusieurs commandes réelles, ID stable, intégrité et valeurs cohérentes,
rapport mis à jour avec captures et écarts, puis validation explicite de la phase RX.
Commencer alors par le rejeu d'une capture ; aucune génération ni association avant.
