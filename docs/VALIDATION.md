# Validation et reprise

Date : 30 octobre 2026.

## Qualification logicielle

- Analyse des quatre dépôts et manuel MCZ réalisée ; références dans ANALYSE_PROTOCOLE.md.
- Tests C++ du décodeur exécutés sous WSL, g++ 11.4, avec AddressSanitizer et UBSan : PASS.
- Compilation cible ESP32 classique `esp32dev`, plateforme 6.9.0 : PASS, chemin RX actif et version verrouillée par défaut. Aucun téléversement.
- Après confirmation utilisateur du câblage, compilation du firmware RX activé : PASS ; RAM 46 656 octets, flash 289 933 octets. Téléversement COM3 réussi et intégrité flash vérifiée par esptool.
- Outil Python de comparaison : exemple avec deux CRC corrects vérifié.
- Tests des outils : 3 tests PASS, dont lecture d'une capture synthétique construite indépendamment avec le CRC Python et rejet des journaux invalides/tronqués.
- Câblage confirmé par l'utilisateur le 30 octobre 2026, sans photo du montage. Réception activée dans platformio.ini ; confirmation déclarative, sans contrôle électrique.
- Aucun code d'émission intégré.

## Qualification matérielle — partielle

| Point | État |
|---|---|
| Carte ESP32 | Photo reçue : ESP32 classique, carte 38 broches, USB micro-B, pont CP2102 ; fabricant/référence exacte non identifiés. Profil esp32dev conservé. |
| Module radio | Verso reçu : E07-M1101D ; face composants marquée 433M V2.0, antenne SMA, connecteur 2×4 numéroté 1..8. Identification visuelle, non électrique. |
| Brochage CC1101 / quartz | Brochage recoupé avec le manuel Ebyte E07-M1101D-SMA, section 3 ; tableau dans README. Quartz 26 MHz documenté pour ce modèle, non mesuré sur l'exemplaire. Câblage déclaré réalisé et confirmé par l'utilisateur ; non contrôlé électriquement. |
| Port USB ESP32 | COM3, Silicon Labs CP210x ; puce ESP32-D0WD-V3 révision 3.1 identifiée par esptool |
| CC1101 détecté via SPI | PASS : PART=00 VERSION=14 ; registres de configuration relus et vérifiés |
| État RX confirmé | PASS : RX READY 434.50MHz OOK, MARCSTATE=0D ; fréquence configurée, non mesurée avec un instrument RF |
| Bursts télécommande cohérents | PASS : 7 séries de 5 répétitions pendant les changements de ventilation, capture RMT |
| Trames réelles avec CRC valide | **35**, toutes redécodées hors ligne et CRC vérifiés par Python |
| Identifiant observé | `C8CC02`, stable |
| Paramètres réels observés | Mode=3, puissance=3, fan1=2/3/4/5/6, fan2=7, user=2, réservé=0 |
| Compatibilité Musa Comfort Air | Structure RX confirmée sur la télécommande testée ; réaction du poêle non confirmée |
| Autorisation de développer TX après RX | En attente de validation RX explicite |

## Reprise

1. Identifier les deux cartes et confirmer le câblage avant toute alimentation.
2. Adapter carte/GPIO, activer uniquement `MCZ_WIRING_CONFIRMED`, compiler.
3. Brancher l'ESP32 USB, identifier le port et flasher le firmware RX.
4. Suivre le README pour capturer plusieurs commandes ; conserver les logs bruts.
5. Noter ci-dessous le nombre de trames, leurs CRC, l'ID, les paramètres,
   les répétitions et les écarts aux sources. Comparer un seul réglage à la fois.
6. Si aucune réception : vérifier la chaîne RX avec une source connue.
7. Mettre à jour ce rapport avant toute décision sur TX.

## Rapport RX à compléter avec preuves

Journal de démarrage : `captures/startup-COM3.log`. Ce journal valide le dialogue
SPI et l'état du récepteur, pas encore la réception d'une télécommande.

Premier essai d'environ une minute : `captures/20261030-103741_first-rx.log`.
Le récepteur reste en état 0D, VALID=0. Les impulsions enregistrées ne suffisent
pas à identifier la télécommande ; aucune conclusion de panne n'est établie.
L'utilisateur confirme n'avoir appuyé sur aucun bouton durant ce premier essai :
il constitue une référence de bruit/activité ambiante, avec 7 séquences brutes,
0 trame valide et 0 débordement signalé.

Second enregistrement de 90 secondes : `captures/20261030-104301_remote-buttons.log`.
L'utilisateur confirme les appuis OFF, ON, température +/− et ventilation +/−,
écran réactif, à environ 10 cm de l'antenne. Récepteur en état 0D, aucune trame
à CRC valide reçue (17 séquences brutes, aucun débordement signalé).

Diagnostic ajouté sans changement RF : commande `d`, lecture RSSI toutes les
10 ms environ, min/max et nombre de fronts rapportés chaque seconde.
Compilation et téléversement de cette version réussis ; lecture matérielle de
contrôle réussie : environ 100 échantillons/seconde, aucune erreur SPI, état RX
0D maintenu, niveaux estimés observés entre −109 et −101,5 dBm sur les premières
fenêtres. Aucune synchronisation avec un appui n'était demandée pour ce contrôle.
RSSI estimé, non calibré : conversion avec offset typique de 74 dB selon
la [fiche TI, §17.3](https://www.ti.com/lit/ds/symlink/cc1101.pdf).
Ce niveau n'identifie ni le protocole ni l'émetteur. La capture brute ponctuelle
peut être consommée par du bruit avant un appui : les journaux précédents ne
suffisent pas à exclure une émission de la télécommande.

### Essai RSSI avec consigne repos puis appuis

Journal : `captures/20261030-105013_buttons.log`, durée 55 secondes.
Consigne : dix secondes sans appui puis appuis espacés, télécommande à 30–50 cm.
Les premières fenêtres présentent des maxima autour de −102 dBm ; ensuite
plusieurs fenêtres montent vers −73,5/−74,5 dBm. État RX 0D maintenu et aucune
trame valide. Cette hausse d'environ 28 dB est compatible avec une émission
durant les essais, mais l'identité de l'émetteur et le protocole ne sont pas prouvés.
Les horaires exacts des appuis n'ont pas été marqués dans le journal.
Prochaine étape : capturer les impulsions des hausses de signal pour analyser
leurs timings ; ne pas conclure à une télécommande totalement muette.

### Captures déclenchées sur niveau radio

Firmware RX étendu avec `t` : seuil −90 dBm estimés, fenêtre 600 ms bornée
à 2048 impulsions, signalement et rejet en cas de débordement, réarmement
après une seconde. Compilation et téléversement COM3 réussis.
Journal : `captures/20261030-105326_buttons.log` (65 secondes).
Huit fenêtres exportées, 492 à 670 impulsions chacune, aucun RX_OVERFLOW
ni TRIGGER_DROPPED. Les pics se situent autour de −63 dBm.
Analyse avec le décodeur C++ hors ligne : **0 trame valide**.
Impulsions proches de 414/828 µs présentes, mais nombreuses coupures/glitches ;
aucune structure complète de 7 octets avec CRC confirmé. L'analyse exploratoire
de nettoyage/tolérance n'a pas fourni de CRC valide ; elle n'a pas été intégrée
au décodeur opérationnel.

Relecture de la [note TI DN022 §3.2](https://www.ti.com/lit/an/swra215e/swra215e.pdf) :
omission identifiée dans le pilote initial pour la bande 58 kHz : FIFOTHR,
TEST2 et TEST1 étaient laissés à leur valeur reset. Correction appliquée :
respectivement 0x47, 0x81 et 0x35. FREND1=0x56 était déjà renseigné.
Fréquence, bande, débit, AGC et décodeur inchangés pour isoler cette correction.
Le bénéfice RF reste à vérifier avec une nouvelle capture après correction.
Compilation et téléversement de la correction réussis. Contrôle de démarrage
`captures/20261030-105720_diagnostic.log` : registres relus conformes, état RX
0D, armement du déclencheur opérationnel, aucune erreur SPI. Aucun appui n'était
demandé durant ce contrôle de cinq secondes. Prochain essai à synchroniser
avec l'utilisateur : capture déclenchée avec les mêmes appuis et la même distance.

### Essai après correction TI, bande 58 kHz

Journal : `captures/20261030-110002_buttons.log` (55 secondes).
Cinq captures déclenchées, 678 à 857 impulsions, aucun débordement ni rejet.
Décodeur embarqué et outil C++ hors ligne : **0 trame valide**.
La correction des registres TI n'a donc pas suffi à qualifier le RX.
Pics au déclenchement entre −82 et −76 dBm ; ces valeurs dépendent aussi
de la position de la télécommande et ne constituent pas une comparaison calibrée.

Prochain essai préparé : élargissement RX de 58 à 101,6 kHz nominaux
(MDMCFG4 0xF6 → 0xC6), fréquence centrale 434,50 MHz inchangée.
Objectif : tester l'hypothèse de filtrage trop étroit/décalage de porteuse.
Le débit, l'AGC et le décodeur restent identiques. FREND1 est adapté à la
nouvelle bande (0x56 → 0xB6, bande >101 kHz selon DN022 §3.2).
Compilation/téléversement réussis. Contrôle `captures/20261030-110308_diagnostic.log` :
RX_CONFIG MDMCFG4=C6 FREND1=B6 BW=101,6 kHz, état RX 0D, aucune erreur SPI.
Pas encore de capture d'appuis MCZ à cette nouvelle bande.

### Piste de contrôle avec une autre télécommande

L'utilisateur indique que le poêle ne réagit actuellement plus à la télécommande
d'origine, même si son écran fonctionne. Une défaillance RF de la télécommande
est une hypothèse ; panne du récepteur du poêle ou association perdue non exclues.
Il propose une télécommande de garage comme source de contrôle. Marque/modèle,
fréquence et modulation à identifier avant modification de la réception.
Un succès sur une autre fréquence qualifierait cette chaîne RX dans ces conditions,
sans prouver à lui seul la réception MCZ à 434,50 MHz. Les pics RSSI observés
jusqu'ici n'identifient pas formellement leur émetteur.

Le lien vendeur fourni par l'utilisateur correspond au Chamberlain ML700EV.
La [fiche fabricant ML700EV](https://chamberlain.de/en-ne/products/garagentorantrieb-comfort-ml700ev)
annonce deux télécommandes TX2REV à 868 MHz dans le kit. La documentation de
la motorisation mentionne aussi un récepteur multibande 433/868 MHz ; cela
ne suffit pas à établir la bande de la télécommande réellement possédée.
Référence au dos à confirmer. Le module E07-M1101D-SMA marqué 433M est une
version adaptée à 387–464 MHz selon sa documentation : une absence de détection
d'une télécommande 868 MHz avec ce module n'est pas un test RX MCZ concluant.

### Contrôle positif garage 868 MHz

L'utilisateur a confirmé l'inscription 868 MHz sur sa télécommande et autorisé
l'essai exploratoire hors bande nominale du module. Profils RX ajoutés :
868,30 / 868,95 / 869,85 MHz, conformément aux fréquences de la famille TX2REV
dans la [documentation Chamberlain](https://doc.chamberlain.de/manuals/online/114A4C087.pdf).
Le décodeur MCZ est inhibé dans ces profils. Aucun mode TX ajouté.
Compilation et téléversement réussis. Test bref des changements et restauration :
`captures/20261030-110858_garage868.log`.

Essai avec consigne d'appuis répétés : `captures/20261030-110921_garage868.log`,
15 secondes par fréquence. Les fenêtres montrent des hausses franches du
niveau reçu, du fond autour de −112 dBm vers −70 à −74 dBm, accompagnées de
centaines de fronts. Ce contrôle positif montre la détection d'une source RF
pendant les essais ; il ne valide ni le décodage du protocole garage, ni MCZ,
ni la sensibilité du module sur toute une bande. Aucune erreur SPI signalée.
Retour 434,50 MHz confirmé par `RX_PROFILE OK FREQ_HZ=434500000 STATE=0D`
puis `STATE=0D VALID=0 FREQ_HZ=434500000`.

Conséquence : ne pas diagnostiquer une panne globale de la chaîne RX, ni une
télécommande MCZ totalement muette sur la seule absence de CRC. Les pics MCZ
précédents restent à relier à une structure de trame exploitable.

### Relecture des sources et analyse hors ligne

Voir `docs/ANALYSE_SIGNAUX_MCZ.md` et `docs/mcz-capture-analysis.json`.
Treize captures déclenchées MCZ comparées à sept captures sans appui : préfixes
autour de 102 ms caractéristiques des références, absents de la référence au repos.
Aucune trame valide dans les 18 hypothèses de nettoyage/timing par journal.
Quatre tests de l'analyseur PASS. Aucun firmware ou réglage radio changé durant
cette analyse. Priorité recommandée : qualifier les fronts et leur acquisition,
puis capturer la même commande avec la bande 101,6 kHz déjà installée.

### Capture RMT mise en place

Capture GPIO remplacée par RMT RX, canal 0, 8 blocs matériels (512 mots),
tampon pilote 32 Kio. Compteur 1 MHz vérifié au démarrage (APB/80), filtre
255 cycles APB soit environ 3,19 µs. Ce seuil filtre les glitches très brefs,
pas les impulsions parasites de 50–200 µs. Aucun réglage radio changé.
Fusion des niveaux adjacents de même signe avec conservation du temps,
contrôle des bornes et rejet des blocs pleins/invalides. Fin de bloc à 3 ms :
le préfixe de 103 ms n'est pas conservé intégralement. La pause finale omise
par le pilote est ajoutée comme borne minimale opposée de 3000 µs, annoncée
par `idle_tail_min_us` ; ce n'est pas une durée exactement mesurée.
La structure de trame, la parité et le CRC restent obligatoires.

Référence : [Espressif RMT / IDF 4.4](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/peripherals/rmt.html).
Les compteurs `dropped` ne remplacent pas la recherche des erreurs du pilote
RMT dans le journal. La capture matérielle ne garantit pas à elle seule
l'absence de perte ou de distorsion RF.

Tests C++ des durées/bornes et du décodeur exécutés avec ASan/UBSan : PASS.
Compilation et téléversement COM3 réussis. Contrôle de démarrage et données
RMT au repos : `captures/20261030-113423_diagnostic.log`.

Nouvel essai avec consigne d'une seule commande répétée :
`captures/20261030-113627_buttons.log` (45 secondes). État RX 0D, 2202 blocs
traités, aucun rejet compté, aucune erreur SPI, aucune trame MCZ valide.
Aucun dépassement du seuil de déclenchement −85 dBm : aucun bloc brut exporté.
L'utilisateur confirme des appuis sur **température + toutes les cinq secondes**.
Cet essai ne permet pas encore une comparaison des trames MCZ GPIO/RMT.
Le format des sources ne contient pas de champ de consigne de température,
mais mode/puissance/ventilateurs : un changement de consigne ne garantit pas
une émission immédiate de paramètres différents. Le manuel §5.5.2 décrit la
régulation AUTO sans préciser une émission RF par appui. Cette piste reste
une hypothèse à vérifier, pas un comportement firmware établi sur l'exemplaire.
Prochain essai : choisir une commande liée aux champs RF et préciser le mode
ainsi que l'état du poêle avant de proposer une action ON/OFF.
L'utilisateur précise : télécommande en AUTO, poêle actuellement éteint.
Le manuel 8901166500 §5.3.1 précise que C modifie et E confirme les réglages.
Il reste à vérifier si les appuis température + étaient suivis d'une validation
E/OK. Ne pas supposer qu'AUTO affiché décrit à lui seul l'état réel du poêle,
ni proposer d'alterner ON/OFF sur un poêle éteint sans intention de démarrage.
Précision utilisateur : uniquement température + pendant cet essai, mais sur
son appareil les modifications de température étaient habituellement reçues
sans validation supplémentaire. L'hypothèse d'une validation OK manquante est
donc retirée comme explication de cet essai. Un contrôle comparatif par
ventilation +/− a été proposé, avec acquisition RMT et réglages RF inchangés.

### Succès RX sur la ventilation

Journal `captures/20261030-123642_buttons.log` : **35 trames valides**, 7 séries
de 5, ID `C8CC02` stable. Vérification hors ligne des 35 captures avec le
décodeur C++, puis CRC des octets par Python `binascii.crc_hqx` : PASS.
Fan1 suit 2, 3, 4, 5, 6, 5, 4 ; mode=3, puissance=3, fan2=7, user=2 et
réservé=0 restent constants. Aucun rejet compté ni erreur pilote/SPI retrouvée.
L'utilisateur confirme le sélecteur du poêle sur REMOTE.
Rapport de qualification : `docs/RAPPORT_RX_VALIDE.md`. TX non ajouté.

```text
Date et matériel :
Journal(s) :
Commande(s) télécommande :
Nombre de trames valides / nombre de captures :
ID observé et stabilité :
CRC et validation structurelle :
Mode / puissance / fan1 / fan2 / user / réservé :
Timing et répétitions mesurés :
Différences par rapport aux références :
Conclusion : protocole confirmé / non confirmé
Validation explicite de la phase RX :
```
