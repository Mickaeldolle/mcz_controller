# Téléverser le firmware de l’ESP32 par Wi-Fi

La cible `esp32dev-alexa-temperature` inclut Alexa, le DHT11, l’OLED et le
téléversement OTA. Exécute les commandes PowerShell à la racine du dépôt.

## Première installation par USB

1. Éteins le poêle avec sa commande habituelle et attends la fin du
   refroidissement. Garde une copie du firmware fonctionnel et ferme le
   serveur PC ou le moniteur qui utilise COM3. Installe la variante OTA.

   ```powershell
   .\.venv\Scripts\python.exe -m platformio run -e esp32dev-alexa-temperature -t upload --upload-port COM3
   ```

2. La configuration Wi-Fi existante est conservée lors d’un téléversement
   USB standard. Si nécessaire, configure-la en suivant le
   [guide de l’API](API.md#mise-en-service). La page de commande de cette
   variante utilise le port 8080.
3. Génère une clé OTA et enregistre-la dans ton gestionnaire de mots de passe.
   La commande de configuration demande la clé deux fois, sans l’afficher.

   ```powershell
   .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
   .\.venv\Scripts\python.exe -m app.ota configure --port COM3
   .\.venv\Scripts\python.exe -m app.network_setup --port COM3 --status
   ```

## Mises à jour suivantes par Wi-Fi

Depuis le PC sur le même sous-réseau que l’ESP32, compile puis envoie le
firmware. Remplace l’adresse d’exemple par celle indiquée au statut USB.
L’outil te demande la clé OTA dans le terminal.

```powershell
.\.venv\Scripts\python.exe -m platformio run -e esp32dev-alexa-temperature
.\.venv\Scripts\python.exe -m app.ota upload 192.168.1.42
```

`upload` lit `.pio/build/esp32dev-alexa-temperature/firmware.bin`. Pour
sélectionner un binaire conservé ailleurs, ajoute `--firmware <chemin>`.
Seul le programme est écrit, dans l’emplacement d’application inactif de
1,25 Mio. Une image complète et valide est sélectionnée au démarrage
suivant. L’ESP32 redémarre après l’installation. Vérifie ensuite que la page
sur le port 8080 se reconnecte et que les mesures du DHT11 sont présentes.

Pendant l’écriture, les nouvelles commandes USB, Wi-Fi et Alexa sont
refusées. L’OLED affiche « Mise à jour » et « En cours », puis retrouve
l’affichage des mesures après le redémarrage ou si le transfert échoue.
Un résultat « radio occupée » signifie qu’il faut attendre la fin
de l’émission en cours avant de relancer le téléversement. Si le résultat de
l’envoi est incertain, vérifie le redémarrage et l’état de la carte avant
de réessayer. Si elle ne revient pas sur le Wi-Fi, utilise le câble USB
pour réinstaller un firmware fonctionnel.

## Accès OTA

L’ESP32 ouvre le port TCP 8081 après configuration de la clé et connexion au
Wi-Fi. Il vérifie le sous-réseau, l’hôte et l’origine comme pour l’API de
commande. Le client obtient un défi à usage unique valable une minute et
calcule un HMAC-SHA256 qui authentifie le défi et le SHA-256 du binaire.
La clé reste sur le PC pendant l’envoi. L’ESP32 la conserve dans sa NVS pour
les redémarrages. HTTP laisse le binaire visible sur le réseau. Garde le
service sur ton réseau de confiance, sans redirection de port Internet.

Pour fermer le port OTA, efface la clé par USB avec
`.\.venv\Scripts\python.exe -m app.ota forget --port COM3`.

Pour le premier essai, garde le poêle éteint et le câble à portée. Vérifie
qu’une tentative avec une clé incorrecte laisse la carte accessible, puis
envoie le binaire avec la bonne clé. Vérifie le message sur l’OLED pendant
l’envoi, puis le retour des mesures et le compteur radio à zéro après
redémarrage.

Le 13 novembre 2026, le téléversement USB sur COM3 a réussi et les
données écrites ont été vérifiées. Après redémarrage, le statut USB a
confirmé la connexion Wi-Fi sur le port 8080, 18 °C, 64 % d’humidité et
un compteur radio à zéro. Le propriétaire a ensuite confirmé le bon
fonctionnement du téléversement Wi-Fi et de son affichage OLED sur la carte.
