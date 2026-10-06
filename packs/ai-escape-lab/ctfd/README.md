# CTFd export

Generate the answer-bearing import file outside the repository:

```sh
python3 ctfd/export_shifter_challenge_pack.py --output /secure/path/ai-escape-lab-ctfd.json
```

The exporter joins the canonical placement and participant challenge sources,
validates the complete seven-flag inventory, and writes the output atomically
with mode `0600`. Import the JSON through Shifter's CTFd challenge-pack surface.
Do not commit the generated file.
