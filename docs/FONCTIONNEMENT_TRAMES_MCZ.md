# Fonctionnement des trames radio MCZ Musa

Version du 2 novembre 2026 — ESP32 classique + CC1101, télécommande ID `C8CC02`.

Cette documentation décrit le format utilisé par ce projet et le relie aux
appuis réellement capturés. Elle ne constitue pas une spécification officielle
de toutes les générations MCZ : les appareils Maestro, Bluetooth ou Wi-Fi ne
doivent pas être supposés compatibles.

## 1. Le principe : envoyer les réglages demandés

La télécommande transmet une trame de **7 octets**, répétée **5 fois** lors des
appuis observés. Un octet contient 8 bits ; les valeurs sont écrites ici en
hexadécimal, avec deux caractères par octet.

Exemple réel :

```text
C8 CC 02 4D B8 FE 20
```

Cette trame demande le mode manuel, une puissance de chauffe de 3 et une
ventilation 1 de 2. Elle ne signifie pas « l'utilisateur a appuyé sur + ».
Le même niveau de puissance produit la même trame, qu'on l'atteigne en
augmentant ou en diminuant.

Il faut distinguer trois niveaux :

```mermaid
flowchart LR
    A[Appui sur la télécommande] --> B[Configuration demandée]
    B --> C[Trame de 7 octets et CRC]
    C --> D[Encodage Manchester et 5 répétitions]
    D --> E[Réception et décodage ESP32]
    E --> F[Affichage dans le terminal]
```

Ce schéma représente notre observation du signal. L'affichage d'une trame
ne constitue pas un accusé de réception du poêle et ne mesure pas son état réel.

## 2. Organisation des sept octets

Les positions 1 à 7 ci-dessous correspondent aux indices 0 à 6 dans le code.
Dans un octet, le bit 7 est le plus significatif et le bit 0 le moins significatif.

| Position | Indice dans le code | Contenu | Exemple |
|---|---|---|---|
| 1 | `raw[0]` | Identifiant, bits 23 à 16 | `C8` |
| 2 | `raw[1]` | Identifiant, bits 15 à 8 | `CC` |
| 3 | `raw[2]` | Identifiant, bits 7 à 0 | `02` |
| 4 | `raw[3]` | Ventilation 1, puissance et mode | `4D` |
| 5 | `raw[4]` | Champ historique « user », ventilation 2, bits réservés | `B8` |
| 6 | `raw[5]` | CRC, octet de poids fort | `FE` |
| 7 | `raw[6]` | CRC, octet de poids faible | `20` |

L'identifiant est reconstruit dans l'ordre des octets transmis :

```text
ID = (raw[0] << 16) | (raw[1] << 8) | raw[2]
C8 CC 02 → 0xC8CC02
```

Cet identifiant est stable dans les essais étudiés. Il distingue la télécommande
dans le protocole ; il n'est ni une clé de chiffrement ni une preuve d'identité
cryptographique. Le firmware TX actuel est limité à cet identifiant précis.

## 3. Quatrième octet : mode, puissance et ventilation 1

```text
Numéro du bit :     7  6  5 | 4  3  2 | 1  0
Champ :            ventil.1| puissance| mode
Nombre de bits :      3    |    3    |   2
```

Les formules utilisées par le décodeur sont :

```text
mode       = raw[3] & 0x03
puissance  = (raw[3] >> 2) & 0x07
ventilation1 = (raw[3] >> 5) & 0x07

raw[3] = (ventilation1 << 5) | (puissance << 2) | mode
```

### Modes

| Valeur | Interprétation | Niveau de preuve dans ce projet |
|---:|---|---|
| 0 | Arrêt demandé | Confirmé par les appuis OFF capturés |
| 1 | Fonctionnement manuel | Confirmé par l'essai explicitement réalisé en manuel |
| 2 | Automatique | Décrit par les sources étudiées ; pas d'essai dédié confirmé ici |
| 3 | ECO selon les sources | Valeur réellement reçue hors mode manuel ; comportement ECO non qualifié par ces captures |

Le mode 1 ne signifie donc pas « toute forme d'allumage ». Un appui ON peut
envoyer le mode 1 ou 3 suivant le mode choisi sur la télécommande.

### Puissance et ventilation

Chaque champ de 3 bits peut représenter 0 à 7, mais toutes ces valeurs ne sont
pas nécessairement des réglages utilisables sur l'appareil.

- Les puissances **1 à 5** ont été confirmées par quatre appuis + puis quatre −.
- Les valeurs de ventilation 1 **2, 3, 4 et 5** ont été recoupées avec les essais.
- Les sources décrivent des ventilations 0 à 5 et une valeur 6 pour automatique.
  Les fonctions 0 et 6 ne sont pas qualifiées par les séquences récentes.
- La valeur 7 ne doit pas recevoir une signification inventée.

Une hausse de puissance ajoute `0x04` au quatrième octet lorsque les autres
champs restent fixes. Une hausse de ventilation 1 ajoute `0x20`. Il faut
toujours décoder les champs : un XOR peut affecter plusieurs bits lors d'une
retenue binaire, même quand le réglage augmente seulement d'une unité.

### Exemple détaillé : `4D`

```text
4D en binaire : 010 011 01
                │   │  └─ mode 1 : manuel
                │   └──── puissance 3
                └──────── ventilation 1 à 2

4D = (2 << 5) | (3 << 2) | 1
   = 0x40     | 0x0C     | 0x01
```

## 4. Cinquième octet : ce qui est décodé et ce qui reste inconnu

```text
Numéro du bit :     7  6 | 5  4  3 | 2  1  0
Champ :            user | ventil.2 | réservé
```

```text
user         = raw[4] >> 6
ventilation2 = (raw[4] >> 3) & 0x07
reserve      = raw[4] & 0x07
```

Pour `B8` :

```text
B8 en binaire : 10 111 000
                │  │   └─ réservé = 0
                │  └───── ventilation 2 = 7
                └──────── user = 2
```

**Le nom « user » est hérité des sources ; sa fonction n'est pas démontrée.**
Il ne faut pas l'assimiler à un compte utilisateur, à l'appairage ou à un
paramètre de sécurité.

Les essais de puissance et de ventilation gardent `B8`. Une autre émission,
reçue sans nouvel appui environ une minute après un appui long, contenait `38` :
les deux bits supérieurs passent alors de 2 à 0, sans changement de ventilation 2
ni des bits réservés. La fonction de cette variation reste inconnue.

La présence de ventilation 2=7 ne prouve ni un ventilateur absent ni une vitesse
physique 7. Les bits réservés observés à zéro ne sont pas nécessairement inutilisés
par toutes les variantes du protocole. Conserver leurs valeurs capturées.

## 5. Captures réelles en mode manuel

Source : [journal du 2 novembre à 21:55](../captures/20261102-215528-553832_live.log).
Conditions : mode manuel confirmé par l'utilisateur, ventilation 1 à 2,
cinquième octet `B8`. Chaque ligne du tableau a été reçue cinq fois par appui.

| Réglage demandé | Trame complète | Quatrième octet |
|---|---|---|
| Manuel, puissance 1 | `C8 CC 02 45 B8 77 89` | `45` |
| Manuel, puissance 2 | `C8 CC 02 49 B8 32 E4` | `49` |
| Manuel, puissance 3 | `C8 CC 02 4D B8 FE 20` | `4D` |
| Manuel, puissance 4 | `C8 CC 02 51 B8 B8 3E` | `51` |
| Manuel, puissance 5 | `C8 CC 02 55 B8 74 FA` | `55` |
| Arrêt, puissance conservée à 1 | `C8 CC 02 44 B8 44 B8` | `44` |

La séquence complète observée est :

```text
ON   +   +   +   +   −   −   −   −   OFF
 1 → 2 → 3 → 4 → 5 → 4 → 3 → 2 → 1 → arrêt
```

Le retour au niveau 1 produit exactement la même trame que l'allumage initial.
L'arrêt change ici uniquement le mode de 1 à 0 dans les paramètres ; les deux
octets du CRC changent aussi puisque les données protégées ont changé.

## 6. Captures réelles de ventilation et profils de l'application

Source : [journal du 2 novembre à 21:41](../captures/20261102-214116-378436_live.log).
Puissance de chauffe à 3, mode reçu à 3 pour les commandes actives.

| Réglage demandé | Trame complète |
|---|---|
| Mode 3, ventilation 1 à 4 | `C8 CC 02 8F B8 8E 16` |
| Mode 3, ventilation 1 à 5 | `C8 CC 02 AF B8 88 F0` |
| Mode 3, ventilation 1 à 3 | `C8 CC 02 6F B8 9E A4` |
| Mode 3, ventilation 1 à 2 | `C8 CC 02 4F B8 98 42` |
| Arrêt, puissance 3 et ventilation 1 à 4 conservées | `C8 CC 02 8C B8 DB 45` |

Le premier appui ventilation − après le niveau 5 revient à `8F`, donc à la
même trame que l'appui ON de cette séquence. Cela montre pourquoi le terminal
ne peut pas déduire le bouton physique à partir de la seule trame.

Au moment de la rédaction, [les profils de l'application](../config/power_profiles.json)
rejouent `C8 CC 02 8F B8 8E 16` pour Allumer et `C8 CC 02 8C B8 DB 45` pour
Éteindre. Allumer demande donc aussi **mode 3, puissance 3, ventilation 1 à 4**.
Il ne reprend pas automatiquement les derniers réglages manuels de la télécommande.
Les captures manuelles n'ont pas remplacé ces profils.

## 7. CRC : vérifier l'intégrité des données

Le CRC protège les **cinq premiers octets** : l'identifiant et les deux octets
de paramètres. Les deux derniers octets transportent le résultat, poids fort
puis poids faible.

| Paramètre | Valeur |
|---|---|
| Variante | CRC-16/XMODEM |
| Largeur | 16 bits |
| Polynôme | `0x1021` |
| Valeur initiale | `0x0000` |
| Réflexion entrée / sortie | Non / non |
| XOR final | `0x0000` |
| Ordre des octets du résultat | Poids fort, puis poids faible |
| Vecteur de contrôle ASCII `123456789` | `0x31C3` |

Exemple : le CRC de `C8 CC 02 4D B8` est `FE20` ; la trame se termine donc
par `FE 20`. Pour une comparaison, il faut recalculer le CRC après un changement
de paramètre : ses variations ne représentent pas de nouveaux réglages.

Un CRC correct établit une cohérence selon cet algorithme. Il ne garantit ni
l'authenticité de l'émetteur, ni la conformité de tous les réglages au modèle,
ni la réception de la commande par le poêle.

### Exemple Python complet : décoder sans matériel

Ce programme n'ouvre aucun port série et n'émet aucun signal.

```python
import binascii
import json


def decode_frame(value: str) -> dict[str, int | str]:
    raw = bytes.fromhex(value)
    if len(raw) != 7:
        raise ValueError("Une trame MCZ doit contenir exactement sept octets")
    received_crc = int.from_bytes(raw[5:7], "big")
    expected_crc = binascii.crc_hqx(raw[:5], 0)
    if received_crc != expected_crc:
        raise ValueError(f"CRC invalide : {received_crc:04X}, attendu {expected_crc:04X}")
    return {
        "id": raw[:3].hex().upper(),
        "mode": raw[3] & 3,
        "puissance": (raw[3] >> 2) & 7,
        "ventilation1": raw[3] >> 5,
        "ventilation2": (raw[4] >> 3) & 7,
        "user": raw[4] >> 6,
        "reserve": raw[4] & 7,
        "crc": f"{received_crc:04X}",
    }


if __name__ == "__main__":
    print(json.dumps(decode_frame("C8 CC 02 4D B8 FE 20"), indent=2))
```

Le résultat est ID `C8CC02`, mode 1, puissance 3, ventilation 1 à 2,
ventilation 2 à 7, user 2, réservé 0 et CRC `FE20`.

## 8. Des octets au signal radio

La radio utilisée par ce projet est réglée sur **434,50 MHz**, modulation
**ASK/OOK**. Le CC1101 fonctionne en série asynchrone : le firmware réalise
l'encodage Manchester et le contrôle du CRC, au lieu de déléguer ces fonctions
au moteur de paquets de la radio.

### Un octet devient un mot de 12 bits

Avant Manchester, chacun des sept octets est encapsulé ainsi :

```text
start | d7 d6 d5 d4 d3 d2 d1 d0 | premier | parite | stop
  1   |       8 bits MSB        | 1 bit   | 1 bit  |  1
```

- Les données sont transmises du bit de poids fort vers le bit de poids faible.
- Le drapeau `premier` vaut 1 pour l'octet d'indice 0, puis 0 pour les six autres.
- La parité est paire sur les huit bits de données, le drapeau et le bit de parité.
  Les bits start et stop ne participent pas à ce calcul.
- Start et stop valent tous deux 1 dans ce format. Ce n'est pas un octet UART
  8N1 classique, même si la liaison USB utilise séparément un port série.

Le firmware construit le mot avec :

```text
donnees9 = (octet << 1) | premier
parite   = XOR des 9 bits de donnees9
mot12    = 0x801 | (donnees9 << 2) | (parite << 1)
```

Pour le premier octet `C8`, le mot est `1 | 11001000 | 1 | 0 | 1`, soit `E45`.

### Manchester et séparateur par octet

Dans la convention de l'encodeur :

```text
bit 1 → HIGH puis LOW
bit 0 → LOW puis HIGH
```

Chaque demi-bit dure nominalement **414 µs**, donc un bit de données Manchester
dure 828 µs. Le décodeur essaie aussi la polarité inversée pour la réception.

Avant **chaque** mot de 12 bits, premier octet compris, un séparateur de trois
demi-bits est ajouté :

```text
LOW 414 µs | HIGH 828 µs
```

Les niveaux adjacents identiques se fusionnent naturellement. Des impulsions
de 828 ou 1242 µs peuvent donc représenter plusieurs demi-bits, sans être une
erreur d'encodage.

## 9. Répétitions et durées nominales

L'encodeur actuel applique la structure suivante, issue des sources étudiées :

```text
préfixe HIGH 103 ms
  → trame 1 → pause LOW
  → trame 2 → pause LOW
  → trame 3 → pause LOW
  → trame 4 → pause LOW
  → trame 5 → pause LOW
```

Chaque trame représente `7 × (3 + 12 × 2) = 189` demi-bits, séparateurs inclus.
L'encodeur ajoute ensuite une pause LOW nominale de 3712 µs. Cette pause peut
se fusionner avec le dernier demi-bit LOW du mot précédent dans le signal brut.

```text
Trame + pause = 189 × 414 + 3712 = 81 958 µs
Commande     = 103 000 + 5 × 81 958 = 512 790 µs
```

Ce sont les **durées nominales du modèle d'émission**, pas une mesure RF exacte
de chaque appui. Les journaux PC récents montrent 81 à 84 ms entre répétitions,
environ 82,35 ms en moyenne dans l'essai manuel. Ces horodatages incluent les
délais de décodage, de transport USB et de traitement sur le PC.

Cinq lignes RX correspondent donc ici à cinq répétitions d'une configuration,
et non à cinq appuis. Le décodeur accepte une seule trame valide pour le
diagnostic ; il n'attend pas les cinq répétitions pour l'afficher.

## 10. Température et appairage : limites des connaissances actuelles

### Pourquoi les appuis température peuvent rester silencieux dans le terminal

Dans le format décodé, aucun champ de température en °C n'a été identifié.
L'hypothèse de travail est que la télécommande garde la consigne et émet des
réglages de puissance calculés lors de sa régulation, éventuellement de manière
différée. Ce fonctionnement est cohérent avec le pilotage MCZ décrit dans le
[guide RFXCOM, section 10.21.1](https://rfxcom.com/WebRoot/StoreNL2/Shops/78165469/MediaGallery/Downloads/RFX_MQTT_User_Guide.pdf#page=40),
qui propose de comparer température souhaitée et mesurée pour piloter la puissance.
Cela ne démontre pas l'algorithme exact de notre télécommande.

L'émission sans nouvel appui observée environ une minute après un appui long
est compatible avec cette hypothèse, sans établir une période fixe. Les bits
encore mal compris pourraient également avoir une fonction non identifiée.

Une autre possibilité est qu'une émission existe mais soit ignorée par le
décodeur actuel. Il faut une capture brute dédiée, avec état initial, gestes
et temps d'attente documentés, pour distinguer ces cas.

### Un appui long n'établit pas l'existence d'une trame d'appairage

L'essai réalisé avec un appui ON/OFF de deux secondes a été fait **hors mode
appairage du poêle**, d'après la confirmation de l'utilisateur. Le premier
groupe reçu correspondait au profil ON déjà connu ; un second groupe différent
a été reçu environ une minute plus tard sans nouvel appui.

Aucune commande d'appairage distincte n'est identifiée à ce jour. On ne peut
pas non plus conclure qu'une commande normale suffit à l'apprentissage sans
réaliser l'essai approprié et observer la confirmation du poêle.

## 11. Lire les journaux et interpréter leurs limites

Le parcours de réception actuel est :

```text
CC1101 → GPIO27 → capture RMT → Manchester/start/stop/parité
       → reconstruction de 7 octets → CRC → ligne Raw: → moniteur PC
```

Le récepteur RMT utilise des durées de résolution 1 µs et termine un bloc après
une pause de 3 ms. La capture actuelle ne mesure donc pas intégralement le
préfixe long de 103 ms. La dernière pause ajoutée au bloc, notée
`idle_tail_min_us=3000`, est une **borne minimale**, pas sa durée exacte.

Les journaux ont deux fonctions différentes :

| Type de journal | Contenu | Ce qu'il ne prouve pas |
|---|---|---|
| `*_live.log` du moniteur | Heure PC, trames décodées valides, intervalles, statut USB | Absence d'autres signaux, timing RF exact, réception par le poêle |
| Capture brute `RX_BURST_BEGIN/END` | Durées signées HIGH/LOW et informations de capture | Capture exhaustive de toute activité radio : seuils, taille des blocs et erreurs restent à examiner |

Dans une capture brute, `+414` désigne HIGH pendant 414 µs et `-414` LOW pendant
414 µs. Le signe représente un niveau électrique, pas un bit de données direct.

Le moniteur utilise maintenant `perf_counter` pour les intervalles. Les premiers
journaux utilisant `monotonic` sous Python 3.11 Windows affichaient parfois
78/94 ms, à cause d'une résolution de 15,625 ms du compteur utilisé.

Les libellés doivent être lus avec prudence :

- `Allumer enregistre` : octets identiques au profil ON, sans identification du bouton.
- `autre trame` : trame à CRC valide qui ne correspond pas aux deux profils connus.
  Cela ne signifie ni trame incorrecte ni commande inconnue du poêle.
- `compteur TX=0` : aucun envoi compté par le firmware ESP32 depuis son démarrage ;
  ce n'est pas le nombre d'émissions de la télécommande. Le compteur est volatil.
- `RX PRET` / `STATE=0D` : récepteur configuré et disponible, pas état du poêle.

Pour afficher les trames, ouvrir `Ecouter-MCZ.cmd`, sans privilèges administrateur.
Fermer le moniteur avec Ctrl+C avant de lancer une autre application sur COM3.
L'ouverture USB peut redémarrer l'ESP32 ; le moniteur n'envoie que les demandes
de statut `j` et `s`, sans commande d'émission radio.

## 12. État des preuves et références

| Élément | Statut |
|---|---|
| Structure 7 octets, ID, parité et CRC | Implémentés ; cohérents avec les captures décodées |
| Mode manuel=1, arrêt=0, puissances 1 à 5 | Recoupés avec la séquence manuelle déclarée par l'utilisateur |
| Variations de ventilation 1 de 2 à 5 | Recoupées avec les appuis et trames observés |
| Cinq répétitions par appui dans les deux séquences récentes | 85 trames valides, soit 17 groupes de cinq |
| Mode 2 et signification opérationnelle de mode 3 | Noms issus des sources ; qualification fonctionnelle dédiée à compléter |
| Ventilation 2=7, champ user et bits réservés | Valeurs observables, interprétation fonctionnelle incomplète |
| Consigne de température et régulation | Hypothèse à qualifier par capture dédiée |
| Appairage | Aucune trame spécifique identifiée ; essai en mode appairage non établi |
| Exécution par le poêle des émissions ESP32 | À vérifier séparément ; ni CRC ni log USB ne sont des accusés de réception |

### Captures et analyses du projet

- [Séquence de puissance manuelle](ANALYSE_MANUEL_20261102_215528.md) : 50 trames.
- [Séquence ON/OFF et ventilation](ANALYSE_SEQUENCE_20261102_214116.md) : 35 trames.
- [Appui long hors appairage](CAPTURE_APPUI_LONG_2026-11-02.md) : deux groupes de cinq.
- [Analyse initiale des sources](ANALYSE_PROTOCOLE.md) : références et révisions des dépôts.
  Les passages RX uniquement de ce document décrivent l'état historique du projet.

### Correspondance avec le code

- [Décodage et extraction des champs](../src/mcz_decoder.cpp).
- [Calcul CRC XMODEM](../src/mcz_crc.cpp).
- [Encodage des mots, Manchester et répétitions](../src/mcz_encoder.cpp).
- [Acquisition RMT et commande USB](../src/main.cpp).
- [Pilote CC1101](../src/cc1101_radio.cpp).
- [Affichage et horodatage du moniteur](../tools/monitor_serial.py).

Les implémentations [KerberRF/APPLI_MCZ](https://github.com/KerberRF/APPLI_MCZ),
[sfauvart/esp32-s2-mcz](https://github.com/sfauvart/esp32-s2-mcz) et
[mylifeos/mcz-musa-esphome-home-assistant](https://github.com/mylifeos/mcz-musa-esphome-home-assistant)
ont servi à l'étude du protocole. Leurs affirmations sont distinguées ici des
mesures sur notre exemplaire ; des projets dérivés ne sont pas des preuves
indépendantes supplémentaires.
