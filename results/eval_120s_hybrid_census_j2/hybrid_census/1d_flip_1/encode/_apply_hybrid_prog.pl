:- dynamic out_block/5.
:- dynamic out_pixel/4.
out_block(V0,V1,V2,V3,V4):- block(V0,V1,V3,V4),sm1(V2).

out_pixel(V0,V1,V2,V3):- unit(V0,V1,V3),block(V0,V4,V2,V5).

