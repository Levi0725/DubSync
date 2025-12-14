# External Plugins

Ez a mappa a külső (nem beépített) pluginoknak van fenntartva.

Minden plugin egy külön mappában helyezkedik el:

```
external/
├── my_plugin/
│   ├── __init__.py       # Plugin osztály
│   ├── README.md         # Dokumentáció
│   └── requirements.txt  # Függőségek
└── another_plugin/
    └── ...
```

## Plugin telepítés

A pluginok automatikusan betöltődnek, ha:
1. Van `__init__.py` fájl
2. Tartalmaz egy `Plugin` osztályt vagy `PluginInterface` leszármazottat
3. A plugin engedélyezve van a beállításokban

## Követelmények

Lásd: [PLUGIN_DEVELOPMENT.md](../../../../docs/PLUGIN_DEVELOPMENT.md)
