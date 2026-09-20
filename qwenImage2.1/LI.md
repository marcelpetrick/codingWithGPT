𝐐𝐰𝐞𝐧-𝐈𝐦𝐚𝐠𝐞 𝟐.𝟏 lokal getestet

Passend zum Wiesn-Start und weil heute der Feed voll mit dem neuen Release ist, habe ich mir auch ein paar Minuten zwecks Setup und Test gegönnt. (Falls mich jemand auf den Bildern erkennen kann, bitte kommentieren - ich finde nicht 😅)
#ComfyUI lag sowieso lokal vor; nur den neuesten Stand gepullt; Migration; bereit zum Rendern.
Die Orchestrierung über #ClaudeCode laufen lassen - keine Lust, die Workflows selber zu erstellen und zu pflegen. Per Sprachnotiz kurz beschrieben, wie viele Bilder welcher Auflösung ich gern hätte, dann Abendbrot vorbereitet. Aus der Ferne hörte man aber auf einmal die Lüfter ..

Ich weiss nicht, ob das für meine Zwecke ein Fortschritt ist. Also ich bin jetzt nicht hype-begeistert wie andere, welche ebenfalls heute einen Testlauf machten. Mit #Flux-Klein und Konsorten kam ich bisher recht weit. Für Illustrationen reichten sie als lokale Modelle.
Auch durch die Verwendung von Referenzbildern (bis zu drei) wurden gefühlt die Ergebnisse schlechter als bei rein textuellem Prompt.

Aktuell unklar, wie verwertbar das Ganze durch die Lizenz ist: "Qwen Research — non-commercial only", vorher "Apache-2.0"

Da von 512x512 über 1024x1024 bis 20248² Pixel alles gerendert werden kann, lief hier auch ein kurzer Benchmark: am besten kam ich hier mit 1024² Pixel Bildern bei 4 bis 10 Minuten aus.

### 3.1 Wall clock per image

```
smoke  01-visor        15.3s █
mp-01-wiesn           237.1s ████████████████
01-visor-reflection   243.1s █████████████████
05-nebula-scale       246.9s █████████████████
04-mission-poster     247.2s █████████████████
02-hull-typography    247.3s █████████████████
03-glove-texture      247.4s █████████████████
bavaria-02-golden     398.2s ████████████████████████████
2K probe (hull)       433.0s ██████████████████████████████
bavaria-01-daylight   663.0s ██████████████████████████████████████████████
                     └────────────────────────────────────────────┘
                     0                                          663s

ABANDONED
2K @ 30 steps        >1879s ███████████████████████████████████████████████▶
                            killed at step 19/30, still slowing
```

### 3.2 Cost per step by resolution

```
 512²    1.91 s/step  ██
1024²    8.21 s/step  ████████
2048²   54.16 s/step  ██████████████████████████████████████████████████
                      └────────────────────────────────────────────────┘
                      0                                             55 s
```

### 3.3 Cost per step by machine state — identical work

```
warm, 22 GB cache, no swap      8.2 s/step  ████████
cache re-warming, 5.7 GB swap  13.3 s/step  █████████████
cold, cache evicted, swapping  22.1 s/step  ██████████████████████
                                            └────────────────────┘
                                            0                  22 s
```

### 4.3 Resolution scaling turns superlinear past 1024²

| Step up | Pixels | Time | Behaviour |
|---|---|---|---|
| 512² → 1024² | 4× | 4.3× | ~linear |
| 1024² → 2048² | 4× | 6.6× | superlinear — quadratic attention appearing |
