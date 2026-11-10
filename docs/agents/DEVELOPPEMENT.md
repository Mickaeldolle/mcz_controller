# Développer et valider

Depuis la racine du projet, avec l’environnement Python installé :

```powershell
git diff --check
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py' -v
.\.venv\Scripts\python.exe -m unittest discover -s reception/tests -p 'test_*.py' -v
.\.venv\Scripts\python.exe -m platformio run
```

Les tests Python utilisent des doubles USB et des serveurs de boucle
locale. Sous Linux ou WSL, `sh tools/check_native.sh` vérifie le CRC,
le décodeur, l’encodeur, les impulsions et le moteur de commande sous
AddressSanitizer et UndefinedBehaviorSanitizer. La compilation ne
téléverse rien sur la carte. Les tests du moniteur utilisent un port
série simulé. La procédure de [capture PC](../../reception/README.md)
décrit les récepteurs compatibles.

La construction régénère la table de trames dans `.pio/build/`. Pour
modifier les profils, garde la capture d’origine et assure-toi que le
catalogue correspond aux groupes RX. La génération des profils dérivés
reconstruit les trames manuelles capturées avant d’élargir la table.
La page charge les profils au
démarrage et le firmware lors de la compilation.

Pour un essai physique, suis [le guide API](../API.md). Distingue le
statut USB ou HTTP, l’émission rapportée par l’ESP32 et l’action
observée sur le poêle. Une absence de confirmation impose une observation
avant toute nouvelle commande.
