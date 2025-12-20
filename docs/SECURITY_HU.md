# Biztonsági Irányelvek

## Támogatott Verziók

| Verzió | Támogatott         |
| ------ | ------------------ |
| 0.1.x  | :white_check_mark: |

## Sebezhetőség Bejelentése

Ha biztonsági sebezhetőséget találsz a DubSync-ben, kérjük, felelősségteljesen jelentsd:

1. **NE** nyiss publikus GitHub issue-t biztonsági sebezhetőségekhez
2. Küldj emailt a karbantartóknak az alábbi információkkal:
   - A sebezhetőség leírása
   - Reprodukálási lépések
   - Lehetséges hatás
   - Javasolt javítás (opcionális)

### Mire számíthatsz

- 48 órán belül visszaigazoljuk a bejelentést
- 7 napon belül első értékelést adunk
- Dolgozunk a javításon és egyeztetjük a közzététel időzítését
- Elismerést kapnak a bejelentők (hacsak nem kérnek anonimitást)

### Hatókör

Ez a biztonsági irányelv vonatkozik:
- Magára a DubSync alkalmazásra
- A beépített pluginokra
- A plugin betöltési mechanizmusra

A külső/harmadik féltől származó pluginok a szerzőik felelőssége.

## Biztonsági Bevált Gyakorlatok Felhasználóknak

1. **Plugin Biztonság**: Csak megbízható forrásból telepíts pluginokat
2. **Projekt Fájlok**: Légy óvatos ismeretlen forrásból származó `.dubsync` fájlok megnyitásakor
3. **Frissítések**: Tartsd naprakészen a DubSync-et a legújabb biztonsági javításokért

## Biztonsági Megfontolások Plugin Fejlesztőknek

Ha plugint fejlesztesz a DubSync-hez:

1. **Input Validálás**: Mindig validáld a felhasználói bevitelt
2. **Fájlműveletek**: Légy óvatos a fájlrendszer elérésével
3. **Függőségek**: Tartsd naprakészen és rendszeresen auditáld a függőségeidet
4. **Kód Átvizsgálás**: Fontold meg a kódod átvizsgáltatását publikálás előtt

---

*Ez a dokumentum [angolul](../SECURITY.md) is elérhető.*
