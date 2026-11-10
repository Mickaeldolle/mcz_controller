# API HTTP de l’ESP32 · version 1

L’ESP32 héberge la page de commande et l’API sur le port HTTP 80 de son adresse IPv4. L’application
cliente peut joindre l’ESP32 directement sur le même sous-réseau Wi-Fi.
Le serveur Python du PC est facultatif pour cette voie.

## Mise en service

1. Garde une copie du firmware actuellement utilisé pour le retour arrière.
   Vérifie le [câblage](FONCTIONNEMENT_TRAMES_MCZ.md#matériel), puis ferme
   les applications qui occupent COM3.
2. Téléverse le firmware compilé. Cette commande remplace celui de la carte
   et la redémarre.

   ```powershell
   .\.venv\Scripts\python.exe -m platformio run -t upload --upload-port COM3
   ```

3. Prépare une clé aléatoire de 64 caractères hexadécimaux minuscules dans
   ton gestionnaire de mots de passe. Pour la générer localement, tu peux
   utiliser `python -c "import secrets; print(secrets.token_hex(32))"`.
4. Lance la configuration depuis une console interactive. Le programme
   demande le SSID Wi-Fi 2,4 GHz, le mot de passe WPA2 et la clé API.
   Les deux secrets sont saisis sans affichage.

   ```powershell
   .\.venv\Scripts\python.exe -m app.network_setup --port COM3
   ```

5. Ouvre `http://<ip-de-l-esp32>/` depuis un navigateur du même réseau.
   La page se connecte automatiquement. L’ouverture de la page et le
   déplacement des curseurs ne déclenchent aucune émission.
   La réservation DHCP du routeur permet de conserver cette adresse.
   Pour retrouver l’adresse via USB, relance la commande avec `--status`.
   `--forget` efface les paramètres réseau et désactive le Wi-Fi.

Le Wi-Fi est désactivé tant qu’aucune configuration n’a été enregistrée.
Les paramètres sont conservés sur la carte en NVS. Le projet ne configure
pas le chiffrement de la flash. L’API utilise **HTTP en clair**. Garde-la
sur un réseau privé de confiance, sans redirection de port ni exposition
à Internet. Les requêtes doivent provenir du même sous-réseau IPv4 et
viser l’adresse IPv4 de la carte dans l’en-tête `Host`. Si un en-tête
`Origin` est présent, il doit correspondre à cette adresse en HTTP. Les
routes API exigent une clé Bearer et le serveur n’active pas CORS.
Pour ce test local, l’ESP32 inclut sa clé configurée dans le HTML de la
page. Tout appareil capable d’ouvrir la page peut récupérer cette clé
et utiliser les commandes. La valeur reste hors du code source.
L’API accepte les clients natifs sans en-tête `Origin`.

## Contrat

Base : `http://<ip-de-l-esp32>`. Ajouter
`Authorization: Bearer <clé>` à chaque appel.

| Appel | Effet |
|---|---|
| `GET /api/v1/status` | Version, disponibilité de la radio, fréquence en Hz, compteur TX et profils autorisés |
| `POST /api/v1/command?profile=1%3A1&id=<id>` | Envoie la trame du profil flamme 1, ventilation 1 |
| `POST /api/v1/command?profile=3%3A5%3A0&id=<id>` | Envoie flamme 3, ventilateur 1 au niveau 5, ventilateur 2 à l’arrêt |
| `POST /api/v1/command?profile=off&id=<id>` | Envoie la trame d’arrêt |

Le POST attend un corps vide. Utilise un identifiant de 32 caractères
hexadécimaux minuscules par action explicite, par exemple un UUID sans
tirets. Les profils d’origine gardent le format `flamme:ventilateur1`.
Les profils à deux ventilateurs utilisent `flamme:ventilateur1:ventilateur2`.
Pour le ventilateur 2, `0` demande son arrêt et `6` correspond à Auto.
La table complète comprend 210 combinaisons explicites, les dix profils
d’origine et `off`. Liste les combinaisons disponibles avec GET.
Un réglage actif peut démarrer le poêle selon son état.

Un exemple de réponse de statut avec une liste de profils abrégée.

```json
{
  "version": 1,
  "ready": true,
  "frequency": 434500000,
  "tx_count": 0,
  "profiles": ["1:1", "1:1:0", "1:1:2", "3:5:0", "5:6:6", "off"]
}
```

| HTTP | Résultat | Interprétation |
|---:|---|---|
| 200 | `sent` | Émission terminée selon le firmware et retour au repos confirmé |
| 409 | `busy` | Radio occupée ou délai de trois secondes entre débuts d’envoi |
| 422 | `rejected` | Profil absent ou identifiant déjà utilisé pour un autre profil |
| 503 | `unavailable` | Radio indisponible |
| 500 | `uncertain` | Émission ou retour au repos non confirmé |
| 400 | `invalid_command` | Requête invalide |
| 401 | `unauthorized` | Clé absente ou incorrecte |
| 403 | `local_subnet_required` | Client hors du sous-réseau local |
| 403 | `invalid_host` ou `invalid_origin` | Hôte ou origine différent de l’adresse de la carte |

Le résultat d’une commande contient `id` et `result`. Le cache partagé
USB/Wi-Fi retient les 16 dernières commandes reconnues en mémoire vive.
Dans cette fenêtre, le même identifiant et profil renvoient le résultat
mémorisé sans réémettre. Le compteur et le cache repartent à zéro après
redémarrage. Après un délai dépassé ou un résultat incertain, vérifie le
poêle avant toute nouvelle action. Un `sent` est un résultat d’émission,
et l’état physique s’observe sur le poêle.

## Vérification en lecture seule

Depuis PowerShell, remplace l’adresse d’exemple par l’adresse affichée
par la configuration. Le GET ne déclenche aucune émission.

```powershell
$mczUrl = 'http://192.168.1.42'
$mczSecret = Read-Host 'Clé API' -AsSecureString
$mczHeaders = @{
    Authorization = 'Bearer ' + [System.Net.NetworkCredential]::new('', $mczSecret).Password
}
try {
    Invoke-RestMethod -Uri "$mczUrl/api/v1/status" -Headers $mczHeaders -TimeoutSec 5
} finally {
    Remove-Variable mczHeaders, mczSecret
}
```

Pour un essai physique, reste devant le poêle en mode distant et lance
une seule commande adaptée à son état. Vérifie ensuite sa réaction.

## Future application Kotlin

La page Web et l’application Android peuvent partager les mêmes routes.
L’application pourra prendre l’adresse IPv4 et la clé en configuration,
lire les profils via `GET /api/v1/status` et effectuer un seul POST par
geste explicite. Une absence de réponse ou un résultat incertain exige
d’observer le poêle avant une nouvelle commande.

Android bloque le trafic HTTP en clair par défaut pour de nombreux
clients. Évalue le transport au moment de développer l’application et
évite une autorisation globale du HTTP.
[Documentation Android sur le trafic en clair](https://developer.android.com/privacy-and-security/risks/cleartext-communications).

## USB

USB série à 115200 bauds, 8N1. Le port a un propriétaire à la fois.
`j` retourne le statut et `!NET\n` le statut réseau. Une commande
`!TX <id> <14 caractères hexadécimaux>\n` ne peut rejouer que les
octets du catalogue. Les réponses structurées commencent par `APP `.
La radio reste au repos (`IDLE`) entre les commandes. Après une erreur
SPI ou RMT pendant un envoi, vérifie le poêle avant de redémarrer l’ESP32.

Espressif documente les composants utilisés.
[Wi-Fi station](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/wifi.html),
[Preferences/NVS](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/preferences.html)
et [serveur HTTP ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/v4.4.8/esp32/api-reference/protocols/esp_http_server.html).
