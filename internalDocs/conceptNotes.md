### Proposed repo structure -- intitial

mainTranscoder.py
├── transcoders
│ ├── from_ADM_XML.py
│ ├── from_AMBI.py
│ ├── from_MPEGH.py
│ ├── to_ADM_XML.py
│ ├── to_AMBI.py
│ ├── to_MPEGH.py
│ └── transcodersINFO.md
└── utils
├── OSC.py
└── parsingHelper.py

### Scene structure:

node convention -> x.y
X = node group
Y = node hierarchy. 1 = parent. Top down hierarchy

Timestep xxx:
{
{node: 1.1,
Type: audio_object,
Az: xxx
El: xxx
Radius: xxx
},
{node: 1.2,
type: spectral_features,
Centroid: xxx,
Flux: xxx,
etc: xxx}
{node: 2.1,
Type: audio_object,
Az: xxx
El: xxx
Radius: xxx
},
{node 2.2,
Type: agent_state,
Data: xxx
},
{node 3.1,
Type: LFE
}

}

}
