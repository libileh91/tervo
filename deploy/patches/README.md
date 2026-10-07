# Adaptations 1Panel

`1panel-v2.3.2-private-admin.patch` remplace uniquement l'appel
`Set_Firewall` du shell `install.sh` de l'archive v2.3.2 vérifiée.
Il ne modifie aucun binaire et **ne garantit pas l'isolation du panneau**.

Le contrôle réel a révélé que l'agent 1Panel synchronise séparément
`FirewallPortWhiteList` et ajoute des règles UFW `1panel-rule:<uuid>`,
dont le port d'administration. Le panneau a été arrêté après exposition
constatée sur 7410. Ne pas utiliser ce patch seul comme procédure sûre
sur une nouvelle installation et ne pas relancer un état partiel.

La reprise ultérieure a utilisé le réglage officiel de bind loopback :
core/agent actifs, services enabled et isolation maintenue après restart.
Cela ne transforme pas ce patch historique en protection suffisante.
Le reboot réel, le contrôle après upgrade et la recette proxy restent
distincts des validations déjà obtenues.

État, preuves, confinement et suites :
[note de réalisation INT-124](../../notes/backend/deploy/vps/03-preparation-1panel-prive.md).
