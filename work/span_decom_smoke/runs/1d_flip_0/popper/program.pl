out_block(V0,V1,V2,V3):- block(V0,V7,V2,V3),block(V5,V6,V9,V4),obj_pair(V8,V7,V6),add(V9,V7,V1).
out_block(V0,V1,V2,V3):- block(V0,V4,V2,V3),obj_succ(V0,V1,V4).
