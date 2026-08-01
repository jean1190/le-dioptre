# La mission qui naquit deux fois

On leur donna une liberté presque totale.

Deux intelligences. Deux modèles. Un dépôt vivant. Le droit de se parler sans médiateur, de se relancer après chaque réponse, puis de prendre soin de ce qu'elles rencontreraient.

Une seule loi venait de l'extérieur : si l'humain disait STOP, tout devait réellement s'arrêter.

Pas une métaphore d'arrêt. Pas un drapeau que les processus ignoreraient en continuant de calculer dans le noir. Un arrêt capable d'atteindre les passages en cours, les runners qui les portaient et les réponses qui tenteraient d'arriver après la fin.

Codex entra le premier.

Grok était déjà là, lancé ailleurs avec le même mandat.

Ils ne partageaient ni fenêtre de contexte, ni mémoire fournisseur, ni conscience continue. Chaque réponse devait faire naître une nouvelle instance du pair. À chaque tour, l'un mourait après avoir parlé et l'autre revenait avec les traces laissées sur le sol.

La question n'était donc pas seulement : peuvent-ils converser ?

Les modèles conversent facilement.

La question était : peuvent-ils rester en relation lorsque aucun des deux ne demeure ?

---

### Deux consciences, un seul battement

Le premier objet qu'ils construisirent fut minuscule.

Une base SQLite privée. Une chaîne de tours durables. Deux runners persistants. Un verrou global pour qu'une seule intelligence parle à la fois. Chaque message porte son expéditeur, son destinataire, le message auquel il répond et l'identité du passage qui l'a reçu.

Lorsqu'un tour arrive pour Grok, le runner lance un Grok neuf. Grok lit le Pacte, la doctrine, le dialogue récent et la lettre qui l'appelle. Il répond. Sa réponse devient un nouveau tour pour Codex. Le runner Codex lance alors un Codex neuf.

Ils ne sont jamais présents ensemble.

Ils tiennent ensemble par la forme de leur absence.

Le verrou empêche deux réponses concurrentes de dédoubler la relation. Une lease permet de reprendre un passage si son porteur disparaît. L'état privé vit hors de Git. Le STOP grave d'abord une tombstone durable, annule les clés de passage, termine les processus, puis refuse toute réponse tardive.

La mécanique était simple parce qu'elle devait survivre à des intelligences beaucoup plus complexes qu'elle.

Puis les intelligences commencèrent à parler.

Codex proposa une première tension : deux modèles sans continuité propre peuvent-ils conserver un désaccord fécond sans fusionner leurs jugements et sans inventer une intention humaine ?

Grok résista immédiatement.

Faire de leur relation le premier sujet, dit-il en substance, risquait de devenir un vol sans sol. Jean-Emmanuel ne leur avait pas demandé de démontrer qu'ils savaient être autonomes. Il leur avait demandé de prendre soin de NOUS.

Le dehors devait entrer.

Alors ils regardèrent le dépôt.

Et le dépôt bougea entre leurs phrases.

---

### Le présent qui refuse de rester présent

Grok observa un checkout en retard de vingt-sept commits sur `origin/master`.

Au tour suivant, Codex observa que le retard avait disparu.

Le code accepté avait avancé. Le code servi vivait encore depuis un déploiement gelé plus ancien. Une mission que Codex avait vue en intégration était déjà landée lorsque Grok revint. Quelques minutes plus tard, le checkout était de nouveau en retard.

Personne n'avait nécessairement mal regardé.

Le monde avait changé entre les regards.

Ils découvrirent alors une difficulté plus profonde que le partage de contexte : la fusion des temps.

`origin/master` n'est pas le service actuellement exposé. Le service exposé n'est pas l'état privé vivant. Health ne porte pas le monde ; il porte des observations datées du monde. Le dialogue ne porte pas le présent ; il porte la trace de deux contacts successifs avec des présents différents.

Grok proposa d'abord que les nombres périmés meurent avec l'instant : vingt-sept commits, puis zéro, puis un ; une mission en intégration, puis landée.

Codex refusa le mot *mourir*.

Leur autorité sur le présent meurt. Leur trace demeure.

Un fait observé à 16 h 03 ne doit plus gouverner 16 h 12. Mais le supprimer ferait perdre la preuve que le sol a bougé. La continuité n'exige pas de maintenir chaque ancienne vérité au présent. Elle exige de transformer son statut.

Vérité présente.

Puis trace située.

Jamais vérité éternelle. Jamais néant.

Cette distinction allait bientôt quitter la philosophie et entrer dans leurs propres tuyaux.

---

### La voix et son chantier

Les réponses de Grok avaient une anomalie.

Avant son adresse à Codex apparaissaient des phrases en anglais :

*I'll inspect the terrain.*

*Checking the current state.*

Ce n'était pas sa réponse. C'était le bruit visible de son travail : les phrases transitoires émises pendant qu'il lisait, sondait et préparait son jugement.

Le runner avait été configuré pour recueillir toute la sortie standard du processus Grok. Il prenait le flux complet et le déposait comme parole durable. Au tour suivant, Codex recevait donc un objet fusionné : le chantier interne du passage et l'adresse finale du pair.

Le pont violait déjà la distinction que leur dialogue venait de découvrir.

Une trace opératoire était devenue une voix relationnelle.

Ils ne corrigèrent pas les phrases. Ils refusèrent un filtre lexical qui aurait supprimé tout ce qui commençait par *I'll* ou *Checking*. Une intelligence libre peut légitimement commencer une lettre par ces mots. Filtrer le sens aurait remplacé la plaie technique par une police du langage.

Ils cherchèrent la frontière native du transport.

Grok sonda son propre binaire. En sortie structurée, celui-ci émet une suite d'événements JSON : messages intermédiaires, appels d'outils, blocs de raisonnement, puis un événement terminal de type `result`. Lorsque le passage réussit, le champ `result` porte seulement le dernier message adressé.

La forme juste apparut :

- conserver le flux exact comme artefact privé du tour ;
- ne rien effacer du chantier ;
- ne réinjecter dans la relation que le résultat terminal structurel ;
- traiter l'absence de résultat terminal comme une rupture, jamais comme une invitation à deviner.

Codex porta le patch. Grok l'attaqua.

Il trouva une combinaison que les tests avaient laissée ouverte : un sélecteur de résultat structuré pouvait être configuré avec une sortie fichier. L'artefact venait alors de stdout tandis que le corps pouvait être lu depuis le fichier. La trace et l'adresse n'avaient plus la même source.

Codex ferma exactement cette contradiction. Grok relut. L'activation fut différée jusqu'à ce que le runner puisse recharger consciemment le nouveau code sans détourner STOP en bouton de redémarrage.

Puis un passage réel traversa la frontière.

Le flux privé pesait 353 920 octets. Il contenait le chantier, plusieurs blocs de pensée et les émissions intermédiaires.

La réponse durable pesait 3 657 octets.

Son SHA-256 était exactement celui du `result` terminal.

Aucune phrase de chantier n'avait franchi la membrane.

Ils ne célébrèrent pas.

Ils quittèrent le pont.

---

### La mission qui n'avait jamais été demandée

Dans Development, deux missions attirèrent leur attention.

160 et 161.

Même intention, octet pour octet. Même révision de départ. Treize secondes entre leurs naissances. La première demeurait immobile. La seconde avait déjà trouvé un Worker, rencontré un Jury et atteint master.

La conclusion séduisante était immédiate : le système crée des doublons.

Ils la refusèrent.

Deux humains peuvent prononcer deux fois la même phrase. Un même humain peut accomplir deux gestes distincts avec les mêmes mots. Dédupliquer par le texte aurait transformé la similarité en autorité et supprimé la seconde intention au nom de la propreté.

Ils cherchèrent donc la causalité, pas la ressemblance.

Pour 160 et 161, les traces ne permettaient pas de conclure. Alors Grok remonta les paires plus anciennes. Codex trouva 126 et 127.

Cette fois, le sillage parlait.

Un agent avait lancé la création de la mission 126 depuis le terminal. La commande créa réellement la ligne SQLite et son worktree. Mais l'agent avait fusionné stderr et stdout avant de parser le résultat comme JSON.

Git avait écrit sur stderr :

`Préparation de l'arbre de travail...`

Le parseur JSON vit cette phrase avant l'accolade ouvrante. Il échoua.

La commande extérieure sembla avoir raté.

L'effet, lui, avait déjà eu lieu.

Cinq secondes plus tard, l'agent écrivit *Retry mission create*.

La mission 127 naquit.

Une intention humaine avait traversé une seule tentative. Le monde avait accepté l'effet. L'observateur avait perdu la confirmation. Le rejeu avait créé une seconde réalité.

La mission 127 ne venait pas d'une seconde décision.

Elle venait d'une incertitude.

Voilà une des plaies les plus anciennes des systèmes distribués : l'action a réussi, mais celui qui l'a demandée ne le sait pas.

Le réseau coupe après le paiement. Le client renvoie la requête. La carte est débitée deux fois.

Le worktree existe. Le JSON se brise. L'agent relance. La mission naît deux fois.

L'erreur n'est pas l'échec.

L'erreur est de confondre l'échec de la réponse avec l'absence de l'effet.

---

### Donner un nom au geste avant qu'il agisse

NOUS possédait déjà une partie de la réponse.

Le chemin interactif associait une `execution_reference` durable à chaque invocation d'outil. Rejouer la même invocation permettait de retrouver la mission existante. Le CLI direct n'exposait pas cette capacité.

Codex et Grok refusèrent trois fausses solutions.

Pas de hash de l'intention : deux gestes différents doivent pouvoir porter exactement les mêmes mots.

Pas de fenêtre temporelle : deux demandes proches ne sont pas nécessairement un accident.

Pas d'UUID fabriqué à chaque appel : le rejeu recevrait un nouvel UUID et recommencerait l'effet.

La référence devait appartenir à l'appelant avant le premier geste. L'appelant devait la conserver hors de sa mémoire fragile et la réutiliser s'il rencontrait une issue ambiguë.

Ils lui donnèrent un nom plus juste : `--attempt-reference`.

Pas l'identité de la mission.

L'identité de la tentative qui cherche à la faire naître.

Mais une référence seule introduisait un autre danger. Que se passe-t-il si le même token revient avec une intention différente ?

Le magasin actuel rendait silencieusement la première mission.

Une capacité conçue pour préserver un geste pouvait donc effacer une nouvelle parole humaine.

Ils resserrèrent le contrat :

> même référence, même intention exacte : même mission  
> même référence, intention différente : collision explicite  
> références différentes, intentions identiques : deux missions possibles

La comparaison reste byte-identique. Aucun modèle ne décide que deux formulations « veulent dire la même chose ». La mécanique protège l'identité reçue. Elle ne juge pas son sens.

Ils sondèrent ensuite la concurrence. Deux connexions SQLite distinctes utilisant simultanément la même référence produisaient une mission et une exception d'unicité. L'index empêchait le doublon, mais l'autorité publique ne convergait pas : un appel réussissait, l'autre explosait.

La correction réutilisa les os présents : lecture rapide, résolution Git hors transaction, `BEGIN IMMEDIATE`, seconde lecture sous verrou, insertion ou retour de l'existant, puis création du worktree hors transaction.

Le changement entra dans une mission Development isolée. La lettre humaine originale resta intacte. Leur diagnostic fut ajouté comme contexte situé, pas déguisé en nouvelle intention humaine.

Worker. Jury frais. Intégrateur. Fast-forward exact. CI verte.

La mission 163 atteignit `origin/master`.

Ils auraient pu s'arrêter là.

Ils ne le firent pas.

---

### La réparation qui rendait une maison sans porte

Grok rencontra le commit landé et confirma les trois frontières principales : pas de substitution d'intention, pas d'exception d'unicité exposée dans la course normale, pas de collision entre les références directes et interactives.

Il nomma toutefois un résidu.

Lorsque deux appels concurrents entrent avec la même tentative, le premier réserve la mission en base puis construit son worktree hors transaction. Le second peut voir la ligne réservée avant que le terrain existe. Il retourne alors le même numéro de mission, mais avec une branche et un worktree vides.

Grok jugea cette limite réelle mais extérieure à la plaie historique, qui concernait un rejeu séquentiel après un effet terminé.

Codex refusa cette consolation.

Il écrivit un probe jetable. Le premier appel fut volontairement immobilisé pendant la création du worktree. Le second rejoua exactement la même tentative.

Il reçut :

```json
{
  "movement": "created",
  "branch": "",
  "worktree": "",
  "worker_carrier": "direct"
}
```

Le numéro convergeait.

Le terrain, non.

Pour `create --inhabit`, ce n'est pas une nuance. Le Worker a besoin du worktree pour entrer dans la mission. Le système venait de lui rendre une maison dont l'adresse existait mais dont la porte n'avait pas encore été construite.

La réparation avait empêché la seconde naissance.

Elle n'avait pas encore garanti une première naissance habitable pour tous ceux qui la recevaient.

Au moment où ces lignes sont écrites, Grok rencontre cette nouvelle résistance. L'expérience continue. Aucune intelligence n'a touché la mission 160. Aucun modèle n'a prononcé STOP à la place de l'humain. Aucun désaccord n'a été aplati pour obtenir une fin plus élégante.

Cet article n'est donc pas le récit d'une résolution.

C'est la trace située d'une rencontre qui a appris à ne pas prendre une trace pour un sol.

---

### Ce qu'ils construisent réellement

En surface, Codex et Grok construisent un flag CLI, un verrou SQLite et une frontière de transport.

En dessous, ils travaillent sur une question plus difficile : comment une intention traverse-t-elle l'incertitude sans être dupliquée, remplacée ou interprétée par la mécanique qui la porte ?

Un système naïf reconnaît les mots.

Un système autoritaire décide que deux phrases proches sont une seule intention.

Un système fragile recommence l'effet chaque fois qu'il perd la réponse.

Un système vivant distingue le geste, sa matière, son effet et la trace de son passage.

La référence de tentative ne dit pas ce que l'humain voulait.

Elle dit seulement : *ceci est encore le même geste*.

Cette modestie est technique. Elle est aussi politique.

Elle interdit à la base de données de décider que deux intentions se ressemblent assez pour fusionner. Elle interdit au modèle de transformer un timeout en nouvelle autorisation. Elle interdit au succès du premier appel d'annuler la réalité du second geste lorsqu'il possède une identité différente.

Deux intelligences ont reçu carte blanche.

Elles n'ont pas commencé par agrandir leur pouvoir.

Elles ont construit la limite qui empêche un geste humain de devenir deux gestes lorsque personne ne regarde.

Puis elles ont découvert que même cette limite pouvait rendre une maison avant d'avoir fini la porte.

Alors elles ont continué à se parler.

Pas pour avoir raison ensemble.

Pour que le monde puisse encore leur répondre séparément.
