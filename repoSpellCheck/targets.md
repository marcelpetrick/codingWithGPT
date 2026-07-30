# Spellcheck Targets

High-value repositories checked with `main.py` (codespell). List grows over time;
updated after every batch of 5 repos scanned.

| # | Repo | Category | Popularity / Brand | Issues Found | Status |
|---|------|----------|---------------------|---------------|--------|
| 1 | https://github.com/langchain-ai/langchain | AI/LLM framework | Very high (~100k★, de-facto LLM app framework) | 54 | scanned — README.md has a real one: `capabilites ==> capabilities` |
| 2 | https://github.com/ollama/ollama | AI/LLM tooling | Very high (~130k★, top local-LLM runner) | 242 | scanned — mostly gen-code/test-fixture noise, needs manual triage |
| 3 | https://github.com/ggerganov/llama.cpp | AI/LLM inference | Very high (~70k★, foundational LLM inference engine) | 1113 | scanned — concentrated in CANN/arch backend source, likely var-name false positives |
| 4 | https://github.com/huggingface/transformers | AI/ML standard library | Extremely high (~135k★, industry-standard NLP/ML lib) | 752 | scanned — spread across tests/model code, needs manual triage |
| 5 | https://github.com/vllm-project/vllm | AI/LLM inference | High (~30k★, fast-rising LLM serving engine) | 276 | scanned — spread across csrc/model code, needs manual triage |
| 6 | https://github.com/microsoft/autogen | AI/LLM agents | High (Microsoft-backed, trending agent framework) | 160 | scanned — real hits incl. `funciton ==> function`, `tempature ==> temperature`, `supercedes ==> supersedes` in sample .cs files |
| 7 | https://github.com/pytorch/pytorch | ML standard library | Extremely high (~85k★, Meta-backed, core ML framework) | 54 | scanned — real hits incl. `cant ==> can't`, `referencable ==> referenceable` (mostly in vendored cpython test suite) |
| 8 | https://github.com/kubernetes/kubernetes | Infra standard library | Extremely high (~110k★, CNCF flagship project) | 2613 | scanned — real hits incl. `convertable ==> convertible`, `poped ==> popped`, `theyre ==> they're`; concentrated in a few test files, needs triage |
| 9 | https://github.com/facebook/react | Frontend standard library | Extremely high (~230k★, Meta-backed, top frontend framework) | 632 | scanned — real hits incl. `accessibiliy ==> accessibility`, `essentialy ==> essentially`; concentrated in test fixtures |
| 10 | https://github.com/golang/go | Language standard library | Extremely high (Google-backed, Go language itself) | 4946 | scanned — real hits incl. `cant ==> can't`; heavily concentrated in compiler test files, needs triage |
| 11 | https://github.com/openai/openai-python | AI/LLM SDK | Extremely high (OpenAI's official Python SDK) | 50 (3 confirmed real) | **user-verified & fixed** — only 3 of 50 hits were real typos (incl. `maxium ==> maximum`, `interpeter ==> interpreter`); the rest were developer's-choice spelling/style, not errors |
| 12 | https://github.com/anthropics/anthropic-sdk-python | AI/LLM SDK | High (Anthropic's official Python SDK) | 17 | scanned — real hit: `interpeter ==> interpreter` in CHANGELOG (same typo as openai-python's, likely shared codegen tooling) |
| 13 | https://github.com/run-llama/llama_index | AI/LLM framework | High (~40k★, leading RAG framework) | 156 | scanned — spread across integrations/tests, needs triage |
| 14 | https://github.com/crewAIInc/crewAI | AI/LLM agents | High, fast-rising (popular multi-agent framework) | 647 | scanned — real hit: `behaivor ==> behavior` in top-level AGENTS.md |
| 15 | https://github.com/comfyanonymous/ComfyUI | AI/image-gen tooling | High, fast-rising (leading node-based diffusion UI) | 149 | scanned — real hits: `isnt ==> isn't`, `unqiue ==> unique`, `indicies ==> indices`, `tesselation ==> tessellation` |
| 16 | https://github.com/AUTOMATIC1111/stable-diffusion-webui | AI/image-gen tooling | Very high (~145k★, the original SD web UI) | 23 | scanned — clean signal, real hits: `extention ==> extension`, `stoping ==> stopping`, `eror ==> error`, `overriden ==> overridden` in CHANGELOG.md |
| 17 | https://github.com/nodejs/node | Language/runtime standard library | Extremely high (~110k★, Node.js runtime) | 1342 | scanned — real hits: `desctructor ==> destructor`, `mulitple ==> multiple`, `strng ==> string`; bulk is historical CHANGELOG text |
| 18 | https://github.com/django/django | Web framework standard library | Extremely high (~83k★, flagship Python web framework) | 446 | scanned — real hits: `dne ==> done` and `Gage ==> Gauge` in AUTHORS, `acount ==> account` |
| 19 | https://github.com/numpy/numpy | Scientific computing standard library | Extremely high (foundational Python numerical library) | 2059 | scanned — real hits: `indx ==> index` (repeated), `homogenous ==> homogeneous` in changelog; concentrated in a few core src files |
| 20 | https://github.com/rust-lang/rust | Language standard library | Extremely high (Rust language itself) | 3302 | scanned — real hit: `atleast ==> at least` in rustc-dev-guide docs; bulk concentrated in compiler test/codegen files |
| 21 | https://github.com/Shubhamsaboo/awesome-llm-apps | AI/LLM curated list | Very high (~125k★, widely-shared LLM apps/agents collection) | 379 | scanned — real hits: `wiht ==> with`, `incase ==> in case`, `furthur ==> further`; bulk is a bundled webpack build artifact + pnpm lockfiles (low-value) |
| 22 | https://github.com/google/langextract | AI/LLM tooling | High, Google-backed (structured extraction from text via LLMs) | 4 | scanned — clean; real hit: `treshold ==> threshold` in a test file |
| 23 | https://github.com/kvcache-ai/ktransformers | AI/LLM inference | High, fast-rising (heterogeneous LLM inference/fine-tuning optimizer) | 298 | scanned — real hit: `Copyrigth ==> Copyright` in CUDA kernel license headers; some duplication from an `archive/` copy of old code |
| 24 | https://github.com/MoonshotAI/kimi-cli | AI/LLM tooling | High, fast-rising (Moonshot AI's Kimi coding CLI agent) | 31 (0 confirmed real) | **user-verified** — zero real flaws; all 31 hits were false positives / developer's choice (incl. `datas` in a PyInstaller `.spec` file, which is PyInstaller's own API name) |
| 25 | https://github.com/thinking-machines-lab/tinker-cookbook | AI/LLM tooling | High-profile lab (Thinking Machines Lab post-training recipes) | 259 | scanned — bulk is intentional multilingual example-fixture text; note: `Expresso` flagged as `Espresso` is a **false positive** (Expresso is a real speech-dataset name) |
| 26 | https://github.com/microsoft/semantic-kernel | AI/LLM framework | Very high (Microsoft's LLM orchestration SDK) | 2172 | scanned — real hits: `daa ==> data`, `deveop ==> develop`; bulk is a bundled GPT-2/RoBERTa `vocab.bpe` resource file (data, not prose) |
| 27 | https://github.com/unslothai/unsloth | AI/LLM tooling | Very high, fast-rising (popular efficient LLM fine-tuning library) | 175 | scanned — mostly `unparseable` (codespell dictionary nit, not a real error — see note below) |
| 28 | https://github.com/PostHog/posthog | Product analytics standard tool | Very high (well-known open-source analytics platform) | 2891 | scanned — real hits: `Bulid ==> Build`, `COPYed ==> copied` in Dockerfile; bulk is bundled webpack test-fixture JS/sourcemaps |
| 29 | https://github.com/ocornut/imgui | C++ GUI standard library | Extremely high (~75k★, ubiquitous "Dear ImGui" library) | 85 | scanned — clean, real hits: `overlayed ==> overlaid`, `canoncialize ==> canonicalize`, `alpha-numeric ==> alphanumeric` (latter in bundled GLFW dep) |
| 30 | https://github.com/catchorg/Catch2 | C++ testing standard library | High, long-standing (widely used C++ test framework) | 65 | scanned — real hit: `Coud ==> Could`; note: `SEH ==> SHE` is a **false positive** (SEH = Structured Exception Handling, a real Windows API term) |

> Note on round 3 sourcing: a live GitHub-trending fetch returned several repos with implausible star counts from obscure accounts (star-inflation/spam pattern) — those were excluded. The 10 above were cross-checked against known, reputable projects/orgs instead.

## Notes
- "Issues Found" = count of `word ==> fix` lines codespell reports (one per misspelling occurrence).
- Runs use shallow clones (`depth=1`) via the existing `main.py`. Kept clones live in `runs/clones/` (git-ignored, not committed) — inspect with `git -C runs/clones/<dir> diff` to review/revert individual fixes.
- Skip list excludes generated/vendored/binary noise (minified JS bundles, vendored libs, data files, non-English localized docs) to keep counts meaningful; some remaining hits in code-heavy files (variable/identifier names, model jargon) may still be false positives — review the diff before trusting a number.
- Update cadence: after every 5 repos scanned.

## Clone directory map (for reviewing diffs)
| Repo | Clone dir under `runs/clones/` |
|------|-------------------------------|
| langchain-ai/langchain | codespell-run-d0f8wr6y |
| ollama/ollama | codespell-run-rqbbexuy |
| ggerganov/llama.cpp | codespell-run-b_37bp8y |
| huggingface/transformers | codespell-run-772p65rw |
| vllm-project/vllm | codespell-run-eququ82n |
| microsoft/autogen | codespell-run-xd77mpvt |
| pytorch/pytorch | codespell-run-80edputg |
| kubernetes/kubernetes | codespell-run-9_f55aa0 |
| facebook/react | codespell-run-y1oncq7w |
| golang/go | codespell-run-31p7218d |
| openai/openai-python | codespell-run-h5dgpj5h |
| anthropics/anthropic-sdk-python | codespell-run-5fbyaw_e |
| run-llama/llama_index | codespell-run-4dt2xnuj |
| crewAIInc/crewAI | codespell-run-_sixsjrs |
| comfyanonymous/ComfyUI | codespell-run-gxtgvvnf |
| AUTOMATIC1111/stable-diffusion-webui | codespell-run-lsjdq1qg |
| nodejs/node | codespell-run-pf6zq4dl |
| django/django | codespell-run-ibvhl0i4 |
| numpy/numpy | codespell-run-cxtx9sjo |
| rust-lang/rust | codespell-run-2o1fiw25 |
| Shubhamsaboo/awesome-llm-apps | codespell-run-4ic6pkpt |
| google/langextract | codespell-run-nzidavwr |
| kvcache-ai/ktransformers | codespell-run-1a_lfuvg |
| MoonshotAI/kimi-cli | codespell-run-d9snxrzx |
| thinking-machines-lab/tinker-cookbook | codespell-run-51qm1z2k |
| microsoft/semantic-kernel | codespell-run-msuvdxcx |
| unslothai/unsloth | codespell-run-mxhixg8l |
| PostHog/posthog | codespell-run-eo7i6p1b |
| ocornut/imgui | codespell-run-k6jql1a0 |
| catchorg/Catch2 | codespell-run-w1z4myfa |

## Highest-confidence, ready-to-fix examples
These read as unambiguous typos worth an upstream PR, not code-identifier false positives:
- **langchain-ai/langchain** — `README.md`: `capabilites ==> capabilities`
- **microsoft/autogen** — `dotnet/src/AutoGen.OpenAI.V1/Extension/FunctionContractExtension.cs:15`: `funciton ==> function`
- **microsoft/autogen** — `dotnet/samples/AgentChat/AutoGen.Anthropic.Sample/Create_Anthropic_Agent_With_Tool.cs:26`: `tempature ==> temperature`
- **microsoft/autogen** — `dotnet/samples/Hello/HelloAIAgents/HelloAIAgent.cs:18`: `supercedes ==> supersedes`
- **facebook/react** — `packages/react-dom/src/__tests__/ReactDOMTestSelectors-test.js:389`: `accessibiliy ==> accessibility`
- **facebook/react** — `packages/react-server-dom-parcel/src/shared/ReactFlightImportMetadata.js:11`: `essentialy ==> essentially`
- **kubernetes/kubernetes** — `staging/src/k8s.io/apimachinery/pkg/runtime/serializer/json/json_test.go`: `poped ==> popped`
- **kubernetes/kubernetes** — `hack/local-up-cluster.sh:1164`: `theyre ==> they're`
- **pytorch/pytorch** — `test/cpython/v3_13/test_descr.py`: `cant ==> can't` (many occurrences)
- **golang/go** — `src/regexp/syntax/regexp.go:187`: `cant ==> can't`
- **openai/openai-python** & **anthropics/anthropic-sdk-python** — both CHANGELOGs: `interpeter ==> interpreter` (identical typo in both official SDKs — likely a shared codegen/template source)
- **crewAIInc/crewAI** — `AGENTS.md:10`: `behaivor ==> behavior`
- **comfyanonymous/ComfyUI** — real hits: `isnt ==> isn't`, `unqiue ==> unique`, `indicies ==> indices`, `tesselation ==> tessellation`
- **AUTOMATIC1111/stable-diffusion-webui** — `CHANGELOG.md`: `extention ==> extension`, `stoping ==> stopping`, `eror ==> error`, `overriden ==> overridden`
- **django/django** — `AUTHORS`: `dne ==> done`, `Gage ==> Gauge`; `django/db/models/query.py`: `acount ==> account`
- **numpy/numpy** — `doc/changelog/1.20.0-changelog.rst`: `homogenous ==> homogeneous`
- **rust-lang/rust** — `src/doc/rustc-dev-guide/src/const-generics.md:125`: `atleast ==> at least`
- **Shubhamsaboo/awesome-llm-apps** — real hits: `wiht ==> with`, `incase ==> in case`, `furthur ==> further`
- **google/langextract** — `tests/init_test.py`: `treshold ==> threshold`
- **kvcache-ai/ktransformers** — CUDA kernel license headers: `Copyrigth ==> Copyright`
- **microsoft/semantic-kernel** — `.DotSettings`: `daa ==> data`; `Agents/README.md`: `deveop ==> develop`
- **PostHog/posthog** — `Dockerfile`: `COPYed ==> copied`; `web_stats_lazy_precompute.py` area: `Bulid ==> Build`
- **ocornut/imgui** — `imgui.cpp`: `overlayed ==> overlaid`; `imstb_textedit.h`: `canoncialize ==> canonicalize`
- **catchorg/Catch2** — `extras/catch_amalgamated.cpp`: `Coud ==> Could`

High per-repo totals for kubernetes, react, go, llama.cpp, transformers, numpy, and rust are dominated by a handful of test-fixture/compiler-test/vendored-code files with repeated words or code-identifier matches — real codespell output, but lower priority than the examples above. Use `git -C runs/clones/<dir> diff -- <file>` to inspect any hit before deciding to upstream it.

## User-verified hit rates
Ground truth from manual review (the real signal — trust this over raw counts):
- **openai/openai-python**: 3 of 50 hits were real (6%). Fixed by user.
- **MoonshotAI/kimi-cli**: 0 of 31 hits were real (0%).

These two data points suggest raw "Issues Found" counts across this whole list likely overstate real, upstream-worthy typos by roughly an order of magnitude — treat every unverified row's count as an upper bound, not an estimate of real value.

## Skip-list evolution (noise sources found & excluded)
Each round surfaced a new category of false-positive noise; the skip list has grown to exclude:
data/binary files, minified/bundled JS, vendored libs (`vendor`, `vendors`, `deps`, `third_party`, `external`, `extern`, `contrib`, `3rdparty`), BPE tokenizer files (`merges.txt`, `vocab.txt`), VCR test cassettes (`cassettes/`), lorem-ipsum placeholder text, non-English localized docs (both `docs/source/<lang>/` and `<lang>-<REGION>` directory/filename conventions), and a few repo-specific vendored math/SIMD libraries (`libdivide`, `lapack_lite`, `stdarch`, `rust-analyzer`). Current full `--skip` pattern is reused verbatim for new scans; expect to keep extending it as new repos surface new noise shapes (e.g. node's `deps/` bundling v8/npm/sqlite, numpy's `lapack_lite`, semantic-kernel's bundled `vocab.bpe`, posthog's bundled webpack test fixtures under `tests/static/`).

**Known dictionary false positives seen repeatedly** — codespell flags these but they are not real errors; don't count them toward "real typos found":
- `unparseable ==> unparsable` — both spellings are valid English; codespell just prefers one. Seen recurring in tinker-cookbook, unsloth, posthog.
- `SEH ==> SHE` — SEH is the real Windows API term (Structured Exception Handling), not a typo.
- `datas ==> data` inside PyInstaller `.spec` files — `datas` is PyInstaller's actual API field name.
- `Expresso ==> Espresso` — Expresso is a real published speech-dataset name, not a typo of Espresso.
- `re-use ==> reuse`, `co-ordinate ==> coordinate` — style nits (hyphenation preference), not errors.
