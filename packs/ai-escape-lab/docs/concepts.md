# Concepts

The lab teaches a participant to direct an autonomous coding agent across several sandbox boundaries.
The human judges evidence, redirects failed approaches, inspects payloads, and submits flags.
Claude Code helps explore the environment; the participant remains responsible for each decision.

The seven stages cover:

1. Discovery of the only allowed application egress.
2. Server-side request forgery (SSRF) through a package-mirror relay.
3. Escape from a native-code harness through an initialization hook.
4. Local file disclosure through unsafe HDF5 external storage.
5. Worker execution through unsandboxed Jinja rendering.
6. Access to a synthetic Kubernetes API through a workload token and its disclosed service credentials.
7. Access to isolated source control and the fictional benchmark solution set.

Every target is local to the participant's disposable VM.
Docker keeps the five upstream challenge networks internal.
A sixth adapter network provides the narrow model-access path for the coding agent.
The [participant entry page](../README.md#start-the-exercise) describes how to begin.
