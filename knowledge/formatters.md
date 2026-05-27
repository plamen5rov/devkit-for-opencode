# Formatters | OpenCode
OpenCode uses language specific formatters.

OpenCode can format files after they are written or edited using language-specific formatters. Formatters are disabled by default; enable them in your config before OpenCode will run them.

* * *

[Built-in](#built-in)
---------------------

OpenCode comes with several built-in formatters for popular languages and frameworks. Below is a list of the formatters, supported file extensions, and commands or config options it needs.



* Formatter: air
  * Extensions: .R
  * Requirements: air command available
* Formatter: biome
  * Extensions: .js, .jsx, .ts, .tsx, .html, .css, .md, .json, .yaml, and more
  * Requirements: biome.json(c) config file
* Formatter: cargofmt
  * Extensions: .rs
  * Requirements: cargo fmt command available
* Formatter: clang-format
  * Extensions: .c, .cpp, .h, .hpp, .ino, and more
  * Requirements: .clang-format config file
* Formatter: cljfmt
  * Extensions: .clj, .cljs, .cljc, .edn
  * Requirements: cljfmt command available
* Formatter: dart
  * Extensions: .dart
  * Requirements: dart command available
* Formatter: dfmt
  * Extensions: .d
  * Requirements: dfmt command available
* Formatter: gleam
  * Extensions: .gleam
  * Requirements: gleam command available
* Formatter: gofmt
  * Extensions: .go
  * Requirements: gofmt command available
* Formatter: htmlbeautifier
  * Extensions: .erb, .html.erb
  * Requirements: htmlbeautifier command available
* Formatter: ktlint
  * Extensions: .kt, .kts
  * Requirements: ktlint command available
* Formatter: mix
  * Extensions: .ex, .exs, .eex, .heex, .leex, .neex, .sface
  * Requirements: mix command available
* Formatter: nixfmt
  * Extensions: .nix
  * Requirements: nixfmt command available
* Formatter: ocamlformat
  * Extensions: .ml, .mli
  * Requirements: ocamlformat command available and .ocamlformat config file
* Formatter: ormolu
  * Extensions: .hs
  * Requirements: ormolu command available
* Formatter: oxfmt (Experimental)
  * Extensions: .js, .jsx, .ts, .tsx
  * Requirements: oxfmt dependency in package.json and an experimental env variable flag
* Formatter: pint
  * Extensions: .php
  * Requirements: laravel/pint dependency in composer.json
* Formatter: prettier
  * Extensions: .js, .jsx, .ts, .tsx, .html, .css, .md, .json, .yaml, and more
  * Requirements: prettier dependency in package.json
* Formatter: rubocop
  * Extensions: .rb, .rake, .gemspec, .ru
  * Requirements: rubocop command available
* Formatter: ruff
  * Extensions: .py, .pyi
  * Requirements: ruff command available with config
* Formatter: rustfmt
  * Extensions: .rs
  * Requirements: rustfmt command available
* Formatter: shfmt
  * Extensions: .sh, .bash
  * Requirements: shfmt command available
* Formatter: standardrb
  * Extensions: .rb, .rake, .gemspec, .ru
  * Requirements: standardrb command available
* Formatter: terraform
  * Extensions: .tf, .tfvars
  * Requirements: terraform command available
* Formatter: uv
  * Extensions: .py, .pyi
  * Requirements: uv command available
* Formatter: zig
  * Extensions: .zig, .zon
  * Requirements: zig command available


When formatters are enabled, OpenCode will use `prettier` for matching files if your project has `prettier` in `package.json`.

* * *

[How it works](#how-it-works)
-----------------------------

When OpenCode writes or edits a file and formatters are enabled, it:

1.  Checks the file extension against all enabled formatters.
2.  Runs the appropriate formatter command on the file.
3.  Applies the formatting changes.

This process happens in the background for enabled formatters.

* * *

[Configure](#configure)
-----------------------

You can enable and customize formatters through the `formatter` section in your OpenCode config.

To enable all built-in formatters, set `formatter` to `true`.

```

{
  "$schema": "https://opencode.ai/config.json",
  "formatter": true
}
```


Use an object to keep built-ins enabled while configuring overrides or custom formatters.

```

{
  "$schema": "https://opencode.ai/config.json",
  "formatter": {}
}
```


Each formatter configuration supports the following:



* Property: disabled
  * Type: boolean
  * Description: Set this to true to disable the formatter
* Property: command
  * Type: string[]
  * Description: The command to run for formatting. Required for custom formatters; optional for built-ins.
* Property: environment
  * Type: object
  * Description: Environment variables to set when running the formatter
* Property: extensions
  * Type: string[]
  * Description: File extensions this formatter should handle


Let’s look at some examples.

* * *

### [Disabling formatters](#disabling-formatters)

If `formatter` is omitted, all formatters are disabled. To disable all formatters after another config enabled them, set `formatter` to `false`:

```

{
  "$schema": "https://opencode.ai/config.json",
  "formatter": false
}
```


To disable a **specific** formatter, set `disabled` to `true`:

```

{
  "$schema": "https://opencode.ai/config.json",
  "formatter": {
    "prettier": {
      "disabled": true
    }
  }
}
```


* * *

### [Custom formatters](#custom-formatters)

You can configure built-in formatters with options like `environment` or `extensions`. To add a custom formatter, specify a `command` and `extensions`:

```

{
  "$schema": "https://opencode.ai/config.json",
  "formatter": {
    "prettier": {
      "command": ["npx", "prettier", "--write", "$FILE"],
      "environment": {
        "NODE_ENV": "development"
      },
      "extensions": [".js", ".ts", ".jsx", ".tsx"]
    },
    "custom-markdown-formatter": {
      "command": ["deno", "fmt", "$FILE"],
      "extensions": [".md"]
    }
  }
}
```


The **`$FILE` placeholder** in the command will be replaced with the path to the file being formatted.