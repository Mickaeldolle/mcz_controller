# Sources et captures MCZ — analyse du 30 octobre 2026

**Mise à jour ultérieure : 35 trames réelles ont été validées après passage à RMT
et test de ventilation. Voir [le rapport de succès RX](RAPPORT_RX_VALIDE.md).**
L'analyse ci-dessous décrit les captures antérieures non décodables.

## Conclusion opérationnelle

Les données montrent une signature temporelle compatible avec la famille MCZ,
mais **aucune trame complète avec parité et CRC validés**. La télécommande n'est
donc ni déclarée totalement muette, ni déclarée fonctionnelle. La première
priorité est de qualifier la démodulation et la capture des niveaux, avant de
modifier le CRC ou de tenter une émission.

Cette analyse est hors ligne : aucun réglage matériel ni firmware n'a été changé
pendant cette relecture. Le dernier profil matériel confirmé reste MCZ 434,50 MHz,
bande 101,6 kHz. Les captures détaillées analysées ci-dessous sont antérieures,
à 58 kHz. Une capture MCZ après élargissement manque encore.

## Ce que les sources permettent réellement de conclure

| Source examinée | Apport | Limite |
|---|---|---|
| [KerberRF/APPLI_MCZ](https://github.com/KerberRF/APPLI_MCZ), `MCZ explains.txt`, `src/Appli_Emit.c`, `src/manchester.c`, `src/manchester.h` | 7 octets ; encapsulation 12 bits ; parité paire incluant le drapeau premier octet ; CRC XMODEM ; préfixe par mot ; 5 répétitions. | Implémentation historique principalement TX ; pas une capture de notre exemplaire. |
| [sfauvart/esp32-s2-mcz](https://github.com/sfauvart/esp32-s2-mcz), `components/mcz_rf_driver/mcz_rf_driver.cpp` | Même structure portée sur ESP32 ; demi-bit 414 µs, préfixe de commande 103 ms. | Dérive de KerberRF : ne constitue pas une confirmation indépendante. |
| [mylifeos/mcz-musa-esphome-home-assistant](https://github.com/mylifeos/mcz-musa-esphome-home-assistant), `mcz-receiver.yaml`, `mcz-remote.yaml` | Le RX contrôle Manchester, start/stop, parité, premier octet, séparateurs et CRC. | Son RX utilise un RXB12 avec capture RMT ESPHome ; le CC1101 sert au TX. Il ne fournit pas une configuration CC1101 RX qualifiée pour notre ancien Musa. |
| [node-rfxcom](https://github.com/rfxcom/node-rfxcom/blob/master/lib/thermostat4.js) | ID 24 bits, modes et paramètres ventilateurs/puissance. | Paquet de commande hôte vers un équipement RFXCOM, différent des 7 octets RF ; ne pas utiliser comme référence de chronogramme. |
| [Manuel MCZ 8901166500, §5.1](https://solarnet-online.com/wp-content/uploads/2017/03/Musa-comfort-air-Manual.pdf) | Télécommande 434,5 MHz et modèle Comfort Air. | Pas de spécification binaire du protocole ni preuve de l'état de la télécommande. |
| [RFXCOM User Guide 5.94, §16, page 58](https://rfxcom.com/WebRoot/StoreNL2/Shops/78165469/MediaGallery/Downloads/RFXtrx_User_Guide.pdf) | Réception MCZ à 434,50 MHz et récupération de l'ID ; exemple de modèle 2 ventilateurs. | Décodage interne propriétaire. Le fan2=7 affiché dans son exemple n'établit pas la signification de cette valeur dans notre trame. |

Les révisions des quatre dépôts sont consignées dans ANALYSE_PROTOCOLE.md.

## Format vérifié sur les sources

La structure attendue par mot est : start=1, données MSB d'abord, indicateur de
premier octet, parité paire sur données+indicateur, stop=1.
Avant chaque mot, les émetteurs ajoutent trois demi-bits LOW/HIGH/HIGH.
Cela conduit à **186 demi-bits** entre le premier start et le dernier stop :
7×24 + 6×3. Notre décodeur et celui de mylifeos vérifient cette structure.

La valeur 393 µs active dans KerberRF compense sa latence logicielle Raspberry Pi ;
le même fichier indique 414 µs mesurés. Ce n'est pas une justification pour
remplacer aveuglément 414 par 393 dans notre récepteur.
La convention inversée est déjà essayée par le décodeur. Aucune divergence de
CRC n'a été trouvée : les cinq premiers octets sont protégés par XMODEM,
initial 0, polynôme 0x1021, résultat transmis MSB en premier.

## Résultats sur les journaux locaux

| Journal | Captures brutes | Impulsions | Segments longs 85–115 ms | Médiane de ces segments | Durées <250 µs | Niveaux consécutifs de même signe |
|---|---:|---:|---:|---:|---:|---:|
| `20261030-103741_first-rx.log`, sans aucun appui confirmé par l'utilisateur | 7 | 1192 | 0 | — | 21,48 % | 40 |
| `20261030-105326_buttons.log`, déclenchement sur niveau fort | 8 | 5008 | 7 | 102,513 ms | 44,17 % | 149 |
| `20261030-110002_buttons.log`, après correction des registres TI | 5 | 3681 | 5 | 102,527 ms | 53,46 % | 99 |

Sur les 13 captures déclenchées, 11 contiennent un segment continu de 101,9 à
103,0 ms. Une autre présente deux morceaux de 13,672 et 88,328 ms, soit 102 ms
au total. Ce préfixe absent de la référence sans appui, et proche des 103 ms des
sources, renforce l'hypothèse que l'on observe bien une émission de la télécommande.
Ce n'est cependant pas une authentification ni un décodage MCZ.

Les durées <250 µs sont inférieures au demi-bit attendu, même avec la tolérance
initiale de 25 %. Les niveaux de même signe successifs signifient que les
enregistrements ne forment pas partout une suite de fronts alternés propre.
Ces anomalies peuvent venir du bruit démodulé, de glitches ou de notre capture
GPIO ; leur origine exacte ne peut pas être isolée avec ces seuls journaux.
L'absence de débordement logiciel n'exclut pas des fronts non capturés.

Le seuil radio ne garde pas uniquement les moments où la porteuse est forte :
les fenêtres de 600 ms comprennent aussi les espaces et du bruit. Les pourcentages
ci-dessus décrivent ces fenêtres entières, pas un taux d'erreur binaire MCZ.
Les différences entre les deux essais ne constituent pas une mesure comparative
calibrée : appuis, position, commandes et conditions n'étaient pas contrôlés.

## Essais de décodage hors ligne

L'outil `tools/analyze_mcz_capture.py` conserve les données originales et essaie
explicitement 18 hypothèses par journal : données brutes, fusion des niveaux
adjacents identiques, suppression d'excursions <80/120/180/240 µs, avec demi-bits
400/414/428 µs. Chaque suppression conserve la durée totale.
Toutes les hypothèses imposent la structure complète, la parité et le CRC.

**Résultat : aucune trame valide.** Le nettoyage simple et ces variations de
timing ne suffisent donc pas. Aucun ID ni paramètre n'est déduit d'octets partiels.
Cette recherche limitée n'exclut pas un autre format ou un autre timing réel.
Les résultats détaillés sont dans `mcz-capture-analysis.json`.

Le nouvel analyseur passe quatre tests : signal synthétique connu à cinq
répétitions et deux polarités, CRC corrompu rejeté, nettoyage préservant le temps
et les données originales, entrées vides/tronquées. Les fixtures synthétiques
ne constituent pas une qualification RF.

## Priorité pour le prochain essai

1. **Qualifier la capture des niveaux.** Comparer la capture GPIO à une capture
   matérielle RMT filtrée sur le même GDO0, ou à un analyseur logique disponible.
   Conserver le préfixe long et les répétitions, et compter les anomalies de niveaux.
   Le filtre doit rester très inférieur au demi-bit attendu.
2. **Exploiter le profil 101,6 kHz déjà installé**, sans modifier simultanément
   le décodeur. Capturer une seule commande répétée pour faciliter la comparaison.
3. Si les fronts restent déformés, caractériser la fréquence centrale autour de
   434,50 MHz, puis les paramètres OOK/AGC, avec un seul facteur à la fois.
4. Seulement sur des signaux plus propres : comparer les mots et les répétitions
   avant CRC. Ne pas inventer de bits manquants pour obtenir une trame acceptée.

La [fiche TI §27.1](https://www.ti.com/lit/ds/symlink/cc1101.pdf) documente du
jitter en sortie asynchrone et des glitches très brefs (37–38,5 ns). Il ne faut
pas assimiler directement ces derniers aux impulsions de 50–200 µs mesurées.
Cela justifie de qualifier notre acquisition, pas d'attribuer automatiquement
tous les défauts au CC1101. La [note TI DN022](https://www.ti.com/lit/an/swra215e/swra215e.pdf)
explique aussi que certains réglages AGC peuvent dégrader la réception OOK.
Ces pistes précèdent une conclusion de panne de la télécommande.

## Reproduire l'analyse

```powershell
python tools/analyze_mcz_capture.py captures/20261030-103741_first-rx.log captures/20261030-105326_buttons.log captures/20261030-110002_buttons.log --output docs/mcz-capture-analysis.json
python tests/test_analysis.py
```

Toujours RX uniquement. Le problème d'absence de réaction du poêle peut aussi
concerner son récepteur, son association ou un autre état de fonctionnement ;
aucun de ces points n'est tranché par les mesures actuelles.
