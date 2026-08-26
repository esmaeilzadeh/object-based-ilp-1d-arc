# Census-routed hybrid ILP for 1D-ARC

Per-instance induction over 1D grids: a train-grid census routes each task to an object language or a pixel language, then a learned program is decoded to pixels.

## Language

### Induction artifacts

**Background knowledge**:
Searchable facts about one instance’s input objects (or pixels) that induction may consult.
_Avoid_: Bias, predicate inventory, geometry tables kept only for decode

**Bias**:
The search grammar that says which background-knowledge predicates may appear in a clause body.
_Avoid_: Background knowledge, predicate inventory

**Predicate inventory**:
The catalog of predicate names the codebase uses to type heads and object-body predicates.
_Avoid_: Background knowledge, bias

**Emit-allowlist identity**:
Searchable object background knowledge contains exactly the predicates the object bias may use.
_Avoid_: Extra facts the learner cannot mention

### Object language

**Object body language**:
Individuals plus succession, measured gap, and less-than / add on sizes: `block`, `bind`, `obj_succ`, `gap`, `size_lt`, `size_add`, `cardinal_ordinal`.
_Avoid_: Pixel `in` / `out` as the object-road vocabulary

**Size less-than**:
A comparison between two size values (lengths, gaps, offsets).
_Avoid_: Treating a size as a block id
