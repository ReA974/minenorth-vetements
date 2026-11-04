# MineNorth Vêtements

Mod Forge 1.20.1 (`minenorth_vetements`) : vêtements de marque (fausses marques inspirées) pour le roleplay MineNorthRP.
Les objets ont leur propre onglet créatif « Vêtements MineNorth » (séparé de l'onglet « Animaux » du mod `minenorth-pets` depuis le 03/11).

## Compilation
`./gradlew build` (JDK 17 : `JAVA_HOME=~/.jdks/ms-17.0.20.1`, Gradle échoue sous Java 27) → `build/libs/minenorth-vetements-1.0.0.jar`.

## Accessoires
**Accessoires VIP** (`VipItems`, avantage `vetementsVip` du mod VIP via l'API, par réflexion) : `chaine_vip`, `montre_vip` (VIP) ; `chaine_diamant`,
`montre_diamant`, `lunettes_holo` (VIP+). Refusés à la pose sans le grade (emplacements de l'inventaire, `/accessoires`) ; vérifié toutes
les 5 s : porté sans le grade = retiré et rendu. Les OP peuvent tout porter. Générés par `tools/gen_streetwear.py` (liste `ACCS`).
Un par emplacement (visage, cou, poignet, mains, dos), en plus des vêtements : on les pose et les retire uniquement par le menu des accessoires (inventaire ou `/accessoires`), plus de clic droit (retiré le 29/10)
(main vide : le dernier porté), `/accessoires` pour la liste cliquable. Chapeaux / casquettes / bonnets / bobs : emplacement casque.
Inventaire du joueur : 5 cases (`AccessorySlot`, ajoutées au menu d'inventaire des deux côtés, index 46 à 50) dans un panneau à gauche de la fenêtre
(`client/InventoryPanel`), cachées avec le livre de recettes et retirées de l'inventaire créatif. Nécessite `META-INF/accesstransformer.cfg`.
Icônes fantômes : `tools/gen_icones_emplacements.py`.
Créatif : bouton « Accessoires » sur l'onglet inventaire et `/accessoires` ouvrent `AccMenu` / `client/AccScreen` (conteneur ordinaire, synchronisé
même en gm 1) ; `/accessoires liste` = liste cliquable dans le chat. Noms des objets en français dans `fr_fr` ET `en_us`.
Cagoules : texture de tête sur leur propre modèle à 0,62 (`SlimArmor.BALACLAVA`, au-dessus des cheveux du skin et des casquettes à 0,52) ;
un chapeau porté avec est relevé de `HAT_LIFT` (0,22). Identité masquée (`Accessories.masked`) : plus de nom au-dessus de la tête (client, `RenderNameTagEvent`) et « Individu masqué » comme nom
affiché : fourni par l'API (`MaskService`, `Accessories.provideMask`) et appliqué par le mod Identité, qui compose le nom (cagoule après le mode staff,
préfixe VIP caché) ; le TAB garde le vrai nom. Dépend de MineNorth API 1.2.0.

## Outils (`tools/`, depuis la racine du mod)
- `gen_streetwear.py` : doudounes, sweats, vestes, manteaux, pantalons, couvre-chefs et accessoires (textures, modèles, `Formes.java`, `AccessoryData.java`, langues).
- `fix_pantalons.py` : nettoie les calques jambes (rien au-dessus de la taille).
- `apercu.py <skin> <slim 0|1> <sortie.png> [tête] [haut] [jambes] [pieds] [acc,...]` : aperçu 3D hors jeu.
- Ordre de génération : `Gen.java`, `gen_rp.py` et `gen_acc.py` (anciennes tenues) **avant** `gen_streetwear.py`, qui repeint les chaussures
  de ces tenues (bas des jambes du calque 1) et écrit `Formes.java` (formes réparties en méthodes : limite Java de 64 Ko par méthode).
  Attention : `Gen.java` réécrit les fichiers de langue en entier, ne le relancer qu'en connaissance de cause.

## Casquettes
Forme d'après la « boss cap » de ZeroContact (03/11) : `cap_boxes` de `gen_streetwear.py` (formes `CAP` et `CAP_INV` pour les casquettes
à l'envers, générées là depuis, plus dans `gen_acc.py`) ; calotte à plateau et bouton, panneau avant structuré, coutures et œillets,
visière incurvée et inclinée, sangle à pression. Les casquettes des anciennes tenues (Nayk, Supreem…) ont la même forme, recopiée dans
`ClothesExtras` (relief Java). Aperçus : `apercu-casquettes-avant.png`, `apercu-casquettes-apres.png`.

## Chaussures
Toutes les paires `*_boots` (03/11) : tige peinte en 512 × 256 sur le bas des jambes (cuir, vernis, daim, toile, maille, nubuck, caoutchouc,
monogramme ; empiècements, piqûres, lacets croisés, œillets, logos) et relief généré : semelle, bout arrondi, talon (aiguille pour les escarpins),
languette, lacets, œillets / crochets, col rembourré, tige des bottes et rangers. Relief sous la forme `<id>_boots` (`ClothesExtrasLayer` la
cherche pour l'emplacement pieds, une tenue peut aussi avoir un haut ou une casquette en relief) ; pastilles 16 à 31 (lignes 2 et 3 de la
palette), à part de celles du haut. Paire en 3D dans l'inventaire (`<id>_boots_acc`). Types (`PROFIL` dans `gen_streetwear.py`) : basket,
runner, montante, toile, chunky, securite, derby, mocassin, chelsea, santiag, escarpin, sandale, tong, claquette, sabot, botte, rangers,
chantier, apres_ski, fourree. Anciennes tenues : liste `SHOES_TENUES` ; chaussures vendues seules : liste `CHAUSSURES`.
Aperçus : `apercu-chaussures-avant.png`, `apercu-chaussures-apres.png`, `apercu-chaussures-zoom.png`.

## Garde-robe RP (03/11)
Liste `GARDEROBE` (+ chapeaux) de `gen_streetwear.py`, aperçu `apercu-garde-robe.png` :
- travail : gilet de chantier, pantalon à genouillères, casques de chantier, veste / pantalon de mécanicien, veste / pantalon pied-de-poule /
  toque de cuisinier, chemise et gilet / tablier de serveur, veste et casquette de livreur ;
- sport : maillots de foot et de basket, shorts, brassière, legging ;
- soirée : costumes Miami rose et bleu ciel (veste + pantalon), chemises hawaïennes, chemise blanche, robe bustier et jupe à paillettes,
  robe et jupe moulantes ;
- bain : maillot une pièce, short flamants roses ; hiver : parkas à capuche fourrée, chapka ;
- femme : crop tops, top à bretelles, jupe plissée, mini-jupe en cuir, jean mom, short en jean ;
- basiques : t-shirts, marinière, débardeur côtelé, chemise à carreaux, bermuda cargo.
Vente : pack `boutiques-minenorth` de `minenorth_shops` ; les tenues pompiers, SAMU, police et RAID n'y sont jamais.

## Tenues de Police Nationale
Générées par `tools/gen_streetwear.py` (section « tenues de Police Nationale », liste `POLICE`), bleu nuit `NAVY_PN`.
Par grade du mod Police (Sous-officier, Officier, Commissaire) : `polo_police_<grade>` et `blouson_police_<grade>` ; communs : `parka_police`,
`pantalon_police`, `casquette_police`, RAID : `blouson_raid` (noir, RAID dans le dos) et `pantalon_raid` (avec `chaussures_intervention` et `gants_pompier` « Gants d'intervention »).
Grade lisible en relief : patte de poitrine + épaulettes (formes `POLO_PN_*` / `BLOUSON_PN_*`, fonction `epaulettes`) : 1 galon argent,
2 galons argent, 3 galons or. Logo POLICE NATIONALE (poitrine et manches) détouré depuis `tools/logo_pn.png` (repris du gilet PN de
ZeroContact), POLICE dans le dos. Brassard BAC, casques balistiques et gilets pare-balles PN : dans ZeroContact.

## Licence
**Tous droits réservés - MineNorthRP.** Voir [LICENSE](LICENSE).

## Sacs
Accessoires de l'emplacement Dos = sacs de rangement (`Bags` : contenance par id, contenu dans le tag `mnv_sac` de l'objet).
Seul le sac porté s'ouvre (`BagMenu` / `client/BagScreen`, paquet `OpenBag`) : touche `BagClient.KEY` (B), bouton « Sac » de l'inventaire
(`InventoryPanel`) et du menu Accessoires. Interdits dedans : sacs et objets non rangeables (boîtes de Shulker). Le contenu n'est jamais
envoyé aux autres clients (`Bags.withoutContents` dans `AccNet.Sync`).

## Parachute (04/11)
- Objet `parachute` (accessoire, emplacement **Dos / sac**, sac olive avec poignée orange, généré par `tools/gen_streetwear.py`).
- En chute libre (au moins 3 blocs, ni monté, ni dans l'eau, ni en élytres), **Espace ouvre la voile** : la chute est freinée, on plane dans
  la direction du regard (plus vite en avançant), et on se pose **sans dégâts**. La voile (caissons orange et blancs, suspentes) est visible
  par tous les joueurs proches, et par soi en levant les yeux. Il faut 4 s pour replier la voile après l'atterrissage.
- Mouvement appliqué chez le joueur ; le serveur valide l'ouverture (parachute porté, vraie chute), annule les dégâts de chute et diffuse la voile
  (`Parachute`, `client.ParachuteClient`). Réseau des accessoires : **protocole 6** (serveur ET clients).
