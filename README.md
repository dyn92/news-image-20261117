# news-image-20261117

[make.fun](https://make.fun) · [Bounty: news-image-20261117](https://make.fun/bounty/news-image-20261117) · $250 in USDC

A program that draws a 1024x1024 newspaper poster summing up Tuesday 17 November 2026 in one image: a dated header plus six story panels (Kerch bridge, Iran drones at Bahrain, the Xi-Trump-Putin summit, Japan scrambling fighters, UK sanctions on settlement builders, and the US emergency alert test), each with a hand-drawn pictogram, a headline and one factual sub-label. Pure Python standard library, no network, byte-identical output on every run.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

This writes `out/entry.png` (1024x1024, under 1 MiB).

Entered on make.fun — "Sum up 17 November's world news in one image", $250 in USDC.
