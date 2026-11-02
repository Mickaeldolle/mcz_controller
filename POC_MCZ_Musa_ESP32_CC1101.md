# POC — Reproduire la télécommande RF d’un poêle MCZ Musa Comfort Air avec ESP32 + CC1101

## 1. Objectif

Construire un **Proof of Concept (POC)** permettant de vérifier qu’un **ESP32 équipé d’un CC1101** peut :

1. recevoir les trames radio émises par une télécommande MCZ ;
2. décoder le protocole MCZ utilisé autour de **434,50 MHz** ;
3. identifier les champs utiles : identifiant télécommande, mode, puissance, ventilateur 1, ventilateur 2 ;
4. valider le CRC des trames ;
5. dans un second temps uniquement, réémettre une trame MCZ valide vers le poêle.

Le poêle concerné est un **MCZ Musa Comfort Air**, ancienne génération / Active System, autour de 2011–2013, avec :
- télécommande LCD RF ;
- panneau d’urgence avec sélecteur `ON / REMOTE / OFF` ;
- double ventilation Comfort Air ;
- une canalisation vers une pièce à l’étage.

Le POC doit d’abord être **100 % passif en réception**.  
Ne pas émettre vers le poêle tant que le protocole reçu n’a pas été confirmé.

---

## 2. Matériel disponible

- ESP32
- module RF **CC1101** version 433 MHz
- Raspberry Pi disponible si besoin
- PC Windows / WSL disponible
- télécommande MCZ d’origine, potentiellement défaillante
- poêle MCZ Musa Comfort Air fonctionnel

Le Raspberry Pi n’est pas nécessaire pour le premier test.  
Le chemin le plus court est :

```text
Télécommande MCZ
      │
      │ 434,50 MHz ASK/OOK
      ▼
   CC1101
      │ SPI
      ▼
    ESP32
      │ USB série
      ▼
      PC
```

---

## 3. Contraintes de sécurité

Ce projet ne doit **jamais piloter directement** :

- la vis sans fin ;
- la bougie d’allumage ;
- l’extracteur de fumées ;
- les sécurités thermiques ;
- les moteurs internes du poêle.

L’objectif est uniquement de **reproduire les commandes utilisateur envoyées par la télécommande officielle**.

Ne pas :
- désactiver une sécurité MCZ ;
- couper brutalement l’alimentation électrique du poêle pour l’arrêter ;
- utiliser le POC comme unique mécanisme de sécurité ;
- envoyer automatiquement des commandes au boot de l’ESP32 ;
- émettre tant que les trames reçues n’ont pas été validées.

La première phase doit être exclusivement RX.

---

# 4. Informations connues sur la télécommande MCZ

La documentation MCZ de cette génération indique une fréquence de télécommande de :

```text
434,5 MHz
```

La famille documentaire concernée couvre notamment :

- Suite Air / Comfort Air
- Club Air / Comfort Air
- Musa Air / Comfort Air
- Toba Air / Comfort Air

Référence de manuel retrouvée :

```text
8901166500
```

Le manuel indique explicitement que la télécommande fonctionne à **434,5 MHz**.

---

# 5. Protocole RF reverse-engineeré

Plusieurs projets open source indépendants décrivent le même protocole.

La charge utile logique est constituée de **7 octets**.

```text
Byte 0 : ID télécommande bits 23..16
Byte 1 : ID télécommande bits 15..8
Byte 2 : ID télécommande bits 7..0

Byte 3 :
bits 7..5 = ventilateur 1
bits 4..2 = puissance
bits 1..0 = mode

Byte 4 :
bits 7..6 = user
bits 5..3 = ventilateur 2
bits 2..0 = réservé / inconnu

Byte 5 = CRC16 MSB
Byte 6 = CRC16 LSB
```

Soit :

```text
byte3 = (fan1 << 5) | (power << 2) | mode

byte4 = (user << 6) | (fan2 << 3) | reserved
```

Valeurs connues :

### Mode

```text
0 = OFF
1 = ON / MANUAL
2 = AUTO
3 = ECO
```

### Puissance

```text
1..5
```

### Ventilateurs

```text
0..5 = niveaux
6    = AUTO
```

Certaines implémentations utilisent `7` pour signaler l’absence d’un ventilateur.

Pour notre Musa Comfort Air à deux ventilateurs, le champ `fan2` est particulièrement important.

---

# 6. CRC

Les 5 premiers octets sont protégés par un :

```text
CRC16 CCITT / XMODEM
polynôme : 0x1021
initial  : 0x0000
```

Le CRC obtenu est placé dans :

```text
byte5 = CRC MSB
byte6 = CRC LSB
```

Une trame ne doit être considérée valide que si :

```text
crc16(bytes[0..4]) == (byte5 << 8 | byte6)
```

---

# 7. Encapsulation et Manchester

Chaque octet est encapsulé dans un mot de **12 bits**.

Le projet historique `KerberRF/APPLI_MCZ` décrit un format de type :

```text
[start] [8 bits data] [first-frame flag] [parity] [stop]
```

Le premier octet possède un indicateur spécifique de début de trame.

Le flux est ensuite transmis avec un codage Manchester.

Convention observée dans les projets :

```text
1 => HIGH puis LOW
0 => LOW puis HIGH
```

Timing mesuré sur une télécommande MCZ :

```text
HALF_BIT        ≈ 414 µs
bit complet     ≈ 828 µs
INTER_FRAME     ≈ 3712 µs
COMMAND_PREFIX  ≈ 103000 µs
```

La trame de 7 octets est répétée environ :

```text
5 fois
```

---

# 8. Paramètres RF à tester

Le projet récent utilisant un CC1101 configure notamment :

```text
frequency       = 434.50 MHz
modulation      = ASK/OOK
packet mode     = désactivé / raw
Manchester      = géré dans le flux logiciel
symbol rate     ≈ 2400
```

Important : utiliser un **CC1101 version 433 MHz**.

Alimenter le CC1101 en :

```text
3.3 V
```

Jamais en 5 V.

---

# 9. Architecture du POC

## Étape 1 — RX brut

Créer un firmware minimal qui :

1. initialise le CC1101 ;
2. le place en réception ;
3. configure 434,50 MHz ;
4. récupère les changements d’état / impulsions via GDO0 ou GDO2 ;
5. mesure les durées en microsecondes ;
6. affiche les impulsions via `Serial`.

Exemple de sortie souhaitée :

```text
RX burst
+414
-414
+828
-414
...
```

Le but est uniquement de confirmer que la télécommande émet.

---

## Étape 2 — détection du timing Manchester

Convertir les impulsions en demi-bits d’environ :

```text
414 µs
```

Tolérance raisonnable initiale :

```text
± 20 à 25 %
```

À ajuster après observation réelle.

Détecter :

- les séquences Manchester ;
- la pause inter-trame ;
- la répétition de la même trame ;
- le préambule / niveau long initial.

---

## Étape 3 — reconstruire les mots de 12 bits

Pour chaque octet :

1. reconstruire les 12 bits ;
2. vérifier start/stop ;
3. vérifier la parité ;
4. identifier le premier octet ;
5. extraire les 8 bits de données.

À la fin :

```text
7 bytes
```

---

## Étape 4 — valider le CRC

Calculer le CRC16 XMODEM sur les cinq premiers octets.

Ne logger comme trame MCZ valide que si :

```text
CRC calculated == CRC received
```

Sortie console cible :

```text
MCZ FRAME VALID
ID       : A1B2C3
Mode     : MANUAL
Power    : 3
Fan1     : 6 (AUTO)
Fan2     : 4
User     : 2
Reserved : 0
CRC      : OK

Raw:
A1 B2 C3 6D A0 12 34
```

---

# 10. Premier test à effectuer

La télécommande MCZ actuelle semble ne plus fonctionner correctement.

Tester malgré tout si sa partie RF fonctionne encore.

Procédure :

1. alimenter la télécommande avec des piles neuves ;
2. ESP32 + CC1101 en RX ;
3. placer la télécommande à 20–50 cm de l’antenne ;
4. appuyer sur différents boutons ;
5. surveiller le port série.

Faire si possible des captures correspondant à :

```text
OFF
ON
Puissance +
Puissance -
Ventilateur 1 +
Ventilateur 2 +
```

Si une ou plusieurs trames valides sont reçues, les sauvegarder.

---

# 11. Analyse comparative

Si plusieurs commandes sont capturées, comparer les trames.

On s’attend à observer :

```text
ID1 ID2 ID3
```

identiques pour toutes les commandes.

Seuls principalement les octets 3 et 4 doivent évoluer.

Exemple :

```text
OFF :
A1 B2 C3 XX YY CRC CRC

ON P1 :
A1 B2 C3 XX YY CRC CRC

ON P5 :
A1 B2 C3 XX YY CRC CRC
```

L’agent doit produire un petit outil ou une fonction permettant de comparer les bits modifiés entre deux captures.

---

# 12. Phase TX — uniquement après validation RX

Ne développer l’émission qu’après avoir validé au moins une vraie trame de la télécommande.

Deux approches sont possibles.

## A. Rejouer une trame capturée

Première méthode de validation :

```text
capture vraie télécommande
        ↓
rejouer exactement la même trame
        ↓
CC1101
        ↓
poêle
```

C’est le test TX le plus prudent.

## B. Générer une nouvelle trame

Lorsque la structure est confirmée :

1. construire les cinq octets ;
2. calculer CRC16 XMODEM ;
3. encapsuler chaque octet ;
4. encoder Manchester ;
5. répéter cinq fois ;
6. émettre en ASK/OOK à 434,50 MHz.

---

# 13. Appairage avec un nouvel identifiant

Le manuel MCZ indique qu’une nouvelle télécommande peut être appairée au poêle.

Le panneau d’urgence comporte un bouton d’association.

La procédure documentée implique approximativement :

```text
mettre le poêle sur REMOTE
        ↓
activer la procédure d’association
        ↓
affichage "---"
        ↓
envoyer depuis la nouvelle télécommande
        ↓
le poêle apprend l’adresse de communication
```

Il est donc plausible que l’ESP32 puisse devenir une nouvelle télécommande avec un ID 24 bits choisi.

Cependant :

**ne pas considérer cela comme validé tant que le protocole de notre Musa n’a pas été confirmé en réception.**

La première stratégie TX doit être le rejeu d’un ID déjà observé.

---

# 14. Alternative si la télécommande est totalement morte

Si aucune émission RF n’est détectée :

1. ne pas conclure immédiatement que le protocole est différent ;
2. vérifier le fonctionnement RX du CC1101 avec une autre source 433 MHz si disponible ;
3. valider la fréquence et la configuration CC1101 ;
4. utiliser les trames et encodeurs des projets open source comme référence ;
5. envisager ensuite un appairage d’un nouvel ID avec le poêle.

---

# 15. Livrables attendus de Codex

Créer un petit projet autonome, idéalement PlatformIO ou Arduino/ESP-IDF.

Structure suggérée :

```text
mcz-rf-poc/
├── README.md
├── platformio.ini
└── src/
    ├── main.cpp
    ├── cc1101_radio.cpp
    ├── cc1101_radio.h
    ├── mcz_decoder.cpp
    ├── mcz_decoder.h
    ├── mcz_crc.cpp
    └── mcz_crc.h
```

Première version :

```text
RX only
```

Fonctions minimales :

```cpp
bool initRadio();
void startReceive();

bool decodeMCZFrame(...);
uint16_t crc16Xmodem(...);

void printFrame(...);
```

Créer une structure :

```cpp
struct MCZFrame {
    uint32_t remoteId;
    uint8_t mode;
    uint8_t power;
    uint8_t fan1;
    uint8_t fan2;
    uint8_t user;
    uint8_t reserved;

    uint8_t raw[7];

    bool crcValid;
};
```

---

# 16. Critères de réussite du POC RX

Le POC RX sera considéré réussi si au moins un des deux objectifs suivants est atteint.

### Niveau 1

Le CC1101 détecte clairement des bursts RF cohérents à 434,50 MHz lors d’un appui télécommande.

### Niveau 2 — objectif principal

Le firmware affiche une trame de 7 octets avec :

```text
CRC OK
ID 24 bits stable
valeurs cohérentes mode/power/fan1/fan2
```

sur plusieurs commandes.

---

# 17. Critères de réussite du POC TX

Uniquement après succès RX.

Le POC TX sera considéré réussi si :

1. une trame capturée peut être rejouée ;
2. le poêle réagit exactement comme à la télécommande ;
3. aucune erreur ou alarme n’apparaît ;
4. l’arrêt est effectué par commande MCZ normale, jamais par coupure électrique.

---

# 18. Sources techniques à étudier

## Documentation MCZ — Musa Comfort Air / Active System

### Manuel MCZ — référence 8901166500

Famille :

```text
Suite / Club / Musa / Nima / Toba
Air / Comfort Air
Active System
```

PDF :

https://solarnet-online.com/wp-content/uploads/2017/03/Musa-comfort-air-Manual.pdf

Copie / consultation :

https://manualzz.com/doc/5074331/mcz-suite-air--comfort-air--club-air--comfort-air--musa-a...

La documentation confirme notamment :

- télécommande 434,5 MHz ;
- fonctionnement du tableau d’urgence ;
- procédure d’association ;
- modèles Musa Comfort Air.

---

## Projet historique — reverse engineering du protocole MCZ

### KerberRF/APPLI_MCZ

https://github.com/KerberRF/APPLI_MCZ

Fichiers particulièrement importants :

```text
MCZ explains.txt
src/Appli_Emit.c
src/Appli_Cmd_Mcz.c
src/manchester.c
src/manchester.h
```

Ce dépôt contient :

- structure des 7 octets ;
- ID 24 bits ;
- fan1 ;
- fan2 ;
- puissance ;
- mode ;
- CRC16 ;
- encapsulation 12 bits ;
- Manchester ;
- timings ;
- répétition des trames.

C’est probablement la référence principale à utiliser pour comprendre le protocole.

---

## Portage ESP32

### sfauvart/esp32-s2-mcz

https://github.com/sfauvart/esp32-s2-mcz

README :

https://github.com/sfauvart/esp32-s2-mcz/blob/main/README.md

Driver :

https://github.com/sfauvart/esp32-s2-mcz/blob/main/components/mcz_rf_driver/mcz_rf_driver.cpp

Ce projet :

- utilise un ESP32-S2 ;
- génère directement des commandes MCZ ;
- implémente CRC, Manchester et timing ;
- a été utilisé sur un MCZ EGO 2.0 Air ;
- repose lui-même sur `KerberRF/APPLI_MCZ`.

Le projet utilise un émetteur RF simple.  
Pour notre POC, préférer le CC1101 disponible.

---

## Projet récent — MCZ Musa + ESP32 + CC1101

### mylifeos/mcz-musa-esphome-home-assistant

https://github.com/mylifeos/mcz-musa-esphome-home-assistant

README :

https://github.com/mylifeos/mcz-musa-esphome-home-assistant/blob/main/README.md

RX :

https://github.com/mylifeos/mcz-musa-esphome-home-assistant/blob/main/mcz-receiver.yaml

RX/TX :

https://github.com/mylifeos/mcz-musa-esphome-home-assistant/blob/main/mcz-remote.yaml

Ce projet est particulièrement important car il utilise :

```text
MCZ Musa 2.0 Air
ESP32-C6
CC1101
434,50 MHz
ASK/OOK
```

Il contient également un décodeur de trames RF.

Le projet indique qu’ON/OFF ont été confirmés sur le poêle réel.

Attention : ce n’est pas exactement la même génération de Musa que notre Musa Comfort Air 2011–2013.  
Il faut donc valider passivement le protocole avant toute émission.

---

## RFXCOM

RFXCOM documente le protocole :

```text
Thermostat4
MCZ 1 fan
MCZ 2 fans
MCZ 3 fans
```

Le modèle `MCZ 2 fans` est particulièrement pertinent pour notre Musa Comfort Air.

Chercher :

```text
RFXtrx User Guide
Thermostat4
MCZ pellet stove 2 fans
```

Projet Node RFXCOM :

https://github.com/rfxcom/node-rfxcom

Fichier intéressant :

https://github.com/rfxcom/node-rfxcom/blob/master/lib/thermostat4.js

Autres implémentations utiles :

https://github.com/domoticz/domoticz

https://github.com/Yadoms/yadoms

Chercher dans ces dépôts :

```text
pTypeThermostat4
sTypeMCZ2
fan1_speed
fan2_speed
flame_power
```

Ces sources peuvent être utilisées pour recouper la représentation logique des paramètres.

---

## CC1101 / ESPHome

Documentation CC1101 ESPHome :

https://esphome.io/components/cc1101/

À consulter pour :

- initialisation CC1101 ;
- fréquence ;
- ASK/OOK ;
- mode raw ;
- configuration des GPIO ;
- émission/réception.

---

# 19. Points à vérifier par l’agent avant de coder

Avant de reprendre aveuglément une implémentation existante :

1. vérifier le modèle exact d’ESP32 disponible ;
2. choisir les GPIO SPI compatibles ;
3. confirmer le brochage du module CC1101 ;
4. ne jamais alimenter le CC1101 en 5 V ;
5. confirmer que la librairie CC1101 choisie permet le mode raw ASK/OOK ;
6. vérifier le comportement de GDO0/GDO2 en RX ;
7. utiliser un timer matériel / interruption pour mesurer précisément les impulsions ;
8. éviter que les logs série perturbent les timings ISR ;
9. stocker les impulsions dans un buffer puis les analyser hors interruption ;
10. commencer par RX uniquement.

---

# 20. Priorité de développement

Ordre imposé :

```text
1. CC1101 détecté
2. fréquence 434,50 MHz
3. RX brut
4. capture télécommande
5. timing Manchester
6. reconstruire 7 octets
7. CRC valide
8. décoder ID/mode/power/fans
9. enregistrer plusieurs vraies trames
10. seulement ensuite TX
11. rejeu exact d’une trame
12. génération dynamique de trames
13. éventuellement appairage nouvel ID
```

Ne pas commencer par construire une interface mobile, Home Assistant, MQTT ou une API.

Le but de ce POC est uniquement de répondre à cette question :

> **Un ESP32 + CC1101 peut-il se comporter comme la télécommande 434,5 MHz de ce MCZ Musa Comfort Air ?**

---

# 21. Mission à donner à Codex

Analyser en profondeur les sources ci-dessus avant d’écrire le code.

Priorité :

1. `KerberRF/APPLI_MCZ`
2. `sfauvart/esp32-s2-mcz`
3. `mylifeos/mcz-musa-esphome-home-assistant`
4. `rfxcom/node-rfxcom`
5. documentation MCZ 8901166500

Comparer les implémentations et relever toute divergence concernant :

- CRC ;
- fréquence ;
- timings ;
- Manchester ;
- format des 12 bits ;
- répétition des trames ;
- valeurs des ventilateurs ;
- signification de `user` ;
- bits réservés ;
- configuration CC1101.

Ne pas masquer les incertitudes.

Avant toute émission RF, produire un rapport court indiquant :

```text
- protocole confirmé / non confirmé
- nombre de trames RX valides
- ID observé
- CRC validé
- valeurs observées
- différences éventuelles avec les projets GitHub
```

L’émission ne doit être ajoutée qu’après validation explicite de la phase RX.
