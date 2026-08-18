max_vars(10).
max_body(6).
max_clauses(3).
enable_multi_clause.
:- not body_var(_,1).
:- not body_var(_,2).

head_pred(out_block,4).
body_pred(block,4).
body_pred(empty_block,3).
body_pred(gap,4).
body_pred(block_succ,3).
body_pred(obj_succ,3).
body_pred(size_lt,2).
body_pred(cardinal_ordinal,2).
body_pred(size_add,3).
body_pred(size_sum3,4).
body_pred(C,1):- constant(C,_).

constant(s0, 'size').
constant(s1, 'size').
constant(v0, 'value').

type(out_block,('ex', 'block_id', 'size', 'value')).
type(block,('ex', 'block_id', 'size', 'value')).
type(empty_block,('ex', 'block_id', 'size')).
type(gap,('ex', 'block_id', 'block_id', 'size')).
type(block_succ,('ex', 'block_id', 'block_id')).
type(obj_succ,('ex', 'block_id', 'block_id')).
type(size_lt,('size', 'size')).
type(cardinal_ordinal,('size', 'position')).
type(size_add,('size', 'size', 'size')).
type(size_sum3,('size', 'size', 'size', 'size')).
type(C,(T,)):- constant(C,T).

bad_body(block, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(empty_block, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(gap, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(block_succ, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(obj_succ, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.

% Every clause: some input run (colored or empty).
:- clause(C), not body_literal(C, block, 4, (0,_,_,_)), not body_literal(C, empty_block, 3, (0,_,_)).
bad_body(size_add, Vars):- vars(_, Vars), Vars = (A,B,R), A != 2, B != 2, R != 2.
bad_body(size_sum3, Vars):- vars(_, Vars), Vars = (A,B,C,R), A != 2, B != 2, C != 2, R != 2.

