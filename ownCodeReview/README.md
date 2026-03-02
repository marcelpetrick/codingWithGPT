# own code review with local ollama

Work in progress!

## idea
Code review bot, which just has to be started on a commit and then it picks up the changed files and does a review with focus to C++, Qt, QML.  
Point out the biggest flaws, etc.

### helper tool: list_models.py
Call with `--benchmark` to some stats for all available models.

```bash
   ~/repos/codingWithGPT/ownCodeReview    master wip ⇡8 *6 !1 ?2  python3 list_models.py --benchmark --verbose                                                                 ✔   
llama3.1:8b | wall=14232ms | gen=80tok | 65.5 tok/s || total=14225ms load=12453ms prompt_eval=394ms(843tok) eval=1222ms(80tok)
qwen3-coder:30b | wall=12550ms | gen=54tok | 24.9 tok/s || total=12519ms load=7769ms prompt_eval=2516ms(841tok) eval=2168ms(54tok)
qwen3:8b | wall=13197ms | gen=128tok | 59.2 tok/s || total=13179ms load=10473ms prompt_eval=432ms(843tok) eval=2164ms(128tok)
qwen3:4b | wall=6404ms | gen=128tok | 94.1 tok/s || total=6365ms load=4632ms prompt_eval=270ms(843tok) eval=1360ms(128tok)
freehuntx/qwen3-coder:14b | wall=8864ms | gen=50tok | 34.5 tok/s || total=8846ms load=6575ms prompt_eval=757ms(845tok) eval=1449ms(50tok)
qwen3-vl:4b | wall=9767ms | gen=128tok | 93.9 tok/s || total=9729ms load=7990ms prompt_eval=273ms(843tok) eval=1363ms(128tok)
qwen3-vl:8b | wall=10970ms | gen=128tok | 61.2 tok/s || total=10934ms load=8302ms prompt_eval=430ms(843tok) eval=2092ms(128tok)
qwen2.5vl:7b | wall=15211ms | gen=27tok | 28.2 tok/s || total=15192ms load=13270ms prompt_eval=874ms(852tok) eval=956ms(27tok)
qwen3-embedding:4b: HTTPError 400 Bad Request {"error":"\"qwen3-embedding:4b\" does not support generate"}
qwen3:14b | wall=13808ms | gen=128tok | 34.5 tok/s || total=13790ms load=9211ms prompt_eval=759ms(841tok) eval=3710ms(128tok)
DC1LEX/nomic-embed-text-v1.5-multimodal:latest: HTTPError 400 Bad Request {"error":"\"DC1LEX/nomic-embed-text-v1.5-multimodal:latest\" does not support generate"}
nomic-embed-text-v1.5-multimodal:latest: HTTPError 400 Bad Request {"error":"\"nomic-embed-text-v1.5-multimodal:latest\" does not support generate"}
    ~/repos/codingWithGPT/ownCodeReview    master wip ⇡8 *6 !1 ?3     
```
 
Which makes `qwen3:4b`best suited for my experiements. With runtime of 4sec.

If the result is helpful is another page ..
