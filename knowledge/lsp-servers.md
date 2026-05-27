# LSP Servers | OpenCode
OpenCode can integrate with Language Server Protocol (LSP) servers to use diagnostics as feedback for the agent.

* * *

[Built-in](#built-in)
---------------------

OpenCode comes with several built-in LSP servers for popular languages:



* LSP Server: astro
  * Extensions: .astro
  * Requirements: Auto-installs for Astro projects
* LSP Server: bash
  * Extensions: .sh, .bash, .zsh, .ksh
  * Requirements: Auto-installs bash-language-server
* LSP Server: clangd
  * Extensions: .c, .cpp, .cc, .cxx, .c++, .h, .hpp, .hh, .hxx, .h++
  * Requirements: Auto-installs for C/C++ projects
* LSP Server: csharp
  * Extensions: .cs, .csx
  * Requirements: .NET SDK installed
* LSP Server: clojure-lsp
  * Extensions: .clj, .cljs, .cljc, .edn
  * Requirements: clojure-lsp command available
* LSP Server: dart
  * Extensions: .dart
  * Requirements: dart command available
* LSP Server: deno
  * Extensions: .ts, .tsx, .js, .jsx, .mjs
  * Requirements: deno command available (auto-detects deno.json/deno.jsonc)
* LSP Server: elixir-ls
  * Extensions: .ex, .exs
  * Requirements: elixir command available
* LSP Server: eslint
  * Extensions: .ts, .tsx, .js, .jsx, .mjs, .cjs, .mts, .cts, .vue
  * Requirements: eslint dependency in project
* LSP Server: fsharp
  * Extensions: .fs, .fsi, .fsx, .fsscript
  * Requirements: .NET SDK installed
* LSP Server: gleam
  * Extensions: .gleam
  * Requirements: gleam command available
* LSP Server: gopls
  * Extensions: .go
  * Requirements: go command available
* LSP Server: hls
  * Extensions: .hs, .lhs
  * Requirements: haskell-language-server-wrapper command available
* LSP Server: jdtls
  * Extensions: .java
  * Requirements: Java SDK (version 21+) installed
* LSP Server: julials
  * Extensions: .jl
  * Requirements: julia and LanguageServer.jl installed
* LSP Server: kotlin-ls
  * Extensions: .kt, .kts
  * Requirements: Auto-installs for Kotlin projects
* LSP Server: lua-ls
  * Extensions: .lua
  * Requirements: Auto-installs for Lua projects
* LSP Server: nixd
  * Extensions: .nix
  * Requirements: nixd command available
* LSP Server: ocaml-lsp
  * Extensions: .ml, .mli
  * Requirements: ocamllsp command available
* LSP Server: oxlint
  * Extensions: .ts, .tsx, .js, .jsx, .mjs, .cjs, .mts, .cts, .vue, .astro, .svelte
  * Requirements: oxlint dependency in project
* LSP Server: php intelephense
  * Extensions: .php
  * Requirements: Auto-installs for PHP projects
* LSP Server: prisma
  * Extensions: .prisma
  * Requirements: prisma command available
* LSP Server: pyright
  * Extensions: .py, .pyi
  * Requirements: pyright dependency installed
* LSP Server: razor
  * Extensions: .razor, .cshtml
  * Requirements: .NET SDK and VS Code C# extension installed
* LSP Server: ruby-lsp (rubocop)
  * Extensions: .rb, .rake, .gemspec, .ru
  * Requirements: ruby and gem commands available
* LSP Server: rust
  * Extensions: .rs
  * Requirements: rust-analyzer command available
* LSP Server: sourcekit-lsp
  * Extensions: .swift, .objc, .objcpp
  * Requirements: swift installed (xcode on macOS)
* LSP Server: svelte
  * Extensions: .svelte
  * Requirements: Auto-installs for Svelte projects
* LSP Server: terraform
  * Extensions: .tf, .tfvars
  * Requirements: Auto-installs from GitHub releases
* LSP Server: tinymist
  * Extensions: .typ, .typc
  * Requirements: Auto-installs from GitHub releases
* LSP Server: typescript
  * Extensions: .ts, .tsx, .js, .jsx, .mjs, .cjs, .mts, .cts
  * Requirements: typescript dependency in project
* LSP Server: vue
  * Extensions: .vue
  * Requirements: Auto-installs for Vue projects
* LSP Server: yaml-ls
  * Extensions: .yaml, .yml
  * Requirements: Auto-installs Red Hat yaml-language-server
* LSP Server: zls
  * Extensions: .zig, .zon
  * Requirements: zig command available


LSP is disabled by default. When enabled, servers start when one of the above file extensions is detected and the requirements are met.

* * *

[How It Works](#how-it-works)
-----------------------------

When LSP is enabled and opencode opens a file, it:

1.  Checks the file extension against all enabled LSP servers.
2.  Starts the appropriate LSP server if not already running.

* * *

[Best Practices](#best-practices)
---------------------------------

LSP can help the agent find and fix issues by providing diagnostics from language servers. This is useful in some projects, but it is not always a net positive.

Language servers can get out of sync, use significant memory, vary by version or project, and slow down agent workflows. In many projects it is better to have the agent run lint, typecheck, or other diagnostic CLI tools directly, so errors are fed back into the agent loop without those tradeoffs. Document those commands in instruction files such as `AGENTS.md` or skills so the agent knows what to run. Enable LSP when your project benefits from additional language-server feedback.

* * *

[Configure](#configure)
-----------------------

You can enable and customize LSP servers through the `lsp` section in your opencode config.

To enable all built-in LSP servers, set `lsp` to `true`.

```

{
  "$schema": "https://opencode.ai/config.json",
  "lsp": true
}
```


Use an object to keep built-ins enabled while configuring overrides or custom servers.

```

{
  "$schema": "https://opencode.ai/config.json",
  "lsp": {}
}
```


Each configured LSP server entry supports the following:

Server entries need `command` unless they only disable a server.


|Property      |Type    |Description                                      |
|--------------|--------|-------------------------------------------------|
|disabled      |boolean |Set this to true to disable the LSP server       |
|command       |string[]|The command to start the LSP server              |
|extensions    |string[]|File extensions this LSP server should handle    |
|env           |object  |Environment variables to set when starting server|
|initialization|object  |Initialization options to send to the LSP server |


Let’s look at some examples.

* * *

### [Environment variables](#environment-variables)

Use the `env` property to set environment variables when starting the LSP server:

```

{
  "$schema": "https://opencode.ai/config.json",
  "lsp": {
    "rust": {
      "command": ["rust-analyzer"],
      "env": {
        "RUST_LOG": "debug"
      }
    }
  }
}
```


* * *

### [Initialization options](#initialization-options)

Use the `initialization` property to pass initialization options to the LSP server. These are server-specific settings sent during the LSP `initialize` request:

```

{
  "$schema": "https://opencode.ai/config.json",
  "lsp": {
    "custom-lsp": {
      "command": ["custom-lsp-server", "--stdio"],
      "extensions": [".custom"],
      "initialization": {
        "preferences": {
          "importModuleSpecifierPreference": "relative"
        }
      }
    }
  }
}
```


* * *

### [Disabling LSP servers](#disabling-lsp-servers)

If `lsp` is omitted, all LSP servers are disabled. To disable all LSP servers after another config enabled them, set `lsp` to `false`:

```

{
  "$schema": "https://opencode.ai/config.json",
  "lsp": false
}
```


To disable a **specific** LSP server, set `disabled` to `true`:

```

{
  "$schema": "https://opencode.ai/config.json",
  "lsp": {
    "typescript": {
      "disabled": true
    }
  }
}
```


* * *

### [Custom LSP servers](#custom-lsp-servers)

You can add custom LSP servers by specifying the command and file extensions:

```

{
  "$schema": "https://opencode.ai/config.json",
  "lsp": {
    "custom-lsp": {
      "command": ["custom-lsp-server", "--stdio"],
      "extensions": [".custom"]
    }
  }
}
```


* * *

[Additional Information](#additional-information)
-------------------------------------------------

### [PHP Intelephense](#php-intelephense)

PHP Intelephense offers premium features through a license key. You can provide a license key by placing (only) the key in a text file at:

*   On macOS/Linux: `$HOME/intelephense/license.txt`
*   On Windows: `%USERPROFILE%/intelephense/license.txt`

The file should contain only the license key with no additional content.