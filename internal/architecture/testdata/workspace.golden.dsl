workspace "System" "The system." {
    !identifiers hierarchical

    model {
        author = person "Author" "Writes packs."
        upstream = softwareSystem "Upstream" "An \"external\" system with a \\ backslash." {
            tags "External"
        }
        system = softwareSystem "System" "The system." {
            library = container "Library" "The library." "Go" {
                core = component "core" "The core." "Go"
                feature = component "feature" "A feature." "Go"
            }
            tools = container "Tools" "The tools." "Go"
        }

        author -> system "Uses"
        system -> upstream "Calls"
        system.library.feature -> system.library.core "Depends on"
    }

    views {
        systemContext system "context" {
            include *
            autoLayout lr
        }
        container system "containers" {
            include *
            autoLayout lr
        }
        component system.library "components-library" {
            include *
            autoLayout lr
        }
    }
}
