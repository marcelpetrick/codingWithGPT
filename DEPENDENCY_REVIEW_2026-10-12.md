# GitHub dependency review — 2026-10-12

## Verdict so far

Published: all nine Dependabot updates landed on the default branches in three verified commits. All nine redundant Dependabot PRs were closed with explanations linking the published commits. A fresh direct query across all 114 repositories confirms zero open Dependabot PRs; only the unrelated x-clone-starter workshop PR remains. The three unrelated issues remain open. GitHub settings were unchanged. Local gates passed; post-push GitHub CI is running. AlliumAssault now reports zero open Dependabot security alerts.

Initial inventory: 114 repositories, 10 open pull requests, 3 open issues. Direct GraphQL queries confirmed every repository count (including private repositories and forks). The user subsequently authorized pushing and completing all compatible dependency PRs.

## Plan with estimates

1. Inventory repositories, issues and PRs (5 minutes).
2. Inspect dependency PR diffs, instructions and checks (10–20 minutes).
3. Apply compatible dependency updates locally and run full repository gates (time depends on inventory).
4. Commit verified updates separately; record blockers (5 minutes per repository).
5. Review results and deliver linked inventory (5 minutes).

## Chronological status

| Time | Stage | Result |
|---|---|---|
| 2026-10-12T12:16 | Inventory | GitHub CLI authenticated; repository and search inventories collected. |
| 2026-10-12T12:18 | Inspection | Confirmed 114 repository counts directly; reviewed all nine dependency diffs and three repository gates. |
| 2026-10-12T12:29 | Verified commits | myLastFmPlayer `b24c031`; DividendenDackel `af674bc`; AlliumAssault browser gate running. |
| 2026-10-12T12:33 | Complete | AlliumAssault `de9649b` committed after all 77 E2E tests; all three updates verified. |
| 2026-10-12T12:40 | Published | Pushed all three dependency commits; closed all nine superseded Dependabot PRs; direct account scan confirms only the unrelated workshop PR remains. |

## Repositories — initial inventory

| Repository | Fork | Open PRs | Open issues |
|---|---|---:|---:|
| [marcelpetrick/DividendenDackel](https://github.com/marcelpetrick/DividendenDackel) | False | 6 | 0 |
| [marcelpetrick/BavarianLemmings](https://github.com/marcelpetrick/BavarianLemmings) | False | 0 | 0 |
| [marcelpetrick/myLastFmPlayer](https://github.com/marcelpetrick/myLastFmPlayer) | False | 1 | 0 |
| [marcelpetrick/AlliumAssault](https://github.com/marcelpetrick/AlliumAssault) | False | 2 | 0 |
| [marcelpetrick/androidCatEars](https://github.com/marcelpetrick/androidCatEars) | False | 0 | 0 |
| [marcelpetrick/TuringTongue](https://github.com/marcelpetrick/TuringTongue) | False | 0 | 0 |
| [marcelpetrick/AgentWhileTrue](https://github.com/marcelpetrick/AgentWhileTrue) | False | 0 | 0 |
| [marcelpetrick/tokenUsage2](https://github.com/marcelpetrick/tokenUsage2) | False | 0 | 0 |
| [marcelpetrick/GermanDubI](https://github.com/marcelpetrick/GermanDubI) | False | 0 | 0 |
| [marcelpetrick/recognizer](https://github.com/marcelpetrick/recognizer) | False | 0 | 0 |
| [marcelpetrick/Raumfreund](https://github.com/marcelpetrick/Raumfreund) | False | 0 | 0 |
| [marcelpetrick/codingWithGPT](https://github.com/marcelpetrick/codingWithGPT) | False | 0 | 0 |
| [marcelpetrick/CroLingo](https://github.com/marcelpetrick/CroLingo) | False | 0 | 0 |
| [marcelpetrick/RecurrenceRanger](https://github.com/marcelpetrick/RecurrenceRanger) | False | 0 | 0 |
| [marcelpetrick/marcelpetrick](https://github.com/marcelpetrick/marcelpetrick) | False | 0 | 0 |
| [marcelpetrick/personalNotes](https://github.com/marcelpetrick/personalNotes) | False | 0 | 0 |
| [marcelpetrick/DevNotesPrivate](https://github.com/marcelpetrick/DevNotesPrivate) | False | 0 | 0 |
| [marcelpetrick/ollamaFarm](https://github.com/marcelpetrick/ollamaFarm) | False | 0 | 0 |
| [marcelpetrick/lizard](https://github.com/marcelpetrick/lizard) | True | 0 | 0 |
| [marcelpetrick/GarminActivityMap](https://github.com/marcelpetrick/GarminActivityMap) | False | 0 | 0 |
| [marcelpetrick/GitLabTeamPulse](https://github.com/marcelpetrick/GitLabTeamPulse) | False | 0 | 0 |
| [marcelpetrick/Cullendula](https://github.com/marcelpetrick/Cullendula) | False | 0 | 0 |
| [marcelpetrick/math-learning-for-kids](https://github.com/marcelpetrick/math-learning-for-kids) | True | 0 | 0 |
| [marcelpetrick/HelgasKatzenspiel](https://github.com/marcelpetrick/HelgasKatzenspiel) | False | 0 | 0 |
| [marcelpetrick/OdoakersAquariumSpiel](https://github.com/marcelpetrick/OdoakersAquariumSpiel) | False | 0 | 0 |
| [marcelpetrick/hr-doccontrol](https://github.com/marcelpetrick/hr-doccontrol) | False | 0 | 0 |
| [marcelpetrick/cheatsheets](https://github.com/marcelpetrick/cheatsheets) | False | 0 | 0 |
| [marcelpetrick/ESP32-Tiny-LLM](https://github.com/marcelpetrick/ESP32-Tiny-LLM) | False | 0 | 0 |
| [marcelpetrick/RitterRadar](https://github.com/marcelpetrick/RitterRadar) | False | 0 | 0 |
| [marcelpetrick/ForkAroundAndFindOut](https://github.com/marcelpetrick/ForkAroundAndFindOut) | False | 0 | 0 |
| [marcelpetrick/llmPEG](https://github.com/marcelpetrick/llmPEG) | False | 0 | 0 |
| [marcelpetrick/LTS_oracle](https://github.com/marcelpetrick/LTS_oracle) | False | 0 | 0 |
| [marcelpetrick/DarkFactory](https://github.com/marcelpetrick/DarkFactory) | False | 0 | 1 |
| [marcelpetrick/WorkshopInTheStyleOfAZartisAnthropicClaudeCodeWorkshop](https://github.com/marcelpetrick/WorkshopInTheStyleOfAZartisAnthropicClaudeCodeWorkshop) | False | 0 | 0 |
| [marcelpetrick/DevNotes](https://github.com/marcelpetrick/DevNotes) | False | 0 | 1 |
| [marcelpetrick/CuteLingoExpress](https://github.com/marcelpetrick/CuteLingoExpress) | False | 0 | 0 |
| [marcelpetrick/LVGL_coffeeDispenser](https://github.com/marcelpetrick/LVGL_coffeeDispenser) | False | 0 | 0 |
| [marcelpetrick/esp32-fever-dream](https://github.com/marcelpetrick/esp32-fever-dream) | False | 0 | 0 |
| [marcelpetrick/x-clone-starter](https://github.com/marcelpetrick/x-clone-starter) | True | 1 | 0 |
| [marcelpetrick/openai-python](https://github.com/marcelpetrick/openai-python) | True | 0 | 0 |
| [marcelpetrick/mostSimpleSharedGroceryList](https://github.com/marcelpetrick/mostSimpleSharedGroceryList) | False | 0 | 0 |
| [marcelpetrick/sensorly-unhinged](https://github.com/marcelpetrick/sensorly-unhinged) | False | 0 | 0 |
| [marcelpetrick/productHunts](https://github.com/marcelpetrick/productHunts) | False | 0 | 0 |
| [marcelpetrick/LLM_prompts_to_automate_work](https://github.com/marcelpetrick/LLM_prompts_to_automate_work) | False | 0 | 0 |
| [marcelpetrick/ESE_Kongress_Selektor](https://github.com/marcelpetrick/ESE_Kongress_Selektor) | False | 0 | 0 |
| [marcelpetrick/ollama](https://github.com/marcelpetrick/ollama) | True | 0 | 0 |
| [marcelpetrick/esp32-agent-skills](https://github.com/marcelpetrick/esp32-agent-skills) | False | 0 | 0 |
| [marcelpetrick/sales-slip-scanner-ng](https://github.com/marcelpetrick/sales-slip-scanner-ng) | False | 0 | 0 |
| [marcelpetrick/OnceUponATensor](https://github.com/marcelpetrick/OnceUponATensor) | False | 0 | 0 |
| [marcelpetrick/AgenticSwearJar](https://github.com/marcelpetrick/AgenticSwearJar) | False | 0 | 0 |
| [marcelpetrick/Ventoy](https://github.com/marcelpetrick/Ventoy) | True | 0 | 0 |
| [marcelpetrick/SpellChecker-Plugin](https://github.com/marcelpetrick/SpellChecker-Plugin) | True | 0 | 0 |
| [marcelpetrick/TapocalypseNow_QmlSameGame](https://github.com/marcelpetrick/TapocalypseNow_QmlSameGame) | False | 0 | 0 |
| [marcelpetrick/esp32Collection](https://github.com/marcelpetrick/esp32Collection) | False | 0 | 0 |
| [marcelpetrick/tinyBlasterRunner](https://github.com/marcelpetrick/tinyBlasterRunner) | False | 0 | 0 |
| [marcelpetrick/recipes](https://github.com/marcelpetrick/recipes) | False | 0 | 0 |
| [marcelpetrick/QtScrobbler](https://github.com/marcelpetrick/QtScrobbler) | False | 0 | 0 |
| [marcelpetrick/4-7-8-breathing-python-browser-prototype](https://github.com/marcelpetrick/4-7-8-breathing-python-browser-prototype) | False | 0 | 0 |
| [marcelpetrick/speech4excellence](https://github.com/marcelpetrick/speech4excellence) | False | 0 | 0 |
| [marcelpetrick/SaveTheSnek](https://github.com/marcelpetrick/SaveTheSnek) | False | 0 | 0 |
| [marcelpetrick/homepageInCpp](https://github.com/marcelpetrick/homepageInCpp) | False | 0 | 0 |
| [marcelpetrick/Interstellar_Space_Genesis_automation](https://github.com/marcelpetrick/Interstellar_Space_Genesis_automation) | False | 0 | 0 |
| [marcelpetrick/jafed.ai](https://github.com/marcelpetrick/jafed.ai) | False | 0 | 1 |
| [marcelpetrick/SoftwareDevelopmentWorkflow](https://github.com/marcelpetrick/SoftwareDevelopmentWorkflow) | False | 0 | 0 |
| [marcelpetrick/Gitlab_Hitparade](https://github.com/marcelpetrick/Gitlab_Hitparade) | False | 0 | 0 |
| [marcelpetrick/pythonCollection](https://github.com/marcelpetrick/pythonCollection) | False | 0 | 0 |
| [marcelpetrick/rustyShenanigans](https://github.com/marcelpetrick/rustyShenanigans) | False | 0 | 0 |
| [marcelpetrick/marcelpetrick.github.io](https://github.com/marcelpetrick/marcelpetrick.github.io) | False | 0 | 0 |
| [marcelpetrick/docker_experiments](https://github.com/marcelpetrick/docker_experiments) | False | 0 | 0 |
| [marcelpetrick/MBA_for_Marcel](https://github.com/marcelpetrick/MBA_for_Marcel) | False | 0 | 0 |
| [marcelpetrick/minimalQt5](https://github.com/marcelpetrick/minimalQt5) | False | 0 | 0 |
| [marcelpetrick/CopilotHackathon](https://github.com/marcelpetrick/CopilotHackathon) | True | 0 | 0 |
| [marcelpetrick/riktiQt_rutmoenster](https://github.com/marcelpetrick/riktiQt_rutmoenster) | False | 0 | 0 |
| [marcelpetrick/lovacNaPosao](https://github.com/marcelpetrick/lovacNaPosao) | False | 0 | 0 |
| [marcelpetrick/openAiExperiments](https://github.com/marcelpetrick/openAiExperiments) | False | 0 | 0 |
| [marcelpetrick/PyWoPro](https://github.com/marcelpetrick/PyWoPro) | False | 0 | 0 |
| [marcelpetrick/BowlingScoreBoard](https://github.com/marcelpetrick/BowlingScoreBoard) | False | 0 | 0 |
| [marcelpetrick/DeepLearning.ai](https://github.com/marcelpetrick/DeepLearning.ai) | False | 0 | 0 |
| [marcelpetrick/GroSim](https://github.com/marcelpetrick/GroSim) | False | 0 | 0 |
| [marcelpetrick/NTXHackathon22](https://github.com/marcelpetrick/NTXHackathon22) | False | 0 | 0 |
| [marcelpetrick/privateDraw.io](https://github.com/marcelpetrick/privateDraw.io) | False | 0 | 0 |
| [marcelpetrick/daily_alarm_2k](https://github.com/marcelpetrick/daily_alarm_2k) | False | 0 | 0 |
| [marcelpetrick/PiCamGifForTumblr](https://github.com/marcelpetrick/PiCamGifForTumblr) | False | 0 | 0 |
| [marcelpetrick/cute_gcov_test](https://github.com/marcelpetrick/cute_gcov_test) | False | 0 | 0 |
| [marcelpetrick/contactSheet](https://github.com/marcelpetrick/contactSheet) | False | 0 | 0 |
| [marcelpetrick/kaggle_30daysOfML](https://github.com/marcelpetrick/kaggle_30daysOfML) | False | 0 | 0 |
| [marcelpetrick/CalliopeCollection](https://github.com/marcelpetrick/CalliopeCollection) | False | 0 | 0 |
| [marcelpetrick/MachWasDraus](https://github.com/marcelpetrick/MachWasDraus) | False | 0 | 0 |
| [marcelpetrick/cppCollection](https://github.com/marcelpetrick/cppCollection) | False | 0 | 0 |
| [marcelpetrick/confidentialTrainings](https://github.com/marcelpetrick/confidentialTrainings) | False | 0 | 0 |
| [marcelpetrick/hauskauf](https://github.com/marcelpetrick/hauskauf) | False | 0 | 0 |
| [marcelpetrick/voice-activated-microbit](https://github.com/marcelpetrick/voice-activated-microbit) | True | 0 | 0 |
| [marcelpetrick/microbitCollection](https://github.com/marcelpetrick/microbitCollection) | False | 0 | 0 |
| [marcelpetrick/cotli_bot](https://github.com/marcelpetrick/cotli_bot) | False | 0 | 0 |
| [marcelpetrick/KubeFlow_BERT_GPU_TensorFlow_Keras_SageMaker_Workshop](https://github.com/marcelpetrick/KubeFlow_BERT_GPU_TensorFlow_Keras_SageMaker_Workshop) | False | 0 | 0 |
| [marcelpetrick/bashCollection](https://github.com/marcelpetrick/bashCollection) | False | 0 | 0 |
| [marcelpetrick/graphicsWithPython](https://github.com/marcelpetrick/graphicsWithPython) | False | 0 | 0 |
| [marcelpetrick/DllVersionChecker](https://github.com/marcelpetrick/DllVersionChecker) | False | 0 | 0 |
| [marcelpetrick/AutoItCollection](https://github.com/marcelpetrick/AutoItCollection) | False | 0 | 0 |
| [marcelpetrick/CloneDetector](https://github.com/marcelpetrick/CloneDetector) | False | 0 | 0 |
| [marcelpetrick/machineLearningWithPython](https://github.com/marcelpetrick/machineLearningWithPython) | False | 0 | 0 |
| [marcelpetrick/esp8266Collection](https://github.com/marcelpetrick/esp8266Collection) | False | 0 | 0 |
| [marcelpetrick/CMake-collection](https://github.com/marcelpetrick/CMake-collection) | False | 0 | 0 |
| [marcelpetrick/cuteDraggableChart](https://github.com/marcelpetrick/cuteDraggableChart) | False | 0 | 0 |
| [marcelpetrick/pyXmlSort](https://github.com/marcelpetrick/pyXmlSort) | False | 0 | 0 |
| [marcelpetrick/Python_FortgeschrittenenSeminar](https://github.com/marcelpetrick/Python_FortgeschrittenenSeminar) | False | 0 | 0 |
| [marcelpetrick/autohotkeyCollection](https://github.com/marcelpetrick/autohotkeyCollection) | False | 0 | 0 |
| [marcelpetrick/dumpDiver](https://github.com/marcelpetrick/dumpDiver) | False | 0 | 0 |
| [marcelpetrick/crashReportExampleProject](https://github.com/marcelpetrick/crashReportExampleProject) | False | 0 | 0 |
| [marcelpetrick/proCreator](https://github.com/marcelpetrick/proCreator) | False | 0 | 0 |
| [marcelpetrick/SAP_AutoIt](https://github.com/marcelpetrick/SAP_AutoIt) | False | 0 | 0 |
| [marcelpetrick/cleanMyCode](https://github.com/marcelpetrick/cleanMyCode) | False | 0 | 0 |
| [marcelpetrick/MaX](https://github.com/marcelpetrick/MaX) | False | 0 | 0 |
| [marcelpetrick/compareFilecontents](https://github.com/marcelpetrick/compareFilecontents) | False | 0 | 0 |

## Pull requests — initial inventory

- [marcelpetrick/DividendenDackel#22: build(deps): bump actions/upload-artifact from 7.0.1 to 7.0.2](https://github.com/marcelpetrick/DividendenDackel/pull/22) — dependabot[bot]
- [marcelpetrick/DividendenDackel#21: build(deps): bump org.jetbrains.kotlin.android from 2.4.20 to 2.4.21 in /android](https://github.com/marcelpetrick/DividendenDackel/pull/21) — dependabot[bot]
- [marcelpetrick/DividendenDackel#20: build(deps): bump url_launcher from 6.3.2 to 6.3.3](https://github.com/marcelpetrick/DividendenDackel/pull/20) — dependabot[bot]
- [marcelpetrick/DividendenDackel#19: build(deps): bump package_info_plus from 10.2.1 to 10.2.2](https://github.com/marcelpetrick/DividendenDackel/pull/19) — dependabot[bot]
- [marcelpetrick/DividendenDackel#18: build(deps): bump build_runner from 2.16.1 to 2.16.2](https://github.com/marcelpetrick/DividendenDackel/pull/18) — dependabot[bot]
- [marcelpetrick/DividendenDackel#17: build(deps): bump shared_preferences from 2.5.5 to 2.5.6](https://github.com/marcelpetrick/DividendenDackel/pull/17) — dependabot[bot]
- [marcelpetrick/myLastFmPlayer#8: chore(deps): bump pylint from 4.1.1 to 4.1.2 in the dev-dependencies group across 1 directory](https://github.com/marcelpetrick/myLastFmPlayer/pull/8) — dependabot[bot]
- [marcelpetrick/AlliumAssault#5: build(deps): bump the dev-tooling group across 1 directory with 4 updates](https://github.com/marcelpetrick/AlliumAssault/pull/5) — dependabot[bot]
- [marcelpetrick/AlliumAssault#4: build(deps): bump @babylonjs/core from 9.29.0 to 9.30.0](https://github.com/marcelpetrick/AlliumAssault/pull/4) — dependabot[bot]
- [marcelpetrick/x-clone-starter#1: Workshop: Part 1 setup and Part 2 requirements skills (sections 2-8)](https://github.com/marcelpetrick/x-clone-starter/pull/1) — marcelpetrick

## Open issues

- [marcelpetrick/DarkFactory#1: Missing blocks](https://github.com/marcelpetrick/DarkFactory/issues/1) — marcelpetrick
- [marcelpetrick/jafed.ai#2: Define "make" or "build on top"](https://github.com/marcelpetrick/jafed.ai/issues/2) — DC1LEX
- [marcelpetrick/DevNotes#2: Notes on the MUC++ talk from 26.01.2024](https://github.com/marcelpetrick/DevNotes/issues/2) — kanje

## Results

| Repository | Version | Local commit | Gate |
|---|---|---|---|
| myLastFmPlayer | 0.0.199 | `b24c031` | Full pipeline passed; 610 tests, 6 skips |
| DividendenDackel | 0.65.12+132 | `af674bc` | Full pipeline passed; 684 tests, 10 Linux integration tests, Linux/Android release builds |
| AlliumAssault | 1.78.6 | `de9649b` | Full verify and REUSE passed; 313 unit tests, 77 Chrome E2E tests |

### Non-dependency work

- [DarkFactory#1](https://github.com/marcelpetrick/DarkFactory/issues/1): missing architecture documentation, README badges, license, reviews and screenshots.
- [jafed.ai#2](https://github.com/marcelpetrick/jafed.ai/issues/2): choose whether to reuse a related project for the embedded edge version.
- [DevNotes#2](https://github.com/marcelpetrick/DevNotes/issues/2): correct notes about execution contexts and callbacks from the MUC++ talk.
- [x-clone-starter#1](https://github.com/marcelpetrick/x-clone-starter/pull/1): workshop setup and requirements skills; no CI checks.
These are outside dependency maintenance and remain unchanged. The workshop PR is the only remaining open PR across the account.

Nine Dependabot PRs across three repositories; all are mergeable and their required CI jobs pass. CodeQL is neutral where present. One unrelated workshop PR has no checks.

Dependabot configuration found at `.github/dependabot.yml` in 10 of 114 repositories. Both `.yml` and `.yaml` paths were checked. The dedicated `GET /repos/{owner}/{repo}/automated-security-fixes` endpoint was then queried for every repository: automatic security fixes are enabled and unpaused in 11 repositories, disabled in 103. GermanDubI deliberately disables routine version PRs and keeps security updates only, as documented in its configuration.

Security updates enabled:
- marcelpetrick/myLastFmPlayer
- marcelpetrick/AlliumAssault
- marcelpetrick/androidCatEars
- marcelpetrick/GermanDubI
- marcelpetrick/codingWithGPT
- marcelpetrick/CroLingo
- marcelpetrick/Cullendula
- marcelpetrick/CuteLingoExpress
- marcelpetrick/pythonCollection
- marcelpetrick/CalliopeCollection
- marcelpetrick/bashCollection

Configured repositories:
- marcelpetrick/DividendenDackel
- marcelpetrick/myLastFmPlayer
- marcelpetrick/AlliumAssault
- marcelpetrick/androidCatEars
- marcelpetrick/TuringTongue
- marcelpetrick/GermanDubI
- marcelpetrick/recognizer
- marcelpetrick/Raumfreund
- marcelpetrick/CroLingo
- marcelpetrick/GitLabTeamPulse

### Security alerts

Among the 11 repositories with automatic security fixes enabled, AlliumAssault has two open alerts: [KaTeX #3](https://github.com/marcelpetrick/AlliumAssault/security/dependabot/3) (low) and [source-map-js #2](https://github.com/marcelpetrick/AlliumAssault/security/dependabot/2) (high). Both are addressed in the updated local lockfile (KaTeX 0.19.0; source-map-js 1.2.2). The fixes have now reached the default branch; GitHub alert status is checked separately after publication. The alerts endpoint was queried for all 114 repositories: 54 returned accessible results (two alerts total); 60 returned HTTP 403 explicitly stating Dependabot alerts are disabled, so they cannot be counted as clean. Details are preserved in `all-dependabot-alerts.json`.

### Dependency PR status

| Repository / PR | Changes | CI | Local result |
|---|---|---|---|
| [marcelpetrick/DividendenDackel#22](https://github.com/marcelpetrick/DividendenDackel/pull/22) | build(deps): bump actions/upload-artifact from 7.0.1 to 7.0.2 | Passing | Passed; commit `af674bc`  Closed as superseded. |
| [marcelpetrick/DividendenDackel#21](https://github.com/marcelpetrick/DividendenDackel/pull/21) | build(deps): bump org.jetbrains.kotlin.android from 2.4.20 to 2.4.21 in /android | Passing | Passed; commit `af674bc`  Closed as superseded. |
| [marcelpetrick/DividendenDackel#20](https://github.com/marcelpetrick/DividendenDackel/pull/20) | build(deps): bump url_launcher from 6.3.2 to 6.3.3 | Passing | Passed; commit `af674bc`  Closed as superseded. |
| [marcelpetrick/DividendenDackel#19](https://github.com/marcelpetrick/DividendenDackel/pull/19) | build(deps): bump package_info_plus from 10.2.1 to 10.2.2 | Passing | Passed; commit `af674bc`  Closed as superseded. |
| [marcelpetrick/DividendenDackel#18](https://github.com/marcelpetrick/DividendenDackel/pull/18) | build(deps): bump build_runner from 2.16.1 to 2.16.2 | Passing | Passed; commit `af674bc`  Closed as superseded. |
| [marcelpetrick/DividendenDackel#17](https://github.com/marcelpetrick/DividendenDackel/pull/17) | build(deps): bump shared_preferences from 2.5.5 to 2.5.6 | Passing | Passed; commit `af674bc`  Closed as superseded. |
| [marcelpetrick/myLastFmPlayer#8](https://github.com/marcelpetrick/myLastFmPlayer/pull/8) | chore(deps): bump pylint from 4.1.1 to 4.1.2 in the dev-dependencies group across 1 directory | Passing | Passed; commit `b24c031` (Pylint 4.1.3 supersedes 4.1.2)  Closed as superseded. |
| [marcelpetrick/AlliumAssault#5](https://github.com/marcelpetrick/AlliumAssault/pull/5) | build(deps): bump the dev-tooling group across 1 directory with 4 updates | Passing | Passed; commit `de9649b`  Closed as superseded. |
| [marcelpetrick/AlliumAssault#4](https://github.com/marcelpetrick/AlliumAssault/pull/4) | build(deps): bump @babylonjs/core from 9.29.0 to 9.30.0 | Passing | Passed; commit `de9649b`  Closed as superseded. |

### Registry review

Official PyPI, npm and pub.dev APIs checked for all direct, development, build and override dependencies in the three affected repositories. All existing pins are exact. Newer compatible releases were included after verification. TypeScript 7.0.2 is blocked by typescript-eslint 8.71.1 peer requirement `<6.1.0`; retain TypeScript 6.0.3. Node types remain on 24.x to match Node 24.

myLastFmPlayer: Pylint 4.1.3 and Ruff 0.17.0, version 0.0.199, committed as `b24c031`. Full `./localPipeline.sh --noRun --report-dir /tmp/github-dependency-review-2026-10-12/mylastfm-report` passed: Ruff clean, Pylint 10/10, 1080 translated strings, Sphinx warnings zero, 610 tests passed / 6 skipped, package builds and installed-wheel import. Coverage reports 98.96%; pytest-cov rounds this to meet the configured 99% gate.

AlliumAssault: applied Dependabot updates and newer compatible patch releases, version 1.78.6, committed as `de9649b` after full `CI=true npm run verify && npm run lint:reuse` passed. npm audit found tooling-only advisories; applied a KaTeX 0.19.0 override to address GHSA-238p-pmpm-9mq7. Audit improves from 12 findings (9 high / 3 low) to 8 high, all stemming from the same unpatched braces advisory. The braces advisory GHSA-vfj7-8cjw-p6xm has no patched published release (latest 3.0.3); do not apply npm audit’s suggested downgrades to obsolete linting tools. `npm audit --omit=dev` passes with zero findings.

DividendenDackel: applied all six Dependabot changes plus flutter_local_notifications 22.3.2; version script bumped to 0.65.12+132. Verified upload-artifact v7.0.2 resolves to the proposed full SHA and Kotlin 2.4.21 is a stable GitHub release. Committed as `af674bc` after the full `./localPipeline.sh --noRun` gate passed with an isolated SDK at Flutter 3.47.4 and Java 21. Shared SDK untouched; format/analyze/tests, all 10 Linux integration tests, version validation, Android 10 compatibility assertion, Linux release build and Android release APK all passed.

Checks ran detached under `systemd-inhibit`, with `flock` preventing duplicate runs. All finished successfully. Status files: `/home/mpetrick/.cache/github-dependency-review-2026-10-12/{mylastfm,flutter,allium}.result` (all contain 0).

AlliumAssault full verify completed: lint and typecheck passed; all 313 unit tests passed. Coverage: statements 99.68%, branches 98.13%, functions 100%, lines 99.9%; thresholds passed. Production build passed; All 77 Chrome E2E cases passed in 11.1 minutes; REUSE lint passed (149/149 files).

DividendenDackel dependency resolution, formatting, analysis and unit tests passed. Full gate passed; dependency update committed as `af674bc`. Version checker also passed for `HEAD^..HEAD`. The log prints the full stage summary at completion.

KaTeX override compatibility was also checked by rendering inline and block math through the installed `micromark-extension-math`; both render successfully without KaTeX errors.

### Primary upstream evidence

- [Pylint release notes](https://github.com/pylint-dev/pylint/releases) and [PyPI metadata](https://pypi.org/pypi/pylint/json).
- [KaTeX advisory](https://github.com/advisories/GHSA-238p-pmpm-9mq7), [source-map-js advisory](https://github.com/advisories/GHSA-68fv-2mgg-jv7q), [braces advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm).
- [npm typescript-eslint peer metadata](https://registry.npmjs.org/typescript-eslint/8.71.1).
- [Kotlin 2.4.21](https://github.com/JetBrains/kotlin/releases/tag/v2.4.21), [upload-artifact 7.0.2](https://github.com/actions/upload-artifact/releases/tag/v7.0.2).
Registry metadata and pub.dev retraction checks are preserved in the evidence directory.

## Resume here

Durable evidence: `/home/mpetrick/.cache/github-dependency-review-2026-10-12/` (inventory, PR diffs, settings, alerts, registry lookups and completed pipeline logs).

Published commits: `myLastFmPlayer` `b24c031`; `DividendenDackel` `af674bc`. AlliumAssault is committed as `de9649b`; 77 Chrome tests and REUSE lint passed. All three repository working trees are clean.

Exact restart / check commands:
```sh
cd /home/mpetrick/repos/AlliumAssault
CI=true npm run verify && npm run lint:reuse
cd /home/mpetrick/repos/myLastFmPlayer
QT_QPA_PLATFORM=offscreen MY_LASTFM_PLAYER_REPORT_BROWSER=true ./localPipeline.sh --noRun
cd /home/mpetrick/repos/DividendenDackel
PATH=/tmp/github-dependency-review-2026-10-12/flutter-3.47.4/bin:$PATH ./localPipeline.sh --noRun
./tool/check-version.sh HEAD^ HEAD
```
If the isolated SDK no longer exists: `git clone --shared --no-checkout /home/mpetrick/develop/flutter /tmp/github-dependency-review-2026-10-12/flutter-3.47.4`, then `git -C /tmp/github-dependency-review-2026-10-12/flutter-3.47.4 checkout --detach 3.47.4`.

Working directory: `/home/mpetrick/repos/codingWithGPT`; branch: `master`.
Raw inventory: `/tmp/github-dependency-review-2026-10-12/{repos,prs,issues}.json`.
Restart inventory: `gh repo list marcelpetrick --limit 1000 --json nameWithOwner,isArchived,isFork,url,defaultBranchRef`.
Check changes: `git status --short`; review this document before continuing.
Publication is complete. All nine Dependabot PRs were closed as superseded by the published verified commits, rather than merging duplicate dependency changes. GitHub CI runs were triggered automatically; see the publication section for their snapshot.

## Publication

User authorized pushing the verified changes and completing compatible dependency PRs.

| Repository | Published commit | Dependabot PRs |
|---|---|---|
| DividendenDackel | [af674bc](https://github.com/marcelpetrick/DividendenDackel/commit/af674bc854ef224de2b76b118216faf8639b2fd2) | #17–#22 closed as superseded |
| myLastFmPlayer | [b24c031](https://github.com/marcelpetrick/myLastFmPlayer/commit/b24c03131c33321878e27c81e40d7f38d7e56c99) | #8 closed as superseded; Pylint 4.1.3 replaces proposed 4.1.2 |
| AlliumAssault | [de9649b](https://github.com/marcelpetrick/AlliumAssault/commit/de9649b7466f4d5f628df0b62279f5cc621657e6) | #4–#5 closed as superseded |

All closures link the verified published commit and explain that its changes include or supersede
the original PR. No branches were force-pushed or deleted. Direct GraphQL queries across every
repository confirm exactly one open PR, the unrelated workshop PR in x-clone-starter.

Post-push GitHub CI snapshot:

- marcelpetrick/DividendenDackel: [CI](https://github.com/marcelpetrick/DividendenDackel/actions/runs/38237618596) — in_progress.
- marcelpetrick/myLastFmPlayer: [Dependency Graph](https://github.com/marcelpetrick/myLastFmPlayer/actions/runs/38237628996) — success.
- marcelpetrick/myLastFmPlayer: [Local Pipeline](https://github.com/marcelpetrick/myLastFmPlayer/actions/runs/38237622222) — in_progress.
- marcelpetrick/myLastFmPlayer: [CodeQL](https://github.com/marcelpetrick/myLastFmPlayer/actions/runs/38237622223) — success.
- marcelpetrick/AlliumAssault: [CodeQL](https://github.com/marcelpetrick/AlliumAssault/actions/runs/38237625652) — in_progress.
- marcelpetrick/AlliumAssault: [CI](https://github.com/marcelpetrick/AlliumAssault/actions/runs/38237625856) — in_progress.

AlliumAssault alerts API returned zero open security alerts after publication. The separate unpatched braces tooling advisory remains recorded above.
