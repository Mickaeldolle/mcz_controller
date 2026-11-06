# Captures réelles

Ce dossier contient les journaux réels de réception, de surveillance et d'essais
USB/RF du projet. Ne pas déposer de fixtures synthétiques ici : les conserver
dans les tests et les identifier explicitement comme telles.

Repères de provenance :

- `20261030-124843_buttons.log` : source des profils ON/OFF actifs.
- `20261102-215528-553832_live.log` : source des profils manuels distincts.
- `*_pairing.log` : préparation et résultat USB des essais supervisés. Un résultat
  `sent` ne prouve ni l'onde RF ni la réaction du poêle ; noter séparément
  l'observation physique. Certains journaux ne contiennent aucun envoi.

Voir [l'état du projet](../docs/agents/ETAT_PROJET.md) et
[le guide des agents](../AGENTS.md). Conserver les originaux sans les réécrire ;
placer les analyses dérivées dans un fichier distinct.

Conserver le journal série complet, avec date, carte, branchements, fréquence,
version du firmware, commande affichée par la télécommande et distance d'essai.
Nom conseillé : `YYYYMMDD-HHMM_OFF.log`, puis `ON_P1`, `FAN1`, `FAN2`.
L'identifiant télécommande est une donnée locale : éviter de publier les captures.
