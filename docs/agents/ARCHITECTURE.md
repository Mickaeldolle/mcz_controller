# Architecture

Deux entrées partagent le même moteur de commande ESP32.

- Page locale → `app/server.py` → `app/bridge.py` → USB → firmware.
- Page embarquée ou application externe → HTTP sur le Wi-Fi local →
  `src/mcz_network.cpp` → firmware.
- Les deux pages partagent `app/web/`. `tools/embed_web.py` intègre ces fichiers
  au firmware et sélectionne le transport Wi-Fi lors de la compilation.
- `src/mcz_api.cpp` valide le profil et l’identifiant et applique le délai
  et l’anti-doublon communs. `src/main.cpp` génère le signal RMT et
  ramène la radio au repos après chaque commande.
- Le serveur HTTP tourne dans une tâche séparée, sur le même cœur que
  le code radio. Le verrou radio couvre les transitions RMT et les deux
  entrées de commande. Les délais réseau sont indépendants de l’USB.
- `src/cc1101_radio.cpp` configure le CC1101 en SPI. `mcz_encoder` et
  `mcz_crc` préparent les trames à émettre.
- [`reception/`](../../reception/README.md) regroupe les outils de capture
  PC, le décodeur hors ligne et l’assemblage d’impulsions. PlatformIO
  compile uniquement les sources de `src/`.
- `app/catalog.py` valide la provenance et génère les profils manuels
  dérivés après comparaison avec les captures. `tools/build_profiles.py`
  intègre la même table au firmware lors de la compilation.
- `app/network_setup.py` configure la connexion et la clé via USB.
  L’ESP32 conserve les paramètres en NVS et écoute seulement après connexion.

Voir [l’API et les protections](../API.md) et le
[protocole radio](../FONCTIONNEMENT_TRAMES_MCZ.md).
