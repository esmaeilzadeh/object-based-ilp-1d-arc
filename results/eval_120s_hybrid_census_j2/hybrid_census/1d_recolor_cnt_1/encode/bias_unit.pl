max_vars(10).
max_body(6).
max_clauses(3).
enable_multi_clause.
:- not body_var(_,1).
:- not body_var(_,2).

head_pred(out_pixel,4).
body_pred(unit,3).
body_pred(block,4).
body_pred(gap,4).
body_pred(obj_succ,3).
body_pred(size_lt,2).
body_pred(cardinal_ordinal,2).
body_pred(size_add,3).
body_pred(size_sum3,4).
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
constant(sm2, 'size').
constant(sm3, 'size').
constant(sm4, 'size').
constant(sm5, 'size').
constant(sm6, 'size').
constant(sm7, 'size').
constant(sm8, 'size').
constant(sm9, 'size').
constant(sm10, 'size').
constant(sm12, 'size').
constant(sm13, 'size').
constant(sm14, 'size').
constant(sm16, 'size').
constant(sm17, 'size').
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

type(out_pixel,('ex', 'unit_id', 'size', 'value')).
type(unit,('ex', 'unit_id', 'value')).
type(block,('ex', 'block_id', 'size', 'value')).
type(gap,('ex', 'block_id', 'block_id', 'size')).
type(obj_succ,('ex', 'block_id', 'block_id')).
type(size_lt,('size', 'size')).
type(cardinal_ordinal,('size', 'position')).
type(size_add,('size', 'size', 'size')).
type(size_sum3,('size', 'size', 'size', 'size')).
type(C,(T,)):- constant(C,T).

bad_body(unit, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(block, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(gap, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(obj_succ, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.

% Every clause: unit must use head Pid (var 1).
:- clause(C), not body_literal(C, unit, 3, (0,1,_)).
bad_body(size_add, Vars):- vars(_, Vars), Vars = (A,B,R), A != 2, B != 2, R != 2.
bad_body(size_sum3, Vars):- vars(_, Vars), Vars = (A,B,C,R), A != 2, B != 2, C != 2, R != 2.

