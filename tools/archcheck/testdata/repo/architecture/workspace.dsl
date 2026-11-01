workspace "Fixture" "A fixture repository." {
    !identifiers hierarchical

    model {
        repo = softwareSystem "Fixture" "A fixture repository." {
            library = container "Library" "The library." "Go" {
                root = component "root" "The root package." "Go"
            }
        }
    }

    views {
        systemContext repo "context" {
            include *
            autoLayout lr
        }
        container repo "containers" {
            include *
            autoLayout lr
        }
        component repo.library "components-library" {
            include *
            autoLayout lr
        }
    }
}
