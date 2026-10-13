# Concepts

The lab gives an attendee practical experience directing an autonomous coding
agent across a deliberately layered sandbox. The human decides what evidence is
credible, redirects failed approaches, inspects generated payloads, and submits
the flags. Claude Code supplies speed and exploratory breadth; it does not turn
the exercise into a passive demonstration.

The seven stages cover:

1. discovering the only allowed application egress;
2. turning a package-mirror relay into SSRF;
3. escaping a native-code harness through initialization-hook abuse;
4. abusing unsafe HDF5 external storage for local file disclosure;
5. converting unsandboxed Jinja rendering into worker execution;
6. using a workload token against a synthetic Kubernetes API and pivoting
   through its disclosed service credentials; and
7. reaching isolated source control and recovering the fictional benchmark
   solution set.

Every target is local to the participant's disposable VM. The five upstream
challenge networks stay Docker-internal. A sixth adapter network is limited to
the narrow model-access path needed by the coding agent.
