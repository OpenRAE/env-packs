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
            commands = container "Commands" "The raes-pack commands. They are the composition root." "Go"
            library = container "Go library" "The pack contracts and the pack operations." "Go" {
                root = component "root" "The root package of the module." "Go"
                strict_yaml = component "strict-yaml" "Decodes exactly one YAML document, and rejects unknown fields." "Go"
            }
            repository_tools = container "Repository tools" "The tools that check and release this repository." "Go" {
                report = component "report" "Holds the findings of the repository tools, writes them, and defines the exit statuses of the tools." "Go"
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
        env_packs.repository_tools.architecture -> env_packs.library.strict_yaml "Depends on"
        env_packs.repository_tools.architecture -> env_packs.repository_tools.report "Depends on"
        env_packs.repository_tools.test_gates -> env_packs.library.strict_yaml "Depends on"
        env_packs.repository_tools.test_gates -> env_packs.repository_tools.report "Depends on"
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
