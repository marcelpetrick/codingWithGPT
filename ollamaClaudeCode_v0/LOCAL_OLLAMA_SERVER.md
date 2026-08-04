## existing and known server

```sh
❯ curl http://192.168.100.37:11434/api/version

{"version":"0.22.0"}%                                                                                                                      ❯ 
❯ 
❯ 
❯ 
❯ curl http://192.168.100.37:11434/api/version

{"version":"0.22.0"}%                                                                                                                      ❯  curl http://192.168.100.37:11434/api/tags | jq '.models[].name'

  % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                 Dload  Upload  Total   Spent   Left   Speed
100   4679   0   4679   0      0 639.9k      0                              0
"qwen2.5-coder:32b"
"qwen3:14b-q8_0"
"qwen3:8b-q8_0"
"qwen3.5:0.8b"
"qwen3.5:9b-ctx64k"
"qwen3.5-ctx32k:9b"
"qwen2.5-coder:7b-ctx32k"
"qwen2.5-coder:7b"
"qwen3.5:27b"
"qwen3.5:9b"
"qwen3-coder:30b"
"qwen3-vl:4b"
"qwen3-vl:8b"
"qwen3-embedding:4b"
```
