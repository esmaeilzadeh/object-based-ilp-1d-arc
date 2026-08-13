:- dynamic out_block/5.
out_block(V0,V1,V2,V3,V4):- v1(V4),gap(V0,V5,V1,V2),block(V0,V1,V3,V6).
out_block(V0,V1,V2,V3,V4):- block(V0,V1,V3,V4),s4(V2),size_odd(V3).
out_block(V0,V1,V2,V3,V4):- block(V0,V1,V2,V4),gap(V0,V5,V8,V3),gap(V0,V6,V5,V7).
out_block(V0,V1,V2,V3,V4):- v6(V4),size_add(V2,V3,V5),block(V0,V1,V5,V6).
