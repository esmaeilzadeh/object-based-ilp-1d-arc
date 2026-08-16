max_vars(10).
max_body(6).
max_clauses(3).
enable_multi_clause.
:- not body_var(_,1).
:- not body_var(_,2).
:- not body_var(_,3).

head_pred(out_block,5).
body_pred(block,4).
body_pred(size_lt,2).
body_pred(cardinal_ordinal,2).
body_pred(size_add,3).
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
constant(s17, 'size').
constant(s18, 'size').
constant(s19, 'size').
constant(s20, 'size').
constant(s21, 'size').
constant(s22, 'size').
constant(s23, 'size').
constant(s24, 'size').
constant(s25, 'size').
constant(s26, 'size').
constant(s27, 'size').
constant(s28, 'size').
constant(s29, 'size').
constant(s30, 'size').
constant(s31, 'size').
constant(s32, 'size').
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

type(out_block,('ex', 'block_id', 'size', 'size', 'value')).
type(block,('ex', 'block_id', 'size', 'value')).
type(size_lt,('size', 'size')).
type(cardinal_ordinal,('size', 'position')).
type(size_add,('size', 'size', 'size')).
type(C,(T,)):- constant(C,T).

bad_body(block, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.

% Every clause: block must use head Bid (var 1).
:- clause(C), not body_literal(C, block, 4, (0,1,_,_)).
bad_body(size_add, Vars):- vars(_, Vars), Vars = (A,B,R), A != 2, A != 3, B != 2, B != 3, R != 2, R != 3.

