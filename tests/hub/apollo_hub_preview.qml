import Quickshell
import "../../widgets"

// Separate preview entry point: not loaded by the main Post-Apollo shell.
// It deliberately opens the staged Hub without replacing Calendar in the bar.
Scope {
    ApolloHubW {
        menuOpen: true
    }
}
