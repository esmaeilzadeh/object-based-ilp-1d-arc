out_block(V0,V1,V2,V3,V4):- s2(V2),s20(V3),block(V0,V1,V5,V4).
out_block(V0,V1,V2,V3,V4):- size_lt(V3,V2),block(V0,V1,V3,V4).
out_block(V0,V1,V2,V3,V4):- s6(V2),s16(V3),block(V0,V1,V5,V4).
