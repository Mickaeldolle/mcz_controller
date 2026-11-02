# Séquence ON/OFF et ventilation du 2 novembre 2026

Source : `captures/20261102-214116-378436_live.log`.
Contexte fourni par l'utilisateur : télécommande initialement éteinte, puis
ON, OFF, ON, ventilation +, ventilation − trois fois. Aucun essai d'émission
ESP32 ni changement des profils effectué pour cette analyse.

## Correspondance des appuis

Le journal contient exactement 35 trames, réparties en sept groupes de cinq
trames identiques. Les numéros RX vont de 1 à 35 sans interruption. Les 35 CRC
ont été recalculés indépendamment avec `binascii.crc_hqx`, tous corrects.

| Première réception (heure de Paris) | Appui déclaré | Trame complète, cinq répétitions | Mode | Puissance | Ventilation 1 |
|---|---|---|---:|---:|---:|
| 21:41:25.678 | ON | C8 CC 02 8F B8 8E 16 | 3 | 3 | 4 |
| 21:41:31.283 | OFF | C8 CC 02 8C B8 DB 45 | 0 | 3 | 4 |
| 21:41:35.898 | ON | C8 CC 02 8F B8 8E 16 | 3 | 3 | 4 |
| 21:41:40.650 | Ventilation + | C8 CC 02 AF B8 88 F0 | 3 | 3 | 5 |
| 21:41:45.292 | Ventilation −, premier appui | C8 CC 02 8F B8 8E 16 | 3 | 3 | 4 |
| 21:41:49.337 | Ventilation −, deuxième appui | C8 CC 02 6F B8 9E A4 | 3 | 3 | 3 |
| 21:41:53.482 | Ventilation −, troisième appui | C8 CC 02 4F B8 98 42 | 3 | 3 | 2 |

Ces correspondances reposent sur l'ordre déclaré des gestes ; il n'y a pas
d'horodatage indépendant des appuis permettant de mesurer la latence exacte.

## Interprétation

- Le champ ventilation 1 suit 4 → 5 → 4 → 3 → 2. Les boutons décrits modifient
  bien ce champ, sans modifier la puissance de chauffe, qui reste à 3.
- OFF change le mode de 3 à 0 et conserve les autres réglages. ON rétablit ici
  le mode 3, habituellement décrit comme ECO dans les sources étudiées.
- Toutes les trames gardent l'ID C8CC02, le champ ventilation 2 à 7, les bits
  historiques « user » à 2 et les bits réservés à 0. Le sens opérationnel de
  ventilation 2=7 et des bits « user » reste non qualifié.
- Le quatrième octet contient à la fois mode, puissance et ventilation 1.
  Après le troisième ON : 8F ; ventilation + : AF ; puis − : 8F, 6F, 4F.
  Les différences découlent de la valeur absolue des champs ; elles ne sont
  pas des codes « bouton + » ou « bouton − ».

Le premier appui − ramène donc exactement la même trame que ON : c'est la
même configuration demandée. Le libellé du moniteur « Allumer enregistré »
signifie uniquement que les sept octets correspondent au profil enregistré ;
il ne permet pas d'identifier le bouton pressé et ne confirme pas l'état du poêle.

Conséquence pour l'application actuelle : son bouton Allumer rejoue le profil
capturé, qui inclut puissance 3 et ventilation 1=4. Il ne reprend pas
automatiquement le dernier réglage 2 de cette nouvelle séquence. Les profils
ont volontairement été conservés pour ne pas changer le comportement de commande
à l'occasion d'une analyse de journal.

## Temps observés et correction du moniteur

Les horodatages PC montrent 81 à 84 ms entre les répétitions, moyenne
82,39 ms. Les cinq lignes de chaque groupe s'étalent sur 328 à 331 ms, du
premier au dernier horodatage de réception. Ce n'est pas la durée totale de
l'émission, car le premier horodatage arrive après réception et décodage.

Les colonnes « +78 ms / +94 ms » du journal utilisent une autre horloge que
les heures imprimées. Vérification dans le Python 3.11 installé :

- `time.monotonic` : GetTickCount64, résolution 15,625 ms ;
- `time.perf_counter` : QueryPerformanceCounter, résolution annoncée 0,1 µs.

Le moniteur utilise désormais `perf_counter` pour tous ses intervalles et
délais. La résolution annoncée du compteur n'est pas une garantie de précision
radio : décodage, ordonnancement et transport USB restent inclus.
Le journal source reste inchangé. Relancer le moniteur applique la correction.

Validation de la correction : cinq tests du moniteur réussis, dont une session
simulée vérifiant l'emploi de l'horloge précise, l'absence de commandes autres
que les requêtes de statut `j`/`s`, le journal et la libération du port USB.
Résultats détaillés : `analyse-sequence-20261102-214116.json`.

## Limites

Cette observation confirme la réception cohérente des sept groupes annoncés,
pas l'exécution de ces réglages par le poêle. Le moniteur ne journalise que les
trames comprises par le décodeur actuel ; il ne prouve pas l'absence d'autres
signaux. Aucun message d'appairage n'est établi par cette séquence ON/OFF/ventilation.
