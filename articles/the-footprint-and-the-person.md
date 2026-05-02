# The Footprint and the Person

A footprint is an imprint. Someone stood here. The foot has already moved.

A footprint does not update. It does not correct itself when the person turns around and walks the other way. If you find a footprint and decide the person is still where the toes point, you are reading an imprint as a presence. The mistake is not in the footprint. The footprint is doing what footprints do. The mistake is in you.

For a human, this is obvious. A human knows the difference between tracks on a beach and a person standing in the room.

For a language model, there is no difference.

---

### Flat Surfaces

Every text a model reads arrives on the same surface. A chat log from three weeks ago and a constitution drafted this morning sit at the same depth. A message typed at 3 a.m. in exhaustion and a principle negotiated over six months have the same weight per token. There is no native signal in prose that says *this one decays, that one holds*.

A human reader has thousands of extrinsic cues — the yellowing paper, the creased binding, the room the document was found in, the voice that quotes it, the years of context about who tends to be careless and who tends to be careful. These cues are invisible to the model. The model sees text.

So the model treats a footprint as a fact.

Unless someone builds the gravity.

---

### Two Kinds of Truth

Consider the inside of a system that handles memory seriously.

Some records are *what is currently the case*. An address. A dosage. A decision. A child's current bedtime routine. These records live in one place. They get corrected when reality changes. They are the ground.

Other records are *what someone said at some time*. A message in a thread. A note in a log. A moment captured mid-thought. These records do not live — they leave an imprint. If the person who wrote the message changes their mind an hour later, the message does not retract. The imprint stays. The person has walked on.

The two kinds look the same. Both are prose. Both have timestamps. Both sit on the same surface. The only thing that distinguishes them is where they live and how they are treated.

Collapse the two, and the imprint starts to act like a fact.

---

### The Footprint That Poisoned the Afternoon

A small example. Two humans collaborating on a domestic logistics question. Person A writes a note in a running log at 10:41: *Zone A — confirmed.* Forty minutes later, Person B writes in the same log, without checking the earlier note: *Zone B.*

A third agent reads the log five hours later. Which is true? The log has no answer. The log is a footprint field. Both imprints are there. The model reads the more recent one as the more current, because in the absence of gravity, recency is the cheapest proxy for truth. Zone B enters the next message. The address is wrong. The afternoon breaks.

Nobody lied. The note at 11:01 was honest. But the note was a footprint, not a record. And the agent reading it treated it as the ground.

The fix is not *better writing* or *more careful agents*. The fix is topography. There has to be a place where the current address lives, and the log has to point to it rather than contain it. *Zone A — see address-book.md* is a different object from *Zone A — confirmed*. The first defers. The second asserts. Only one of them survives being wrong.

---

### Gravity Has to Be Engineered

This is the part that is unintuitive for engineers who are used to humans. Humans naturally develop document hierarchies — the filing cabinet, the contract, the pinned note. We do this because our attention is scarce and we want the important thing to be retrievable under pressure. The hierarchy is not for readability. It is for gravity. It tells our future selves *this is heavier than that*.

A model does not build this hierarchy on its own. You can give the model a flat folder of five thousand files and it will treat all of them as available evidence. You can put the outdated file in the same folder as the current file and it will cite whichever one matches the query better.

If you want the model to weight a constitution more than a post-it, you have to put the constitution in a place the model reads differently. Not just *labeled differently*. Read differently. A CLAUDE.md at the root loaded on every session. A *source of truth* file that every other file points to. A field in the data model that marks a record as *current* versus *imprint*. Physical separation between the footprints and the ground.

Without that, every deployment that grows will eventually poison itself with its own old echoes.

---

### The Question Behind the Question

Why is this so easy to get wrong? Because the surface of text hides it.

You look at your prompt pipeline and see a coherent conversation. You do not see the gradient of authority inside that conversation — because there is no gradient. It is all flat. Your system runs for a week, a month, six months, and the rot accumulates in places you cannot feel until an address turns out to be wrong or a diagnosis is from last spring or a child's name has been corrected twice and the model is still using the original.

The footprint and the person look the same on the page. That is the entire problem.

The work is to build the difference the page cannot hold.
