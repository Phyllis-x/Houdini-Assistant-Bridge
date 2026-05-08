# `asset` — HDA libraries and node type definitions

## Functions

| Function                 | Danger      | Description                              |
| ------------------------ | ----------- | ---------------------------------------- |
| `list_installed_libraries` | read      | Loaded `.hda` / `.otl` files.            |
| `install_library`        | write       | Load an HDA library file.                |
| `uninstall_library`      | destructive | Unload an HDA library file.              |
| `get_definition_info`    | read        | Definition + library path for a type.    |
| `find_instances`         | read        | All scene instances of a node type.      |

## Idioms

### Where is a node type defined?

```bash
$CLI call asset get_definition_info --kwargs '{"category":"Sop","type_name":"geo"}'
```

### Find every instance of a custom HDA

```bash
$CLI call asset find_instances --kwargs '{"category":"Sop","type_name":"my_studio::geo_setup::1.0"}'
```

## Notes

- `uninstall_library` is destructive — the preflight requires explicit
  `--allow destructive`.
