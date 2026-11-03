# MineNorth Vêtements

Mod Forge 1.20.1 (`minenorth_vetements`) : vêtements de marque (fausses marques inspirées) pour le roleplay MineNorthRP.
Les objets vont dans l'onglet « Animaux & Vêtements » (mod `minenorth-pets`), sinon dans l'onglet commun « MineNorth ».

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
