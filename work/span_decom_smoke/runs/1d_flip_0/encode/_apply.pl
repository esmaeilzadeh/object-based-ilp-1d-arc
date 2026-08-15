:- dynamic out_block/4.
out_block(V0,V1,V2,V3):- empty(V0,V1),in_block(V0,V1,V2,V3).
out_block(V0,V1,V2,V3):- in_col_succ(V0,V4,V1),in_block(V0,V2,V4,V3).
out_block(V0,V1,V2,V3):- in_block(V0,V4,V2,V3),in_col_succ(V0,V1,V4).