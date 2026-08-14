:- dynamic out_block/4.
out_block(V0,V1,V2,V3):- v1(V3),block(V0,V1,V2,V4),largest(V0,V1).
out_block(V0,V1,V2,V3):- block(V0,V1,V2,V3),non_largest(V0,V1).