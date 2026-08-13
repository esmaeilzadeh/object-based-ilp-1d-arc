max_vars(10).
max_body(6).
max_clauses(3).
enable_multi_clause.
:- not body_var(_,1).
:- not body_var(_,2).
:- not body_var(_,3).

head_pred(out_block,4).
body_pred(block,4).
body_pred(largest,2).
body_pred(size_add,3).
body_pred(size_lt,2).
body_pred(offset_pos,3).
body_pred(cardinal_ordinal,2).
body_pred(size_even,1).
body_pred(size_odd,1).
body_pred(C,1):- constant(C,_).

constant(s0, 'size').
constant(s1, 'size').
constant(s2, 'size').
constant(s3, 'size').
constant(s4, 'size').
constant(s5, 'size').
constant(s6, 'size').
constant(s7, 'size').
constant(s8, 'size').
constant(s9, 'size').
constant(s10, 'size').
constant(s11, 'size').
constant(s12, 'size').
constant(s13, 'size').
constant(s14, 'size').
constant(s15, 'size').
constant(s16, 'size').
constant(v0, 'value').
constant(v1, 'value').
constant(v2, 'value').
constant(v3, 'value').
constant(v4, 'value').
constant(v5, 'value').
constant(v6, 'value').
constant(v7, 'value').
constant(v8, 'value').
constant(v9, 'value').

type(out_block,('ex','position','size','value')).
type(block,('ex','position','size','value')).
type(largest,('ex','position')).
type(size_add,('size','size','size')).
type(size_lt,('size','size')).
type(offset_pos,('position','size','position')).
type(cardinal_ordinal,('size','position')).
type(size_even,('size',)).
type(size_odd,('size',)).
type(C,(T,)):- constant(C,T).

:- clause(C), not body_literal(C, block, 4, (0,_,_,_)).
bad_body(offset_pos, Vars):- vars(_, Vars), Vars = (A,_,R), A != 1, R != 1.
bad_body(size_add, Vars):- vars(_, Vars), Vars = (A,B,R), A != 2, B != 2, R != 2.

