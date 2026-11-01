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
            }
            repository_tools = container "Repository tools" "The tools that check and release this repository." "Go" {
                architecture = component "architecture" "Checks the code and the design records against this model." "Go"
            }
        }

        pack_author -> env_packs "Builds, checks, and releases packs with"
        pack_consumer -> env_packs "Validates packs with"
        maintainer -> env_packs "Develops and releases"
        env_packs -> raes "Validates SDL and RAES contracts with"
        env_packs -> github "Is built and released on"
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
