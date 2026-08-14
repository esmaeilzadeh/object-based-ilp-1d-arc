out_block(V0,V1,V2,V3):- out_succ(V0,V4,V1),block(V0,V4,V2,V3).
out_block(V0,V1,V2,V3):- obj_succ(V0,V1,V4),block(V0,V4,V2,V3).