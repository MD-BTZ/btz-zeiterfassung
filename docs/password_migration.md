# Passwortmigration

## Übersicht

Diese Migration entfernt die separate `temp_passwords`-Tabelle und integriert deren Funktionalität direkt in die `users`-Tabelle. Dies vereinfacht die Datenbankstruktur und vermeidet Synchronisierungsprobleme zwischen den Tabellen.

## Durchgeführte Änderungen

1. **Datenbank-Schema**:
   - Neue Spalten in der `users`-Tabelle:
     - `plain_password`: Speichert verschlüsselte Passwörter (vorher in `temp_passwords.temp_password`)
     - `verification_hash`: Speichert den Verifikations-Hash (vorher in `temp_passwords.verification_hash`)
     - `last_password_change`: Zeitstempel der letzten Passwortänderung

2. **Datenmigration**:
   - Alle Einträge aus `temp_passwords` wurden in die `users`-Tabelle migriert
   - Die ursprüngliche `temp_passwords`-Tabelle wurde zu `temp_passwords_old` umbenannt

3. **Code-Aktualisierung**:
   - Alle Verweise auf die `temp_passwords`-Tabelle in `app.py` wurden aktualisiert
   - Die Tabellenerstellung wurde angepasst, um das neue Schema zu unterstützen
   - Die Funktionen zur Passwortverarbeitung wurden aktualisiert

## Vorteile

- **Vereinfachte Datenstruktur**: Alle benutzerbezogenen Daten in einer Tabelle
- **Bessere Datenkonsistenz**: Kein Risiko von verwaisten oder nicht synchronisierten Passwortdaten
- **Einfacheres Backup und Wiederherstellung**: Alle relevanten Daten in einer Tabelle
- **Verbesserte Sicherheit**: Implementierte die gleiche Passwort-Hashing-Logik, aber mit einer übersichtlicheren Struktur

## Nach der Migration

1. Testen Sie die Anwendung gründlich, insbesondere:
   - Passwortänderungsprozesse
   - Passwort-Reset durch Administratoren
   - Anmeldefunktionen

2. Wenn alles korrekt funktioniert, können Sie die Backup-Tabelle entfernen:
   ```
   python3 cleanup_tables.py
   ```

## Wiederherstellung im Fehlerfall

Falls Probleme auftreten, können Sie die Datenbank aus dem Backup wiederherstellen:
```
cp attendance_backup_[TIMESTAMP].db attendance.db
```

Die Originalversionen der Dateien wurden ebenfalls gesichert als:
```
app.py.[TIMESTAMP].bak
```
