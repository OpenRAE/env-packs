# CTFd export

Use this operator how-to guide to create the answer-bearing CTFd import file.
Work from `packs/ai-escape-lab/` with a protected output directory outside the repository.
The output contains seven static flags and twenty-three progressive hints.
Keep it outside participant-visible artifacts and source control.

```sh
python3 ctfd/export_shifter_challenge_pack.py --output /secure/path/ai-escape-lab-ctfd.json
```

Replace `/secure/path/` with your protected operator directory.
The exporter joins the canonical flag-placement and challenge sources.
It checks the complete seven-flag inventory and writes the output atomically with mode `0600`.

After deployment approval, import the JSON through Shifter's CTFd challenge-pack surface.
Verify all challenges, flag associations, and progressive hints.
Delete the local operator copy after import verification.
The [operator runbook](../docs/operator-runbook.md#3-register-the-scenario-and-ctfd-content) gives the deployment sequence.
