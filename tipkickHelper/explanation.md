# How the Tipkick Helper Process Works

A reference diagram for anyone running the agent setup against this repo.
Run this process periodically — at squad-announcement time, after friendlies,
and whenever major injury news drops.

---

## 1 — Overall pipeline

```mermaid
flowchart TD
    A[User opens chat\n in tipkickHelper/] --> B[Agent reads AGENTS.md\n + pool_rules.md\n + strategy.md]
    B --> C{New information\nto process?}
    C -- Yes --> D[Classify the drop]
    C -- No: research run --> E[Fan out subagents]
    E --> F1[Subagent 1:\nInjuries & squad news]
    E --> F2[Subagent 2:\nOdds / prediction markets]
    E --> F3[Subagent 3:\nFriendly results & form]
    E --> F4[Subagent 4:\nGroup analysis & dark horses]
    F1 & F2 & F3 & F4 --> G[Synthesise findings]
    G --> H[Update docs]
    D --> H
    H --> I{Picks affected?}
    I -- Yes --> J[Update my_picks.md\nflag every change]
    I -- No --> K[Update model_picks.md\nor strategy.md only]
    J & K --> L[Commit locally\nnever push without asking]
```

---

## 2 — Data sources & where they flow

```mermaid
flowchart LR
    subgraph External["External Sources"]
        PM[Polymarket\nKalshi]
        ESPN[ESPN / FOX /\nCBS Sports]
        SKY[Sky Sports\nbeIN Sports]
        FIFA[FIFA.com\nofficial]
        WST[World Soccer Talk\nGoal.com / Rotowire]
    end

    subgraph Classification["Classification"]
        ODD[Odds /\npower ranking]
        INJ[Injury /\nsquad news]
        FORM[Friendly\nresults]
        RULE[Pool rule\nchange]
        GUT[User gut\nfeel]
    end

    subgraph Docs["Documentation files"]
        FAV[favorites.md]
        GRP[groups.md]
        DH[dark_horses.md]
        HOSTS[hosts.md]
        PR[pool_rules.md]
        STR[strategy.md]
        SRC[sources.md]
        MP[model_picks.md]
        MY[my_picks.md ⚠️]
    end

    PM --> ODD
    ESPN --> ODD & INJ & FORM
    SKY --> INJ & FORM
    FIFA --> INJ & RULE
    WST --> INJ & FORM

    ODD --> FAV
    INJ --> FAV & GRP & DH
    FORM --> FAV & GRP
    RULE --> PR & STR
    GUT --> MY

    FAV & GRP & DH --> MP
    MP --> MY

    External --> SRC
```

> ⚠️ `my_picks.md` is the only file the user fills in directly.
> Every agent edit to it must be flagged in the chat.

---

## 3 — Strategy selection logic

```mermaid
flowchart TD
    START([Start]) --> Q1{How many\nparticipants?}
    Q1 -- "≤ 13" --> LOSS[5th place = net loss\nMinimum viable: aim for top-3]
    Q1 -- "14–25" --> GOOD["Top-5 = top 20–38%\nCash-out floor is real\n→ Strategy A has positive EV"]
    Q1 -- "26–50" --> MID["Top-5 = top 10–19%\n→ A or B depending on goal"]
    Q1 -- "> 50" --> HARD["Top-5 = top < 10%\n→ Strategy B (one swing)\nbecomes mandatory"]

    GOOD --> GOAL{Primary goal?}
    MID --> GOAL
    GOAL -- "Don't lose money" --> A[Strategy A:\nPure chalk + consensus bonuses]
    GOAL -- "Win the pool" --> B[Strategy B:\nChalk + one contrarian swing\ne.g. champion or one semi-finalist]

    A --> LOCK[🔒 Lock before opening kickoff\n11 Jun 2026 21:00 CET]
    B --> LOCK

    LOCK --> NOSWITCH["No mid-tournament switches.\nPer-match picks adjust for injuries\nbut the playbook stays."]
```

> Current pool: **25 participants** → Strategy A locked 2026-05-15.

---

## 4 — Per-match pick decision tree

```mermaid
flowchart TD
    MATCH([Upcoming match]) --> INJ2{Major injury /\nsuspension\nsince last update?}
    INJ2 -- Yes --> RERANK[Re-rank favorites\nfor this specific match]
    INJ2 -- No --> DEF[Use default chalk]

    RERANK --> CHALK{Is the favorite\nstill the chalk?}
    CHALK -- Yes --> DEF
    CHALK -- No --> SWAP[Pick next-best\nfavorite — stay within\nStrategy A philosophy]

    DEF --> SCORE{Scoreline heuristic}
    SWAP --> SCORE

    SCORE --> BIG{Big mismatch?\n e.g. France vs Iraq}
    BIG -- Yes --> S1["Pick 3–0\n(blowout is justified)"]
    BIG -- No --> CLOSE{Teams evenly\nmatched?}
    CLOSE -- Yes --> S2["Pick 1–1"]
    CLOSE -- No --> FAV2{Moderate\nfavorite?}
    FAV2 -- Yes --> S3["Pick 2–0 or 2–1"]
    FAV2 -- No --> S4["Pick 1–0"]
```

---

## 5 — Agent research trigger checklist

When to run the fan-out research pass:

```mermaid
flowchart LR
    T1["📅 After squad\nannouncements\n(~1 June)"]
    T2["🏥 Major injury\nbreaking news"]
    T3["⚽ After friendly\nresults"]
    T4["📊 Odds move > 2 pp\non Polymarket"]
    T5["📧 Admin email\n(rule change / count)"]
    T6["🔁 Weekly refresh\nduring tournament"]

    T1 & T2 & T3 & T4 & T5 & T6 --> RUN["Run fan-out:\n4 parallel subagents\n(injuries / odds / form / groups)"]
    RUN --> UPDATE["Update affected .md files\nCheck my_picks.md for\nforced deviations\nCommit locally"]
```

---

## 6 — Bonus pick EV logic

```mermaid
flowchart TD
    BP([Bonus pick slot]) --> Q{How many pool\nparticipants pick\nthe same team?}
    Q -- "> 40% of pool" --> COPY["Chalk pick:\nyou match the field\nbut don't lose ground"]
    Q -- "10–30% of pool" --> MID2["Moderate contrarian:\n+EV if team qualifies\n- small floor risk"]
    Q -- "< 10% of pool" --> SWING["High-variance swing:\nbig upside, big floor risk\nUse max ONE of these"]

    COPY --> NOTE1["Safe for semi-finalist\nand group winner slots"]
    MID2 --> NOTE2["Portugal champion\nis in this zone at N=25"]
    SWING --> NOTE3["Under Strategy A:\nzero swing picks.\nOnly allowed under B."]
```

---

## 7 — File dependency map

```mermaid
graph TD
    PR[pool_rules.md\nscoring + tie-break] --> STR[strategy.md\nmath + playbook]
    STR --> MP[model_picks.md\ndata-driven defaults]
    FAV[favorites.md\nodds + form + injuries] --> MP
    GRP[groups.md\ngroup reads] --> MP
    DH[dark_horses.md\ncontrarian options] --> MP
    HOSTS[hosts.md\nhome advantage] --> MP
    MP --> MY["my_picks.md\n★ USER'S SHEET ★"]
    SRC[sources.md\nlinks] -.-> FAV & GRP & DH
    AGENTS[AGENTS.md\nworkflow guide] -.-> ALL["all files"]
```

---

*Last updated: 2026-06-02. Tournament: 11 June – 19 July 2026.*
