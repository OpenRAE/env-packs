workspace "RAES environment-pack tooling" "Defines, validates, and releases RAES environment packs." {
    !identifiers hierarchical

    model {
        pack_author = person "Pack author" "Builds, checks, and releases environment packs."
        pack_consumer = person "Pack consumer" "Validates an environment pack before it uses the pack."
        maintainer = person "Maintainer" "Develops, reviews, and releases this repository."
        raes = softwareSystem "RAES" "Owns the SDL and the RAES contracts." {
            tags "External"
        }
        github = softwareSystem "GitHub" "Hosts the repository, its CI, and its releases." {
            tags "External"
        }
        env_packs = softwareSystem "RAES environment-pack tooling" "Defines, validates, and releases RAES environment packs." {
            commands = container "Commands" "The raes-pack commands. They are the composition root." "Go" {
                issue_skeleton_command = component "issue-skeleton-command" "The raes-pack-issue-skeleton command. Its Runner is the only code that starts gh." "Go"
            }
            library = container "Go library" "The pack contracts and the pack operations." "Go" {
                root = component "root" "The root package of the module." "Go"
                packfs = component "packfs" "Reads pack trees through root descriptors, and commits staged trees atomically." "Go"
                document = component "document" "Decodes pack-owned YAML and JSON strictly, within the validation limits." "Go"
                schema = component "schema" "Holds the packaged schemas and validates a document against them in full." "Go"
                secret_shape = component "secret-shape" "The one policy for secret-shaped keys and values." "Go"
                diagnostic = component "diagnostic" "The one diagnostic type of the product, its presentation catalog, and the list of the diagnostics of one operation." "Go"
                outcome = component "outcome" "The exit statuses and the output streams of the commands and the repository tools, and the handling of defects." "Go"
                jsondoc = component "jsondoc" "Writes JSON envelopes and documents with the bytes of the Python implementation." "Go"
                terminal = component "terminal" "Escapes labels from packs, file names, and arguments for a terminal." "Go"
                raes_interface = component "raes-interface" "Declares the RAES operations that env-packs uses. Only its adapter calls the RAES Go module." "Go"
                issue_skeleton = component "issue-skeleton" "Plans the standard planning issues of a new pack, and writes them to GitHub through gh." "Go"
                strict_yaml = component "strict-yaml" "Decodes exactly one YAML document, and rejects unknown fields." "Go"
            }
            repository_tools = container "Repository tools" "The tools that check and release this repository." "Go" {
                report = component "report" "Holds the findings of the repository tools and writes them." "Go"
                architecture = component "architecture" "Checks the code and the design records against this model." "Go"
                test_gates = component "test-gates" "Runs mutation testing on changed lines and proves regression tests." "Go"
                conformance = component "conformance" "Runs the conformance corpus against the Python or the Go implementation." "Go"
            }
        }

        pack_author -> env_packs "Builds, checks, and releases packs with"
        pack_consumer -> env_packs "Validates packs with"
        maintainer -> env_packs "Develops and releases"
        env_packs -> raes "Validates SDL and RAES contracts with"
        env_packs -> github "Is built and released on"
        env_packs.library.schema -> env_packs.library.document "Depends on"
        env_packs.library.schema -> env_packs.library.root "Depends on"
        env_packs.library.schema -> env_packs.library.diagnostic "Depends on"
        env_packs.library.issue_skeleton -> env_packs.library.terminal "Depends on"
        env_packs.commands.issue_skeleton_command -> env_packs.library.issue_skeleton "Depends on"
        env_packs.commands.issue_skeleton_command -> env_packs.library.outcome "Depends on"
        env_packs.commands.issue_skeleton_command -> env_packs.library.terminal "Depends on"
        env_packs.repository_tools.report -> env_packs.library.outcome "Depends on"
        env_packs.repository_tools.architecture -> env_packs.library.strict_yaml "Depends on"
        env_packs.repository_tools.architecture -> env_packs.repository_tools.report "Depends on"
        env_packs.repository_tools.architecture -> env_packs.library.outcome "Depends on"
        env_packs.repository_tools.test_gates -> env_packs.library.strict_yaml "Depends on"
        env_packs.repository_tools.test_gates -> env_packs.repository_tools.report "Depends on"
        env_packs.repository_tools.test_gates -> env_packs.library.outcome "Depends on"
    }

    views {
        systemContext env_packs "context" {
            include *
            autoLayout lr
        }
        container env_packs "containers" {
            include *
            autoLayout lr
        }
        component env_packs.commands "components-commands" {
            include *
            autoLayout lr
        }
        component env_packs.library "components-library" {
            include *
            autoLayout lr
        }
        component env_packs.repository_tools "components-repository-tools" {
            include *
            autoLayout lr
        }
    }
}
