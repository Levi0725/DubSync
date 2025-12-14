# Argos Translator Plugin

Offline fordító plugin a DubSync alkalmazáshoz, amely az Argos Translate könyvtárat használja.

## Funkciók

- 🌍 **Offline működés**: Nincs szükség internet kapcsolatra a fordításhoz
- 🔄 **Valós idejű fordítás**: Gépelés közben frissülő fordítási javaslatok
- 📋 **Egyszerű másolás**: Egy kattintással átmásolható a fordítás
- 🎯 **Angol → Magyar**: Optimalizálva szinkronfordításhoz

## Használat

1. Írd be az angol szöveget a felső szövegmezőbe
2. A fordítás automatikusan megjelenik alul
3. Kattints a "📋 Másolás" gombra a fordítás vágólapra másolásához
4. Használd a "📥 Beillesztés fordításba" gombot a közvetlen beillesztéshez

## Beállítások

A plugin beállításainál módosíthatod:
- Forrásnyelv (alapértelmezett: angol)
- Célnyelv (alapértelmezett: magyar)
- Automatikus fordítás késleltetése

## Nyelvmodellek

Az első használatkor a plugin automatikusan letölti a szükséges nyelvi modelleket.
Ez az első alkalommal néhány percet vehet igénybe.

### Támogatott nyelvek:
- Angol → Magyar
- Magyar → Angol
- (További nyelvpárok telepíthetők)

## Technikai információk

A plugin az [Argos Translate](https://github.com/argosopentech/argos-translate) 
nyílt forráskódú offline fordító motort használja.

### Függőségek:
- `argostranslate` - Offline fordító motor
- `argos-translate-files` - Nyelvi modellek

## Hibaelhárítás

**A fordítás nem működik:**
- Ellenőrizd, hogy a nyelvi modellek le vannak-e töltve
- Indítsd újra az alkalmazást a plugin aktiválása után

**Lassú fordítás:**
- Az első fordítás lassabb lehet a modell betöltése miatt
- Nagyobb szövegek fordítása több időt vesz igénybe

## Verzióelőzmények

### v1.0.0
- Kezdeti kiadás
- Angol-Magyar fordítás támogatás
- Integrált fordító panel
