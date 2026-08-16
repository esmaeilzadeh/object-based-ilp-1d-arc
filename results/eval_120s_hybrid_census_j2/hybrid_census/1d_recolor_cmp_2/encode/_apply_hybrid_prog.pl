:- dynamic out_block/5.
:- dynamic out_pixel/4.
out_block(V0,V1,V2,V3,V4):- s0(V2),block(V0,V1,V3,V5),block(V0,V7,V6,V4),size_lt(V3,V6).
out_block(V0,V1,V2,V3,V4):- s0(V2),v5(V4),s7(V3),block(V0,V1,V3,V5).


