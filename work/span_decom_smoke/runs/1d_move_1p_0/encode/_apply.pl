:- dynamic out_block/4.
out_block(V0,V1,V2,V3):- block(V0,V4,V2,V3),succ(V4,V1).