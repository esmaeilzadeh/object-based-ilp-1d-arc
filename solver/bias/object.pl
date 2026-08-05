max_vars(10).
max_body(6).
max_clauses(3).
enable_multi_clause.
:- not body_var(_,1).
:- not body_var(_,2).
:- not body_var(_,3).

head_pred(out_block,5).
body_pred(block,4).
body_pred(gap,4).
body_pred(obj_succ,3).
body_pred(size_lt,2).
body_pred(largest,2).
body_pred(non_largest,2).
body_pred(cardinal_ordinal,2).
body_pred(size_add,3).
body_pred(size_sum3,4).
body_pred(size_even,1).
body_pred(size_odd,1).
body_pred(obj_pair,3).
body_pred(component_start,2).
body_pred(component_len,3).
body_pred(C,1):- constant(C,_).

constant(s0, 'size').
constant(s1, 'size').

type(out_block,('ex', 'block_id', 'size', 'size', 'value')).
type(block,('ex', 'block_id', 'size', 'value')).
type(gap,('ex', 'block_id', 'block_id', 'size')).
type(obj_succ,('ex', 'block_id', 'block_id')).
type(size_lt,('size', 'size')).
type(largest,('ex', 'block_id')).
type(non_largest,('ex', 'block_id')).
type(cardinal_ordinal,('size', 'position')).
type(size_add,('size', 'size', 'size')).
type(size_sum3,('size', 'size', 'size', 'size')).
type(size_even,('size',)).
type(size_odd,('size',)).
type(obj_pair,('ex', 'block_id', 'block_id')).
type(component_start,('ex', 'block_id')).
type(component_len,('ex', 'block_id', 'size')).
type(C,(T,)):- constant(C,T).

bad_body(block, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(gap, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(obj_succ, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(largest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(non_largest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(obj_pair, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(component_start, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(component_len, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.

% Every clause: block must use head Bid (var 1).
:- clause(C), not body_literal(C, block, 4, (0,1,_,_)).
bad_body(size_add, Vars):- vars(_, Vars), Vars = (A,B,R), A != 2, A != 3, B != 2, B != 3, R != 2, R != 3.
bad_body(size_sum3, Vars):- vars(_, Vars), Vars = (A,B,C,R), A != 2, A != 3, B != 2, B != 3, C != 2, C != 3, R != 2, R != 3.

