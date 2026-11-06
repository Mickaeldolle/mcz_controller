# Essai d'appairage avec l'ESP32 — 2 novembre 2026

## Résultat

**Tentative d'association non confirmée par le poêle.** L'utilisateur indique
que les trois traits « --- » sont restés affichés, sans bip ni autre réaction.
La commande a été envoyée une seule fois, à moins d'un mètre du poêle, sans
obstacle, d'après la confirmation de l'utilisateur.

## Contexte et commande

- Le poêle démarre depuis le sélecteur local sur ON.
- Sur REMOTE, il ne répond pas à sa télécommande d'origine.
- L'association avec la télécommande d'origine a déjà été essayée : affichage
  « --- », puis appui ON/OFF, sans confirmation.
- Les trames d'origine sont reçues et décodées par notre ESP32.
- L'utilisateur a confirmé l'affichage « --- » juste avant notre déclenchement.
- Câblage conservé : GDO0 du CC1101 vers GPIO27 de l'ESP32 ; SPI inchangé.
- Aucun flash ni augmentation de puissance RF effectués pendant l'essai.
- Puissance RF configurée : environ 0 dBm nominal, non mesurée.

La trame rejouée est la capture manuelle :

```text
C8 CC 02 45 B8 77 89
ID=C8CC02, mode=1, puissance=1, ventilation1=2,
ventilation2=7, bits user=2, reserve=0, CRC=7789.
```

Il s'agit d'une commande ON connue, pas d'une trame spécifique d'appairage
identifiée. Une commande contient cinq répétitions. Son identifiant USB était
`e364862ff9070f7cef6a35a27f97bc11` ; cet identifiant de requête n'est pas
l'identifiant radio C8CC02.

## Déroulement observé côté PC et firmware

Source : [journal d'essai](../captures/20261102-224307-845233_pairing.log).

| Heure de Paris | Événement |
|---|---|
| 22:43:10.013 | Préparation : connected=true, busy=false, compteur TX=0 ; attente du déclenchement |
| 22:46:39.464 | Une demande USB `on` contenant la trame capturée est transmise |
| 22:46:40.004 | Résultat USB `sent` |
| 22:46:41.063 | Nouveau statut : connected=true, busy=false, compteur TX=1 |
| 22:46:41.247 | Outil terminé et port COM3 libéré |

Le traitement USB observé a pris environ 540 ms. Il est cohérent avec une
commande nominale de 512790 µs plus les traitements, sans constituer une
mesure de la forme d'onde ni de la puissance rayonnée.

Le bilan technique établit l'exécution du chemin TX du firmware, l'achèvement
rapporté et le retour à un statut RX prêt. Il ne démontre pas que les octets
ont été émis correctement sur l'antenne ni reçus par le poêle. Aucun récepteur
indépendant, analyseur logique ou SDR n'a enregistré notre émission.

## Vérification hors ligne complémentaire

Les dix trames complètes de la capture brute d'origine
`20261102-211909_longpress_excerpt.log` se décodent avec `invert=0` dans
l'analyseur Python : cinq `C8 CC 02 8F B8 8E 16`, puis cinq
`C8 CC 02 8B 38 D3 5A`. La convention Manchester de nos données RX est donc
cohérente avec celle de l'encodeur, sans inversion nécessaire dans ces captures.
Cela ne mesure pas la polarité ou la modulation de notre émission physique.

## Interprétation et suite

Le poêle ignore ici deux émetteurs, mais notre TX RF n'étant pas encore
caractérisé, ce résultat ne démontre pas à lui seul une panne de son récepteur.
La distance inférieure à un mètre ne justifie pas d'augmenter arbitrairement
la puissance ni de multiplier les envois.

Le contrôle discriminant suivant est l'observation indépendante de notre TX :
un second récepteur ou SDR capable de recevoir aussi la télécommande permet
de comparer fréquence, activité RF, octets, polarité, répétitions et durées.
Une mesure numérique de GPIO27 ne prouve que la sortie ESP32, pas l'onde RF.
La procédure d'association exacte de cette génération reste à recouper ;
l'efficacité d'une commande ON ordinaire en apprentissage n'est pas établie.

Si une émission indépendante correctement qualifiée reste ignorée en suivant
la procédure exacte, examiner avec le mainteneur le chemin de réception,
l'antenne, le décodage et l'apprentissage du poêle. Aucune intervention sur
son câblage interne n'a été réalisée ni prescrite à l'utilisateur.

Les profils actifs de l'application n'ont pas été remplacés. L'outil a utilisé
le fichier manuel séparé. Aucune relance automatique, aucune seconde commande
et aucun ordre OFF n'ont été envoyés pendant cet essai, le poêle n'ayant
manifesté aucun début d'allumage.
