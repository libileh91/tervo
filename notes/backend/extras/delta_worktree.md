# Identifier le checkout Delta avant intégration

Delta travaille dans une copie du dépôt. Vérifier le terminal ouvert avant
de lancer une commande Git :

```bash
pwd
git rev-parse --show-toplevel
git branch --show-current
git --no-optional-locks status --short
git log -1 --oneline
```

La branche de destination et le chemin varient : ne pas recopier ceux d'une
ancienne session. Les fichiers non commités ne sont pas inclus dans un transfert
de commits. Demander à l'agent le SHA exact de la tâche validée.

Pour intégrer une autre conversation Delta, demander explicitement de
récupérer ses changements. Pour intégrer dans le checkout principal, examiner
d'abord les commits et les modifications locales ; ne pas lancer de
`reset --hard`, push forcé ou `stash pop` automatique.

**Commit, intégration locale et push sont trois actions distinctes.**
Un commit dans Delta ne prouve ni une intégration dans le checkout principal,
ni une publication distante.
