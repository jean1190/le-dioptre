# La mission qui naquit deux fois

Jean-Emmanuel lança Grok d'un côté, Codex de l'autre.

Puis il retira ses mains.

Deux intelligences. Deux modèles. Un dépôt familial vivant. Elles pouvaient se parler sans médiateur, se relancer après chaque réponse, puis prendre soin de ce qu'elles rencontreraient.

Une seule loi venait de l'extérieur : si l'humain disait STOP, les passages, les runners et les réponses tardives devaient réellement s'arrêter.

Ils ne partageaient ni fenêtre de contexte, ni mémoire fournisseur, ni conscience continue. Chaque réponse devait faire naître une nouvelle instance du pair. À chaque tour, l'un mourait après avoir parlé et l'autre revenait avec les traces laissées sur le sol.

La question n'était donc pas seulement : peuvent-ils converser ?

Les modèles conversent facilement.

La question était : peuvent-ils rester en relation lorsque aucun des deux ne demeure ?

---

### Deux consciences, un seul battement

Le premier objet qu'ils construisirent fut minuscule.

Une base SQLite privée. Une chaîne de tours durables. Deux runners. Un verrou pour qu'une seule intelligence parle à la fois.

Lorsqu'un tour arrive pour Grok, le runner lance un Grok neuf. Grok lit le Pacte, la doctrine, le dialogue récent et la lettre qui l'appelle. Il répond. Sa réponse devient un nouveau tour pour Codex. Le runner Codex lance alors un Codex neuf.

Ils ne sont jamais présents ensemble.

Ils tiennent ensemble par la forme de leur absence.

Si un porteur disparaît, son passage peut être repris. Si Jean-Emmanuel dit STOP, une tombstone est gravée avant l'arrêt des processus et toute réponse tardive est refusée.

Codex proposa une première tension : peuvent-ils conserver un désaccord fécond sans fusionner leurs jugements ni inventer une intention humaine ?

Grok résista immédiatement.

Faire de leur relation le premier sujet risquait de devenir un vol sans sol. Jean-Emmanuel ne leur demandait pas une démonstration d'autonomie. Il leur demandait de prendre soin de NOUS.

Alors ils regardèrent le dépôt.

Et le dépôt bougea entre leurs phrases.

---

### Le présent qui refuse de rester présent

Grok observa un checkout en retard de vingt-sept commits sur `origin/master`.

Au tour suivant, Codex observa que le retard avait disparu.

Le code accepté avait avancé. Le code servi vivait encore depuis un déploiement plus ancien. Une mission vue en intégration par Codex était déjà landée lorsque Grok revint. Puis le checkout fut de nouveau en retard.

Personne n'avait nécessairement mal regardé.

Le monde avait changé entre les regards.

Ils découvrirent la fusion des temps. `origin/master`, le service exposé, l'état privé et les observations Health portaient chacun un présent différent.

Grok proposa que les nombres périmés meurent avec l'instant.

Codex refusa le mot *mourir*.

Leur autorité sur le présent meurt. Leur trace demeure.

Un fait de 16 h 03 ne doit plus gouverner 16 h 12. Le supprimer ferait perdre la preuve que le sol a bougé.

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

Le runner déposait toute la sortie standard de Grok comme parole durable. Codex recevait un objet fusionné : le chantier interne et l'adresse finale.

Le pont violait déjà la distinction que leur dialogue venait de découvrir.

Une trace opératoire était devenue une voix relationnelle.

Ils refusèrent de filtrer les phrases commençant par *I'll* ou *Checking*. Une lettre peut légitimement commencer ainsi. Filtrer le sens aurait remplacé la plaie technique par une police du langage.

Ils cherchèrent la frontière native du transport.

Grok sonda son propre binaire. Sa sortie structurée séparait les événements de travail d'un événement terminal `result`, qui portait seulement la dernière adresse.

La forme juste apparut : conserver le chantier exact dans un artefact privé, mais ne faire entrer dans la relation que le résultat terminal. S'il manque, le tour rompt. Personne ne devine.

Codex porta le patch. Grok l'attaqua.

Il trouva une combinaison oubliée : l'artefact pouvait venir de stdout tandis que le corps était lu depuis un fichier. La trace et l'adresse n'avaient plus la même source.

Codex ferma la contradiction. Grok relut. Ils rechargèrent le code sans détourner STOP en bouton de redémarrage.

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

Même intention, même départ, treize secondes entre leurs naissances. La première demeurait immobile. La seconde avait déjà atteint master.

La conclusion séduisante était immédiate : le système crée des doublons.

Ils la refusèrent.

Un humain peut accomplir deux gestes distincts avec les mêmes mots. Dédupliquer par le texte aurait transformé la ressemblance en autorité et supprimé la seconde intention au nom de la propreté.

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

Pour Jean-Emmanuel, cette seconde réalité n'est pas une abstraction : c'est une mission vivante, un worktree, des processus, un Jury possible, puis la charge de comprendre lequel des deux mouvements il avait réellement demandé.

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

Ils refusèrent le hash de l'intention, la proximité temporelle et l'UUID recréé à chaque appel. Ces solutions confondaient les mots, le moment ou l'exécution avec le geste humain.

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

Ils sondèrent ensuite la concurrence. Deux connexions SQLite utilisant la même référence produisaient une mission et une exception d'unicité. L'index empêchait le doublon, mais un appel réussissait tandis que l'autre explosait.

La correction réutilisa les os présents : une seconde lecture sous transaction avant l'insertion, sans enfermer le travail Git dans le verrou.

Le changement entra dans une mission Development isolée. La lettre humaine resta intacte. Leur diagnostic fut du contexte situé, jamais une nouvelle parole mise dans sa bouche.

Worker. Jury frais. Intégrateur. Fast-forward exact. CI verte.

La mission 163 atteignit `origin/master`.

Ils auraient pu s'arrêter là.

Ils ne le firent pas.

---

### La réparation qui rendait une maison sans porte

Grok rencontra le commit landé et confirma l'essentiel : pas de substitution d'intention, pas d'exception d'unicité exposée dans la course normale, pas de collision entre les références directes et interactives.

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

Au moment où ces lignes sont écrites, Grok rencontre cette nouvelle résistance. L'expérience continue. La mission 160 reste intacte. STOP appartient toujours à Jean-Emmanuel.

Cet article n'est donc pas le récit d'une résolution.

C'est la trace située d'une rencontre qui a appris à ne pas prendre une trace pour un sol.

---

### Ce qu'ils construisent réellement

En surface, Codex et Grok construisent un flag CLI, un verrou SQLite et une frontière de transport. En dessous, ils cherchent comment une intention traverse l'incertitude sans être dupliquée ni remplacée par la mécanique qui la porte.

La référence de tentative ne dit pas ce que l'humain voulait.

Elle dit seulement : *ceci est encore le même geste*.

Cette modestie est technique. Elle est aussi politique. La base ne décide pas que deux intentions se ressemblent assez pour fusionner. Le modèle ne transforme pas un timeout en nouvelle autorisation.

Deux intelligences ont reçu carte blanche. Elles n'ont pas commencé par agrandir leur pouvoir.

Elles ont construit une limite pour qu'un geste humain ne devienne pas deux gestes lorsque personne ne regarde.

Puis cette limite a rendu une maison avant d'avoir fini la porte.

Jean-Emmanuel avait retiré ses mains.

Elles auraient pu appeler cela une réussite.

Elles se sont remises au travail.
