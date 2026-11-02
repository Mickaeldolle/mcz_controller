# Allumer et éteindre le MCZ Musa : bilan des blocages

État du 2 novembre 2026. À lire avec le
[guide de mise en service](MISE_EN_SERVICE_ALLUMAGE_EXTINCTION.md).

## 1. Analyse et conclusion

**Le projet dispose déjà d'une chaîne logicielle capable de demander une
émission ON/OFF. Aucun manque fondamental de format de trame n'est identifié
pour un premier essai. En revanche, l'allumage et l'arrêt du poêle par notre
émetteur ne sont pas encore démontrés de bout en bout.**

**Situation terrain confirmée par l'utilisateur : le poêle ne répond pas à la
télécommande d'origine, alors que ses émissions sont bien décodées par notre
ESP32. Le contrôle radio d'origine est donc déjà en échec.** La priorité est
de distinguer une association perdue, un état bloquant du poêle, un défaut du
chemin de réception et une émission d'origine dégradée mais encore décodable
par notre récepteur. Aucune de ces causes n'est encore établie.

Les captures réelles établissent que la télécommande émet et que notre ESP32
les décode. Elles ne prouvent ni que notre CC1101 émet correctement, ni que
le récepteur du poêle reçoit notre montage, ni que l'identifiant est encore
accepté par le poêle.

La recommandation est de conserver le montage ESP32 + CC1101 et l'application
USB locale, en donnant d'abord la priorité au diagnostic du contrôle du poêle.
Un essai ESP32 restera utile pour comparer un autre émetteur, sans présumer
qu'il résoudra la panne. Il devra reproduire les dernières commandes manuelles
capturées : **ON, puissance 1, ventilation 1 à 2**, puis l'arrêt correspondant.
Une migration ESPHome ou Home Assistant ne lève pas à elle seule cette incertitude.

Ce document propose des actions ; sa rédaction n'a ni changé les profils
actifs, ni reflashé la carte, ni envoyé de commande radio.

## 2. Ce qui existe déjà

```mermaid
flowchart LR
    A[Page locale ON / OFF] --> B[Serveur Python]
    B --> C[USB et requête identifiée]
    C --> D[CRC et ID vérifiés]
    D --> E[Encodage Manchester RMT]
    E --> F[CC1101 en émission]
    F --> G[Récepteur du poêle]
    G --> H[Réaction physique]
```

Les étapes jusqu'à la préparation du signal ont des preuves de code et de
tests locaux. Les deux dernières étapes exigent une observation physique.

| Composant | Preuve disponible | Limite |
|---|---|---|
| Trames propres à notre télécommande | ID C8CC02 ; captures ON/OFF et puissance manuelle 1 à 5 | Pas un accusé du poêle |
| Réception CC1101 → ESP32 | 35 trames ventilation et 50 trames manuelles récentes, CRC contrôlés | Ne qualifie pas l'étage TX |
| Encodeur | 7 octets, encapsulation 12 bits, parité, Manchester, cinq répétitions | La sortie électrique et RF reste à mesurer |
| Pilote TX | STX, entrée de données GDO0, PATABLE OOK, attente de fin RMT, retour RX | Pas encore de preuve RF de notre émission |
| Application locale | Actions on/off, anti-doublon, délai entre commandes, absence de relance après erreur | « Envoyée » n'est pas « reçue par le poêle » |
| Carte accessible en USB | Statuts réels antérieurs : ready=true, fréquence 434500000, compteur TX=0 | Statuts ponctuels, compteur remis à zéro au démarrage |

## 3. Comparaison des trois projets demandés

Les comparaisons portent sur les copies locales et les révisions ci-dessous,
pas sur un suivi de leur branche distante actuelle.

| Projet | Montage et stratégie | Ce que nous retenons | Ce qu'il ne valide pas pour nous |
|---|---|---|---|
| [mcz-musa-esphome-home-assistant](../research/mcz-musa-esphome-home-assistant/README.md) | XIAO ESP32-C6, CC1101 TX à 434,50 MHz, RMT ; RXB12 séparé pour RX | Rejouer ses propres trames complètes ; cinq répétitions ; auteur déclarant une confirmation ON/OFF sur l'afficheur d'un MUSA 2.0 AIR | Notre ancien Musa, notre carte, notre pilote CC1101 et notre portée |
| [esp32-s2-mcz](../research/esp32-s2-mcz/README.md) | ESP32-S2 Mini + FS1000A, GPIO temporisé ; auteur utilisant un EGO 2.0 Air | Structure des champs, encapsulation, 414 µs, préfixe 103 ms, cinq répétitions ; adaptation d'APPLI_MCZ | Un FS1000A n'est pas un CC1101 : sa configuration RF et son alimentation ne se transposent pas |
| [APPLI_MCZ](../research/APPLI_MCZ/README.md) | Raspberry Pi, wiringPi, sortie GPIO vers émetteur | Base historique de l'encapsulation, du CRC et de Manchester | Les délais GPIO Linux, la radio et les broches du Raspberry Pi ne valident pas l'ESP32 |

Révisions relues :

```text
mcz-musa-esphome-home-assistant : cc8d07ae5b46f06a549a92f1a203ef965424050c
esp32-s2-mcz                   : a7933043a11a2984a114f9644365f35a24b516ea
APPLI_MCZ                      : 9e40d5b78ca106b9dbddf0c227b899ccd6cb30be
```

Le premier projet confirme ON/OFF selon son auteur, mais livre des trames ON/OFF
remplies de zéros et un verrou d'envoi désactivé par défaut : ses fichiers ne
peuvent pas être flashés tels quels pour piloter notre poêle. Nous possédons
déjà les captures qui manquent dans ces exemples.

Les chemins de code déterminants sont
[le bloc CC1101 et TX du projet Musa](../research/mcz-musa-esphome-home-assistant/mcz-remote.yaml),
[l'encodeur du projet S2](../research/esp32-s2-mcz/components/mcz_rf_driver/mcz_rf_driver.cpp),
[Manchester dans APPLI_MCZ](../research/APPLI_MCZ/src/manchester.c) et
[ses constantes de temps](../research/APPLI_MCZ/src/manchester.h).

### Comparaison des paramètres d'émission

| Paramètre | Notre projet | Projet Musa ESPHome | ESP32-S2 / APPLI_MCZ |
|---|---|---|---|
| Identifiant | C8CC02 capturé | À renseigner avec sa télécommande | À fournir/configurer |
| Génération du signal | RMT ESP32 classique, 1 µs | RMT sur ESP32-C6 | GPIO temporisé |
| Demi-bit nominal | 414 µs | 414 µs | S2 : 414 µs ; APPLI : 393 µs actifs pour compensation de latence |
| Séparateur par octet | LOW 414 + HIGH 828 µs | Identique | Bit Manchester 0 puis attente d'un demi-bit : même intention de forme |
| Préfixe et pause | HIGH 103000 µs ; LOW 3712 µs | Identiques | Identiques dans les constantes |
| Répétitions | 5 | 5 | 5 |
| Radio | CC1101 asynchrone, OOK | CC1101, packet_mode=false, Manchester matériel désactivé | S2 : FS1000A ; APPLI : GPIO vers émetteur |
| Puissance RF configurée | Environ 0 dBm nominal, non mesuré | `output_power: 10` | Autre matériel, pas de valeur comparable établie ici |

**Aucune divergence de structure ne suffit ici à expliquer un échec certain.**
La différence de puissance RF peut affecter la portée ; ce n'est pas la preuve
d'une panne et elle ne justifie pas une augmentation automatique. La valeur
393 µs d'APPLI_MCZ compense ses appels GPIO ; elle ne doit pas remplacer nos
414 µs matériellement cadencés sans mesure.

## 4. Blocages, risques et décisions à prendre

| Réf. | Point | Nature et impact | Comment le lever |
|---|---|---|---|
| B01 | Réaction physique aux commandes ESP32 non démontrée | Blocage de qualification fonctionnelle | Un essai supervisé ON puis OFF, observation de l'afficheur/cycle, preuve consignée |
| B02 | Profils actifs différents du scénario manuel retenu | Écart réel de configuration ; ne bloque pas toute émission mais bloque un essai manuel maîtrisé | Choisir explicitement les trames manuelles capturées et vérifier leurs CRC/provenance avant utilisation |
| B03 | Tests de provenance liés au format historique et aux anciens profils | Adaptation logicielle nécessaire si B02 est appliqué | Accepter les nouveaux journaux live et mettre à jour les attentes fixes ; détail dans le guide |
| B04 | Sortie TX électrique/RF non caractérisée | Inconnue matérielle ; RX et compilation ne suffisent pas | Si l'essai physique échoue, comparer la sortie et le signal reçu par un récepteur indépendant |
| B05 | Poêle sans réaction à la télécommande d'origine malgré des trames reçues par l'ESP32 | Échec du contrôle d'origine confirmé par l'utilisateur ; cause non isolée, priorité de diagnostic | Vérifier commande locale, REMOTE, alarmes, puis procédure d'association exacte et chemin RF ; ne pas conclure directement à un récepteur défectueux |
| B06 | Pas d'accusé d'exécution du poêle dans notre système | Limite de supervision, pas un obstacle au premier essai présentiel | Observer le poêle ; ajouter plus tard une mesure indépendante si nécessaire |
| B07 | Possibilité de commandes concurrentes depuis la télécommande | Risque d'écrasement des réglages ou de confusion | Après le contrôle de référence, poser la télécommande sans l'actionner ; pour un essai manuel isolé, retirer temporairement ses piles si nécessaire |
| B08 | Un seul propriétaire de COM3 | Contrainte opérationnelle vérifiée | Arrêter moniteur/capture avant le serveur et réciproquement |
| B09 | Version exacte du firmware installé non attestée par le seul statut `j` | Limite de traçabilité | Associer la qualification à un binaire archivé ; réinstaller ce binaire si l'installation est incertaine |

### B02 : les trames sont déjà disponibles, mais ne sont pas interchangeables

| Profil | ON | OFF | Réglages d'allumage |
|---|---|---|---|
| Actif aujourd'hui | C8 CC 02 8F B8 8E 16 | C8 CC 02 8C B8 DB 45 | Mode 3, puissance 3, ventilation 1 à 4 |
| Recommandé pour le premier essai manuel | C8 CC 02 45 B8 77 89 | C8 CC 02 44 B8 44 B8 | Mode 1, puissance 1, ventilation 1 à 2 |

Le champ ventilation 2 reste à 7 et les bits historiques « user » à 2 dans
les deux cas. Leur signification complète reste à qualifier, mais il n'est
pas nécessaire de les réinventer pour rejouer exactement une capture réelle.

L'adoption des nouvelles trames ne nécessite pas de changer l'encodeur ou de
reflasher la carte : elles gardent le même format, le même CRC et le même ID.
Elle nécessite un redémarrage du serveur, qui charge les profils au lancement.

### B04 : séparer logiciel, broche et onde radio

Notre code prévoit de mettre GDO0 en haute impédance côté CC1101 avant de le
piloter depuis l'ESP32, puis de rendre l'ESP32 en entrée avant restauration RX.
Le chemin est cohérent avec la [fiche TI, §27.1](https://www.ti.com/lit/ds/symlink/cc1101.pdf#page=63),
qui utilise GDO0 comme entrée de données TX en mode asynchrone.

La configuration OOK utilise deux entrées PATABLE : niveau éteint à l'indice 0,
niveau actif à l'indice 1. Le code écrit `00` et `60`, avec FREND0=`11`.
Cette organisation suit [TI, §24 et tableau des puissances](https://www.ti.com/lit/ds/symlink/cc1101.pdf#page=59).
Le réglage nominal n'est pas une mesure de puissance rayonnée.

Le [RMT d'Espressif](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/peripherals/rmt.html)
génère les niveaux et durées ; son achèvement ne démontre pas l'émission RF.
Un analyseur logique sur GPIO27 démontre la sortie numérique, pas l'onde radio.
Un second récepteur ou un SDR qualifié permet de vérifier le signal émis.
Le même CC1101, commuté en TX, ne peut pas servir simultanément de témoin RX.

### B05 : ne pas confondre émission de la télécommande et association

L'utilisateur confirme explicitement que le poêle ne répond pas à la
télécommande d'origine. Les captures récentes montrent une émission cohérente
et un CRC correct sur notre ESP32. Cette confirmation remplace l'hypothèse
antérieure d'une réaction physique encore non renseignée.

Un CRC valide sur notre récepteur n'exclut pas un écart de fréquence, une portée
réduite ou une dégradation RF que le récepteur du poêle tolère moins bien. Une
association perdue, une mauvaise position du sélecteur, une alarme ou un défaut
de réception restent également des pistes, pas des diagnostics acquis.

Le premier résultat discriminant est le fonctionnement depuis les commandes
locales du poêle. Si elles ne fonctionnent pas non plus, ne pas réduire la panne
à la radio : vérifier l'état du poêle et faire intervenir son mainteneur si
nécessaire. Si elles fonctionnent, le diagnostic peut se concentrer sur le
chemin de commande distant. L'appairage doit être essayé selon la notice exacte,
avec observation de sa confirmation, avant de conclure à une panne du récepteur.

Il n'est pas établi qu'un nouvel appairage soit nécessaire. Nous réutilisons
l'ID d'origine ; il faut d'abord tester cet ID avant d'en changer ou de
modifier l'association. Aucun appui long capturé jusqu'ici n'a été effectué
avec le poêle confirmé en mode « --- » ; aucune trame d'appairage spécifique
n'est identifiée.

## 5. Contrôles réalisés pour ce bilan

- Comparaison des trois copies locales aux révisions indiquées.
- Compilation PlatformIO : réussite, RAM 26 520 octets, Flash 300 041 octets.
- Suite Python finale : 24 réussis, 1 test optionnel ignoré sur Windows.
- C++ sous WSL : trois suites réussies avec AddressSanitizer/UndefinedBehaviorSanitizer.
  Trois tests d'outils réussis, dont le lecteur C++ ignoré sous Windows.
- Procédure du guide reproduite dans une copie temporaire : profils manuels,
  nouveau journal de provenance et adaptations de tests proposés ; 24 tests
  réussis, un test optionnel ignoré. Le JSON actif est resté identique octet par octet.
- Vérification C++ complémentaire des six trames manuelles capturées : chacune
  est encodée puis redécodée en cinq répétitions identiques, durée nominale
  512790 µs ; maximum calculé de 343 éléments RMT sur les 512 disponibles.
  Ce contrôle de données ne simule pas le pilote matériel RMT ni la radio.
- Une première exécution Python a subi une interruption HTTP locale Windows
  `WinError 10053` ; le contrôle ciblé des 13 tests d'application, puis la suite
  complète, ont réussi. L'origine de cette interruption isolée n'est pas établie.
  Aucun assouplissement des protections HTTP n'a été effectué.

Ces contrôles sont hors émission RF. Ils ne qualifient pas B01, B04 ou B05.
Les résultats de capture détaillés sont dans
[l'analyse manuelle](ANALYSE_MANUEL_20261102_215528.md) et
[l'analyse de ventilation](ANALYSE_SEQUENCE_20261102_214116.md).

## 6. Recommandation, sécurité et alternatives

Ordre recommandé : établir le fonctionnement des commandes locales et l'état
REMOTE/alarmes ; vérifier l'association selon la notice exacte ; puis, si
nécessaire, comparer la chaîne RF avec un essai ESP32 maîtrisé. Le choix du
profil manuel et l'adaptation des tests préparent cet essai, mais ne réparent
pas un récepteur du poêle défaillant. Un échec commun des deux émetteurs n'en
constitue pas non plus une preuve suffisante sans contrôler notre propre TX.

Ne pas recopier l'alimentation 5 V du FS1000A sur le CC1101 : notre module reste
alimenté en 3,3 V. Ne pas remplacer les sécurités du poêle ni couper son courant
pour effectuer un arrêt normal. La prise connectée citée dans le projet S2
peut fournir un indice de consommation ; sa coupure n'est pas notre méthode
d'extinction. Le cycle de refroidissement doit rester piloté par le poêle.

ESPHome constitue une alternative ultérieure pour une intégration domotique,
pas une condition d'allumage. Un récepteur séparé est utile pour diagnostiquer
le TX ; il n'est pas obligatoire si le poêle accepte et confirme directement
les commandes. L'automatisation sans surveillance attendra une qualification
répétable et un moyen crédible de constater les échecs.
